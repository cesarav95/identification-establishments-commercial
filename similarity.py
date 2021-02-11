import cv2
import numpy as np
import os
from matplotlib import pyplot as plt
import json
import copy
#Pytorch
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
from torchvision import datasets, models, transforms, utils
from torch.autograd import Variable
from collections import OrderedDict
from PIL import Image
import torch.nn.functional as F
import math
import utils

from fuzzywuzzy import fuzz # Para comparar similaridad entre textos

#Parametros
THRESH_SIMILARIDAD = 0.40
THRESH_DIST_ENTRE_IMGS = 15
THRESH_SIMILARIDAD_TEXT = 77

#SIMILARIDAD ENTRE IMAGENES DE ESTABLECIMINETOS COMERCIALES

# Carga el modelo que se utilizara para calcular la similitud de dos imagenes
def cargar_modelo_similaridad(dir_pth):
  print("Cargando modelo similaridad...")
  model = models.vgg16_bn(pretrained=True)
  classifier = nn.Sequential(OrderedDict([
      ('fc1', nn.Linear(4096, 4096)),
      ('relu', nn.ReLU()),
      ('drpot', nn.Dropout(p=0.2)),
      ('fc2', nn.Linear(4096, 8)),
      ('output', nn.LogSoftmax(dim=1))
  ]))
  model.classifier[6] = classifier
  model.load_state_dict(torch.load(dir_pth))
  model.cuda()
  return model

# Extrae el feature vector de una imagen al pasar por el modelo de similaridad 
def obtener_feature_vector_img(img, model):  
  layer = model._modules.get('avgpool')# ultima capa de la parte convolucional del modelo, en este caso VGG16
  preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
  ])
  input_tensor = preprocess(img)
  input_batch = input_tensor.unsqueeze(0).cuda()
  my_embedding = torch.zeros(25088).unsqueeze(0)
  def copiar_data(m, i, o):
    x = o.data.reshape(-1)
    my_embedding.copy_(x)
  h = layer.register_forward_hook(copiar_data)
  model.eval()
  model(input_batch)
  h.remove()
  return my_embedding

#Calcula la similaridad de dos imagenes usando distancia coseno
def calcular_similitud_imagenes(img1, img2, model):
  fv_1 = obtener_feature_vector_img(img1, model)
  fv_2 = obtener_feature_vector_img(img2, model)
  cos = nn.CosineSimilarity(dim=1, eps=1e-6)
  cos_sim = cos(fv_1,fv_2)
  return cos_sim[0]

def reducir_array_objetos_similares(array):
  print("Simplificando arreglos de objetos similares...")
  arr_result = []
  while len(array) > 0:
    c1 = set(array[0])    
    array.pop(0)
    elim = []
    for i,e in enumerate(array):
        if(len(set(c1).intersection(e))>0):
            elim.append(e)            
            c1 = c1.union(e)
    arr_result.append(c1)
    for w in elim:
        array.remove(w)
  return arr_result 

def mostrar_imagenes_similares(image1,image2, s):
  fig, (ax1, ax2, ax3) = plt.subplots(figsize=(14,2), ncols=3, nrows=1)
  ax1.imshow(image1)
  ax1.axis('off')    
  ax2.imshow(image2)
  ax2.axis('off')
  ax3.set_title(s*100)
  ax3.axis('off')

def convertir_indices_pred_a_bb(array_similares, array_bb, tipo='TEST'):
  resultados = []
  cont = 0
  for s in array_similares:
    cont = cont + 1
    images_bbs = []
    clases =[]
    crops = []
    prob = []
    cont_crop = 0
    for obj in s:
      img_index = int(obj.split("-")[0])
      bb_index = int(obj.split("-")[1])
      crops.append("{}-{}".format(cont,cont_crop))
      cont_crop  = cont_crop + 1
      if tipo == 'TEST':
        images_bbs.append({"img_path":array_bb[img_index]["img_path"], "bb":array_bb[img_index]["bounding_boxes"][bb_index]})
      else:
        prob.append(1)
        clases.append(array_bb[img_index]["clases"][bb_index])
        images_bbs.append({"img_path":array_bb[img_index]["img_path"], "bb":array_bb[img_index]["bounding_boxes"][bb_index]})
    resultados.append({"id_obj":cont, "objetos":images_bbs, "clase":{"class_idx":clases, "prob":prob}, "crops":crops})  
  return resultados

#Agrupa detecciones, en base a la similitud de las regiones de imagenes detectadas
def agrupar_objetos_similares(predicciones_yolo,metadatos, dir_pth_sim,tipoconsulta='TEST'):
  print("Agrupando objetos similares")
  predicciones_con_objetos = []
  bb_por_imagen = {}
  #eliminar imagenes sin detecciones
  for p in predicciones_yolo:
    if (len(p["bounding_boxes"]) > 0):
      predicciones_con_objetos.append(p)
    filename_tmp = p["img_path"].split('/')[-1]
    bb_por_imagen[filename_tmp] = len(p["bounding_boxes"])
  imagenes_sin_objetos = len(predicciones_yolo) - len(predicciones_con_objetos)
  print("Cantidad imagenes con objetos", len(predicciones_con_objetos))
  print("Cantidad imagenes sin objetos", imagenes_sin_objetos)
  print("Cantidad total de imagenes", len(predicciones_yolo))
  #cargar modelo
  modelo_sim =  cargar_modelo_similaridad(dir_pth_sim)
  array_objetos = []
  for i in range(len(predicciones_con_objetos) - 1):
    # Recuperar bbs
    path_img1 = predicciones_con_objetos[i]["img_path"]
    bbs1 = predicciones_con_objetos[i]["bounding_boxes"]
    path_img2 = predicciones_con_objetos[i+1]["img_path"]
    bbs2 = predicciones_con_objetos[i+1]["bounding_boxes"]
    #verificar si son imagenes del mismo lado
    filename1 = path_img1.split('/')[-1].replace('.jpg','').replace('.png','')
    filename2 = path_img2.split('/')[-1].replace('.jpg','').replace('.png','')
    dir_img1 = 'iz'
    dir_img2 = 'iz'
    if 'der-' in filename1:
      dir_img1 = 'der'
    if 'der-' in filename2:
      dir_img2 = 'der'    
    #calcular distancia entre las ubicaciones geograficas de las imagenes a comparar
    location1 = utils.convertir_punto_crs(metadatos[filename1]["coordenadas"],4326,24879) 
    location2 = utils.convertir_punto_crs(metadatos[filename2]["coordenadas"],4326,24879)  
    distancia_imgs =  utils.calcular_distancia_puntos(location1, location2)  
    #Comparar detecctiones de las dos imagenes
    for index1, bb1 in enumerate(bbs1):
      img_crop1 = utils.recuperar_crop_imagen_bb(path_img1,bb1)
      id_obj1 = "{}-{}".format(i,index1)# formar un id con el indeice de la imagen y de su bb
      objeto = []
      objeto.append(id_obj1)
      for index2, bb2 in enumerate(bbs2):        
        img_crop2 = utils.recuperar_crop_imagen_bb(path_img2,bb2)
        id_obj2 = "{}-{}".format(str(i+1),index2)# formar un id con el indeice de la imagen y de su bb
        #print("id object 2 :",id_obj2)
        if dir_img1 == dir_img2:
          similaridad = calcular_similitud_imagenes(img_crop1, img_crop2, modelo_sim)
          if similaridad >= THRESH_SIMILARIDAD and distancia_imgs <= THRESH_DIST_ENTRE_IMGS:
            print("Similaridad entre {} y {} en {}  con distancia {} metros%".format(path_img1,path_img2,similaridad*100,distancia_imgs ))
            objeto.append(id_obj2)
            mostrar_imagenes_similares(img_crop1, img_crop2, similaridad)
          else:
            if similaridad >= THRESH_SIMILARIDAD:
              mostrar_imagenes_similares(img_crop1, img_crop2, similaridad)
              print("Similaridad NO entre {} y {} en {}  con distancia {} metros%".format(path_img1,path_img2,similaridad*100,distancia_imgs ))
                      
        if i == (len(predicciones_con_objetos) - 2): #Guardar los objetos detectados de la ultima imagen
          #print("ultimo index: ",i)
          array_objetos.append([id_obj2])
      array_objetos.append(objeto)
  #Enlazar objetos similares de la secuencia de imagenes
  array_similares = reducir_array_objetos_similares(array_objetos)
  #print(array_similares)
  resultados = convertir_indices_pred_a_bb(array_similares,predicciones_con_objetos, tipo = tipoconsulta)
  return resultados,imagenes_sin_objetos,bb_por_imagen


def guardar_objetos(array, dir_output):
  os.makedirs(dir_output, exist_ok=True)
  for obj in array:
    id = obj["id_obj"]
    #os.makedirs("{}/{}".format(dir_output,id), exist_ok=True)
    bbs = obj["objetos"]
    cont = 0
    for bb in bbs:
      img = Image.open(bb["img_path"]).convert('RGB')
      img_crop = img.crop(bb["bb"][:4])
      #img_crop.save("{}/{}/{}.jpg".format(dir_output,id,cont), 'PNG')
      img_crop.save("{}/{}-{}.jpg".format(dir_output,id,cont), 'PNG')
      cont = cont + 1

#Funcion que determinar la simitus entre dos cadenas de texto
def similitud_textos(t1,t2):
  #umbral = 0.80
  umbral = THRESH_SIMILARIDAD_TEXT
  #prob = jellyfish.jaro_winkler_similarity(t1, t2)
  prob = fuzz.ratio(t1, t2)
  if prob >= umbral:
    return True
  else:
    return False
  