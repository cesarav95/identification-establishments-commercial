import torch as torch
import torch.nn as nn
from torchvision import datasets, models, transforms, utils
from torch.autograd import Variable
from skimage import io
import craft.craft_utils as craft_utils
import craft.imgproc as imgproc
import craft.file_utils as file_utils
import json
import zipfile
from craft.craft import CRAFT
from collections import OrderedDict
import torch.backends.cudnn as cudnn
import argparse
from PIL import Image
import time
import numpy as np
import cv2
import os

def copyStateDict(state_dict):
    if list(state_dict.keys())[0].startswith("module"):
        start_idx = 1
    else:
        start_idx = 0
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = ".".join(k.split(".")[start_idx:])
        new_state_dict[name] = v
    return new_state_dict

def str2bool(v):
    return v.lower() in ("yes", "y", "true", "t", "1")

# convert bounding shape to bounding box
def bounding_box(points):
    points = points.astype(np.int16)
    x_coordinates, y_coordinates = zip(*points)
    return [(min(x_coordinates), min(y_coordinates)), (max(x_coordinates), max(y_coordinates))]

def test_net(net, image, text_threshold, link_threshold, low_text, cuda, poly, refine_net=None):

    t0 = time.time()
    # resize
    img_resized, target_ratio, size_heatmap = imgproc.resize_aspect_ratio(image, args.canvas_size, interpolation=cv2.INTER_LINEAR, mag_ratio=args.mag_ratio)
    ratio_h = ratio_w = 1 / target_ratio
    # preprocessing
    x = imgproc.normalizeMeanVariance(img_resized)
    x = torch.from_numpy(x).permute(2, 0, 1)    # [h, w, c] to [c, h, w]
    x = Variable(x.unsqueeze(0))                # [c, h, w] to [b, c, h, w]
    if cuda:
        x = x.cuda()
    # forward pass
    with torch.no_grad():
        y, feature = net(x)
    # make score and link map
    score_text = y[0,:,:,0].cpu().data.numpy()
    score_link = y[0,:,:,1].cpu().data.numpy()
    # refine link
    if refine_net is not None:
        with torch.no_grad():
            y_refiner = refine_net(y, feature)
        score_link = y_refiner[0,:,:,0].cpu().data.numpy()
    t0 = time.time() - t0
    t1 = time.time()
    # Post-processing
    boxes, polys = craft_utils.getDetBoxes(score_text, score_link, text_threshold, link_threshold, low_text, poly)
    # coordinate adjustment
    boxes = craft_utils.adjustResultCoordinates(boxes, ratio_w, ratio_h)
    polys = craft_utils.adjustResultCoordinates(polys, ratio_w, ratio_h)
    for k in range(len(polys)):
        if polys[k] is None: polys[k] = boxes[k]
    t1 = time.time() - t1
    # render results (optional)
    render_img = score_text.copy()
    render_img = np.hstack((render_img, score_link))
    ret_score_text = imgproc.cvt2HeatmapImg(render_img)
    if args.show_time : print("\ninfer/postproc time : {:.3f}/{:.3f}".format(t0, t1))
    return boxes, polys, ret_score_text
def recuperar_crop_imagen_bb(path_img, bb):
    img = Image.open(path_img).convert('RGB')
    img_crop = img.crop(bb[:4])
    return img_crop
def recuperar_imagen_dir(path_img):
    img = Image.open(path_img).convert('RGB')
    return img

parser = argparse.ArgumentParser(description='CRAFT Text Detection')
parser.add_argument('--trained_model', default='/content/drive/My Drive/TESIS/codigo-completo/craft/craft_mlt_25k.pth', type=str, help='pretrained model')
parser.add_argument('--text_threshold', default=0.7, type=float, help='text confidence threshold')
parser.add_argument('--low_text', default=0.4, type=float, help='text low-bound score')
parser.add_argument('--link_threshold', default=0.4, type=float, help='link confidence threshold')
parser.add_argument('--cuda', default=True, type=str2bool, help='Use cuda for inference')
parser.add_argument('--canvas_size', default=1280, type=int, help='image size for inference')
parser.add_argument('--mag_ratio', default=1.5, type=float, help='image magnification ratio')
parser.add_argument('--poly', default=False, action='store_true', help='enable polygon type')
parser.add_argument('--show_time', default=False, action='store_true', help='show processing time')
parser.add_argument('--test_folder', default='imagenes-prueba', type=str, help='folder path to input images')
parser.add_argument('--refine', default=False, action='store_true', help='enable link refiner')
parser.add_argument('--refiner_model', default='weights/craft_refiner_CTW1500.pth', type=str, help='pretrained refiner model')
parser.add_argument("-f", "--fff", help="a dummy argument to fool ipython", default="1")
args = parser.parse_args()

def test_craft(objetos):   
    net = CRAFT()     # initialize
    print('Loading weights from checkpoint (' + args.trained_model + ')')
    
    if args.cuda:
        net.load_state_dict(copyStateDict(torch.load(args.trained_model)))
    else:
        net.load_state_dict(copyStateDict(torch.load(args.trained_model, map_location='cpu')))
    if args.cuda:
        net = net.cuda()
        net = torch.nn.DataParallel(net)
        cudnn.benchmark = False
    net.eval()    
    t = time.time()
    imgs_text_obj = {}
    #Analizar objetos detectados
    for i in range(len(objetos)):
        #Recuperar id y imagenes del objeto
        imagenes = objetos[i]["objetos"]
        id_obj = objetos[i]["id_obj"] 
        imgs_text_obj[id_obj]=[]
        #Obtener textos de cada una de las imagenes que componen el objeto
        crops_text = []        
        for img in imagenes:
            img_path = img["img_path"]
            bb = img["bb"]
            img_crop = recuperar_crop_imagen_bb(img_path, bb)
            img_crop = np.array(img_crop)
            image = imgproc.loadImage(img_crop)
            # detection
            bboxes, polys, score_text = test_net(net, image, args.text_threshold, args.link_threshold, args.low_text, args.cuda,args.poly, None)
            for i, bbs in enumerate(bboxes):
                crop = bounding_box(bbs)
                cropped = image[crop[0][1]:crop[1][1],crop[0][0]:crop[1][0]]
                crops_text.append(cropped)
        imgs_text_obj[id_obj] = crops_text
    print("elapsed time : {}s".format(time.time() - t))
    return imgs_text_obj

def test_craft_prueba(ruta, DIR_PTH = "craft_mlt_25k.pth"):   
    net = CRAFT()     # initialize
    print('Loading weights from checkpoint (' + DIR_PTH + ')')
    
    if args.cuda:
        net.load_state_dict(copyStateDict(torch.load(DIR_PTH)))
    else:
        net.load_state_dict(copyStateDict(torch.load(DIR_PTH, map_location='cpu')))
    if args.cuda:
        net = net.cuda()
        net = torch.nn.DataParallel(net)
        cudnn.benchmark = False
    net.eval()    
    t = time.time()
    imgs_text_obj = {}
    arr = os.listdir(ruta)
    for i, name in enumerate(arr):
        arr[i] = ruta+"/"+name
    crops_text = []
    #Analizar objetos detectados
    for i in range(len(arr)):
        #Obtener textos de cada una de las imagenes que componen el objeto
        
        img_crop = recuperar_imagen_dir(arr[i])
        img_crop = np.array(img_crop)
        image = imgproc.loadImage(img_crop)
        # detection
        bboxes, polys, score_text = test_net(net, image, args.text_threshold, args.link_threshold, args.low_text, args.cuda,args.poly, None)
        for i, bbs in enumerate(bboxes):
            crop = bounding_box(bbs)
            cropped = image[crop[0][1]:crop[1][1],crop[0][0]:crop[1][0]]
            crops_text.append(cropped)
    print("elapsed time : {}s".format(time.time() - t))
    return crops_text