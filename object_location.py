import cv2
import numpy as np
import os
import json
import copy
from PIL import Image
import math
import utils
import csv

#Parametros
image_size = 640 
d = image_size / 2

def leer_csv_imagenes_gsv(path_file):
  datos_csv = {}
  list_names_images = []
  with open(path_file) as csv_file:
    cont = 0
    csv_reader = csv.reader(csv_file, delimiter=';')
    for line in csv_reader:
      if(not cont == 0):
        file_name = line[0].replace('.jpg','').replace('.png','')
        datos_csv[file_name] = {"coordenadas":[float(line[1]),float(line[2])], "vector_unit":[float(line[5]),float(line[6])],"fov":float(line[8]), "dist_a_fachada":float(line[7])}
        list_names_images.append(file_name)
      cont = cont + 1
  return datos_csv,list_names_images

def calcular_distancia_en_metros(pixeles, fov, dist_a_fachada):  
  dist_total_imagen = 2*dist_a_fachada*math.tan(math.radians(fov/2))
  #print("TOTAL DIST :", dist_total_imagen)
  #print("DIST A FACHADA:", dist_a_fachada)
  dist_real_fachada = dist_total_imagen * pixeles / image_size
  #conversion de px a metros
  #dist_a_bb = (pixeles -90) * (fov/-50) + (640/15)*d
  return dist_real_fachada

def calcular_ubicacion_geografica_detecciones(predicciones_yolo, datos_csv):
  coordenadas_detecciones = []
  for obj in predicciones_yolo:
    id_obj = obj["id_obj"]
    bbs = obj["objetos"]
    clase = obj["clase"]
    crops = obj["crops"]
    cont = 0
    nuevo_punto = []
    new_x = 0
    new_y = 0
    print("-------------------------------------------------------------------------")
    print("ID_OBJ: ", id_obj)
    print("-------------------------------------------------------------------------")
    for bbox in bbs:
      filename = bbox["img_path"].split('/')[-1].replace(".jpg","").replace(".png","")       
      location = utils.convertir_punto_crs(datos_csv[filename]["coordenadas"],4326,24879)        
      vector_unit = datos_csv[filename]["vector_unit"]
      dist_a_fachada = datos_csv[filename]["dist_a_fachada"]
      fov = datos_csv[filename]["fov"]
      print("nombre imagen : ",filename) 
      bb = bbox["bb"][:4]
      infe_x=bb[0]
      infe_y=bb[1]
      supe_x=bb[2]
      supe_y=bb[3]
      centro_x =(infe_x + supe_x) /2
      centro_y = (infe_y + supe_y) /2
      info = ""
      info = info + "bb = {}".format(bb)
      info = info + ", centro bb en x = {}".format(centro_x)
      #print("Centro bb x: ", centro_x)
      #l = (supe_x - infe_x)/2
      #print("L = ", l)
      #hallar la distancia que vamos considerar aumentar
      #x = d - l#vamos a recorrer
      x = abs(centro_x - d)      
      distancia = calcular_distancia_en_metros(x, fov, dist_a_fachada)
      info = info + ", cant. pixeles desplazar = {}  , dist. metros desplazar = {}".format(x, distancia)
      direccion_imagen = 'der'
      if('iz-' in filename):
        direccion_imagen = 'iz'
      #saber hacia que lado de la imagen se encuentra el boundingbox (IMAGENES IZQUIERDO)
      if ( (centro_x>=d and direccion_imagen == 'iz') or(centro_x<d and direccion_imagen == 'der')):#derecha
          info = info + ", vect. unit : NO CAMBIA DIRECCION"
          x_location_part = location[0] + distancia*vector_unit[0]
          y_location_part = location[1] + distancia*vector_unit[1]
          info = info + ", coordenadas = ({}, {})".format(x_location_part,y_location_part)
          new_x = new_x + (location[0] + distancia*vector_unit[0])
          new_y = new_y + (location[1] + distancia*vector_unit[1])
      else:          #izquierda
          info = info + ", vect. unit. : CAMBIA DIRECCION"
          x_location_part = location[0] + distancia*vector_unit[0]
          y_location_part = location[1] + distancia*vector_unit[1]
          info = info + ". coordenadas = ({}, {})".format(x_location_part,y_location_part)
          new_x = new_x + (location[0] - distancia*vector_unit[0])
          new_y = new_y + (location[1] - distancia*vector_unit[1])      
      print(info)
    new_x = new_x / len(bbs)
    new_y = new_y / len(bbs)
    nuevo_punto = utils.convertir_punto_crs([new_x,new_y],24879,4326)
    
    print("Final location : {}".format(nuevo_punto))
    print()
    coordenadas_detecciones.append({"id_obj":id_obj, "location": nuevo_punto,"clase": clase, "crops": crops, "img_bbs":bbs, "direccion":direccion_imagen})
  return coordenadas_detecciones

def guardar_ubicacion_geografica(detecciones, filename, formato = "json"):
  if formato == "json":
    with open(filename, 'w') as f:
      json.dump(detecciones, f)
  if formato == "csv":
    with open(filename,'w',newline='') as csvfile:
      writer = csv.writer(csvfile, delimiter=';')
      writer.writerow(['id_obj','image_name', 'latitude', 'longitude', 'clases','id_imgs'])
      for d in detecciones:
        writer.writerow([d["id_obj"],d["filename"], d["location"][0],  d["location"][1],d["clase"],d["crops"]])
