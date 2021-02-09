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
import similarity
import utils

#PARAMETROS
#DIR_PTH_CLASIFICACION = "vgg16_bn_ec.pth"
class_names =  ['boticas y farmacias', 'lugares de comida y bebida', 'lugares de estetica y cuidado', 'otros', 'sin negocios', 'tiendas de materiales de construccion', 'tiendas de productos de primera necesidad', 'tiendas de vestir']
class_to_idx = {'boticas y farmacias': 0, 'lugares de comida y bebida': 1, 'lugares de estetica y cuidado': 2, 'otros': 3, 'sin negocios': 4, 'tiendas de materiales de construccion': 5, 'tiendas de productos de primera necesidad': 6, 'tiendas de vestir': 7}
idx_to_class = { v : k for k,v in class_to_idx.items()}
#DIR_DICCIONARIO = "diccionario_ec.txt"

def cargar_modelo_clasificacion(dir_pth):
  print("Cargando modelo clasificacion...")
  model = models.vgg16_bn(pretrained=True)
  classifier = nn.Sequential(OrderedDict([
    ('fc1', nn.Linear(4096, 4096)),
    ('relu', nn.ReLU()),
    ('drpot', nn.Dropout(p=0.2)),
    ('fc2', nn.Linear(4096, 8)),
    ('output', nn.LogSoftmax(dim=1))
  ]))
  model.classifier[6] = classifier
  model.class_to_idx = class_to_idx
  #IN_FEATURES = model.classifier[-1].in_features 
  #final_fc = nn.Linear(IN_FEATURES, 8)
  #model.classifier[-1] = final_fc
  model.load_state_dict(torch.load(dir_pth))
  model.cuda()
  return model

def process_image(image):
    # TODO: Process a PIL image for use in a PyTorch model
    size = 256, 256
    image.thumbnail(size, Image.ANTIALIAS)
    image = image.crop((128 - 112, 128 - 112, 128 + 112, 128 + 112))
    npImage = np.array(image)
    npImage = npImage/255.        
    imgA = npImage[:,:,0]
    imgB = npImage[:,:,1]
    imgC = npImage[:,:,2]    
    imgA = (imgA - 0.485)/(0.229) 
    imgB = (imgB - 0.456)/(0.224)
    imgC = (imgC - 0.406)/(0.225)        
    npImage[:,:,0] = imgA
    npImage[:,:,1] = imgB
    npImage[:,:,2] = imgC    
    npImage = np.transpose(npImage, (2,0,1))    
    return npImage

def preprocesar_imagenes_objeto(imagenes):
  input_imgs = []
  #preprocess = transforms.Compose([
  #  transforms.Resize(256),
  #  transforms.CenterCrop(224),
  #  transforms.ToTensor(),
  #  transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
  #])  
  for img in imagenes:
    img_path = img["img_path"]
    bb = img["bb"]
    img_crop = utils.recuperar_crop_imagen_bb(img_path, bb)
    input_tensor = torch.FloatTensor([process_image(img_crop)])
    #input_tensor = preprocess(img_crop).unsqueeze(0)

    input_imgs.append(input_tensor)  
  return input_imgs

def cargar_diccionario(path_file):
  diccionario = {}
  file = open(path_file)
  lines = file.read().split('\n')
  lines = (line for line in lines if line and not line.startswith('#')) # Eliminar lineas vacias y comentarios
  lines = (line.strip() for line in lines) # Eliminar espacios en blanco de cada linea
  continuar = False
  for line in lines:    
    if(line.startswith('[')):
      index_str = line[1:-1].strip()
      if(index_str.isdigit()):
        index = int(index_str)
        diccionario[index] = []
        continuar = True
      else:
        continuar = False
    else:
      if(continuar):
        diccionario[index].append(line)
  return diccionario

def prediccion_por_textos(diccionario, palabras, coincidentes_unicos=False):
  for j in range(len(palabras)):
    palabras[j] = palabras[j].lower()
  #list_palabras = set(palabras)
  list_palabras = palabras
  print(list_palabras)
  array_pred = [0 for i in range(len(class_names))]  
  threshold_len_words = 3
  pals_coincidentes = []
  pals_coincidentes_unicas = set()
  for index_class in range(len(array_pred)):
    tmp_list_palabras = list_palabras.copy()
    if not index_class == 4:
      cont = 0
      for p in tmp_list_palabras:
        for pclave in diccionario[int(index_class)]:
          if similarity.similitud_textos(p,pclave):
             print("Encontro coincidencia en : index_pal: ",cont," --> ",p," == ", pclave,"clase: ",class_names[index_class])
             array_pred[index_class] = array_pred[index_class] + 1
             id_str_pal = "{}-{}".format(cont,p)
             pals_coincidentes_unicas.add(id_str_pal)
             pals_coincidentes.append(p)
             break
        cont = cont +1
  total_coincidentes = len(pals_coincidentes)
  total_coincidentes_unicas = len(pals_coincidentes_unicas)
  if total_coincidentes > 0:
    if coincidentes_unicos:
      print("Clasificacin CON CU")
      array_pred = [array_pred[i]/total_coincidentes_unicas for i in range(len(array_pred))]
    else:
      print("Clasificacin sin CU")
      array_pred = [array_pred[i]/total_coincidentes for i in range(len(array_pred))]
  return array_pred

def ajustar_probabilidades(diccionario, probabilidades, array_textos):
  prob_ocr = 0.00015
  for index,lista_ocr in enumerate(array_textos):
    prediccion = probabilidades[index]
    s,idx = prediccion.sort()
    top_ids_predictions = idx[-5:]  
    top_ids_predictions = top_ids_predictions.cpu()
    for indice in top_ids_predictions: 
      if(not indice == 1):
        for pal in diccionario[int(indice)]:
            for k in lista_ocr:
                if k in pal and len(k)>= 3:                
                    probabilidades[index][indice] = probabilidades[index][indice] + probabilidades[index][indice]*0.25
                    print (k, ": existe e n", class_names[indice])
  return probabilidades

# Clasificar objeto a una de las clases de establecimiento comercial
def clasificar_objeto(input_imgs, model, textos_ocr, diccionario, cu):  
  #input_batch = input_imgs.cuda()
  probabilidades = []
  prom_probabilidad = torch.zeros(1,8)
  model.eval()
  with torch.no_grad():
    for input in input_imgs:
      input = input.cuda()    
      outputs = model(input)
      #probabilidad = F.softmax(outputs, dim=1)
      #probabilidad = F.sigmoid(outputs)
      probabilidad = outputs.cpu()
      #probabilidad = outputs.cpu()
      #print(probabilidad)
      prom_probabilidad = torch.add(prom_probabilidad,probabilidad)

  prom_probabilidad = prom_probabilidad / len(input_imgs)

  probabilities = torch.exp(prom_probabilidad).data.numpy()[0]
  prob_copy = probabilities.copy()
  top_idx_old = np.argsort(prob_copy)[-1*len(class_names):][::-1] 
  top_class_old = [idx_to_class[x] for x in top_idx_old]   

  #Clasificacion por OCR
  pred_ocr = prediccion_por_textos(diccionario,textos_ocr, coincidentes_unicos=cu)
  print("TEXTOS: ",textos_ocr)  
  print("PROB VGG16: ",probabilities)
  print("PROB_OCR: ",pred_ocr)
  print("CLASES SIN OCR: ",top_class_old)
  #Ajustar probabilidades
  for j in range(len(class_names)):
    if pred_ocr[j] > 0:
      probabilities[j] = (probabilities[j] + pred_ocr[j])/2

  top_idx = np.argsort(probabilities)[-1*len(class_names):][::-1] 
  top_probability = probabilities[top_idx]
  #prob,idx = prom_probabilidad.sort()
  return top_probability, top_idx

def mostrar_clasificacion(img, probabilities, classes, id_obj):
  fig, (ax1, ax2) = plt.subplots(figsize=(15,4), ncols=2, nrows=1)
  titulo = "OBJETO: {}".format(id_obj)    
  ax1.set_title(titulo)
  ax1.imshow(img)
  ax1.axis('off')  
  y_pos = np.arange(len(probabilities))
  ax2.barh(y_pos, probabilities)
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels([x for x in classes])   
  ax2.invert_yaxis() 
  #ax2.set_xlabel(textos)

def mostrar_clases_objetos(objetos):
  for obj in objetos:
    imagenes = obj["objetos"]
    id_obj = obj["id_obj"]
    clases_idx = obj["clase"]["class_idx"]
    #top_class = [class_names[x] for x in clases_idx]
    top_class = [idx_to_class[x] for x in clases_idx]
    prob = obj["clase"]["prob"]    
    img_path = imagenes[0]["img_path"]
    bb = imagenes[0]["bb"]
    img = utils.recuperar_crop_imagen_bb(img_path,bb)
    mostrar_clasificacion(img,prob,top_class, id_obj) 


def clasificar_objetos_detectados(objetos, DIR_PTH_CLASIFICACION,DIR_DICCIONARIO):
  model = cargar_modelo_clasificacion(DIR_PTH_CLASIFICACION)
  diccionario = cargar_diccionario(DIR_DICCIONARIO)
  objetos_output = objetos
  for i in range(len(objetos)):
    imagenes = objetos[i]["objetos"]
    id_obj = objetos[i]["id_obj"] 
    textos_ocr = objetos[i]["textos_ocr"]
    print("OBJETO : ",id_obj)
    input = preprocesar_imagenes_objeto(imagenes)
    output, idx = clasificar_objeto(input, model, textos_ocr, diccionario, cu)
    top_class = [idx_to_class[x] for x in idx]   
    idx = idx.tolist()
    output = output.tolist()   
    objetos_output[i]["clase"] = {"prob":output, "class_idx":idx}
    
    print("PROB_CON_OCR: ",output)
    print("IDX: ", idx)
    print("CLASES: ",top_class )
    print("--------------------------------------------------------")
  return objetos_output
