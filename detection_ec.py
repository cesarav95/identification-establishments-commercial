from cv2 import cv2
import numpy as np
import os
import json

#Parametros
DIR_YOLO_CONFIG = 'yolov4-custom_ec.cfg'
DIR_YOLO_WEIGHTS = 'yolov4-custom_ec.weights'
DIR_YOLO_META = 'obj.data'
BATCH_YOLO = 1
NET_INPUT_SIZE = 608
IMG_INPUT_SIZE = 640
IMG_INPUT_WIDTH = 640
IMG_INPUT_HEIGTH = 640


#Funcion para generar un archivo txt de entrada para yolov4
# el cual contiene las rutas de las imagenes de entrada
def leer_carpeta_imagenes(path):
  list_imgs = []
  list_files = os.listdir(path)# obtener lista de nombres archivos del directorio path
  if os.path.exists("input.txt"):
    os.remove("input.txt")
  file_input = open("input.txt", "w")
  for dir in list_files:
    if '.jpg' in dir or '.png' in dir:
      path_file = path + "/" + dir
      list_imgs.append(path_file)# agregar directorio a la ruta de las imagenes      
      file_input.write(path_file) 
      file_input.write("\n")
  file_input.close()
  return list_imgs

# Funcion para reeescalar el bb predicho por yolov4 ajustado a tamaño original de la imagen
def convertir_bb(x,y,w,h,net_size, img_size):
  # recuperar centro ancho y alto del bounding box
  #x, y, w, h = d[2][0], d[2][1], d[2][2], d[2][3]   #en el caso de usar libdarknet.so
  x = x * net_size
  y = y * net_size
  w = w * net_size
  h = h * net_size
  # reescalar bounding box al tamaño de la imagen original
  x_min = round(img_size*(x - (w/2))/net_size)
  y_min = round(img_size*(y - (h/2))/net_size)
  x_max = round(img_size*(x + (w/2))/net_size)
  y_max = round(img_size*(y + (h/2))/net_size)
  if x_min < 0:
    x_min = 0 
  if y_min < 0:
    y_min = 0
  if x_max > img_size:
    x_max = img_size
  if y_max > img_size:
    y_max = img_size       
  return [x_min,y_min,x_max,y_max]

#Funcion para leer el json de predicciones de yolov4 en darknet
def leer_json_detecciones(path_json):
  data = {}
  with open(path_json) as f:
    data = json.load(f)
  predicciones = []
  for d in data:
    filename = d["filename"].split('/')[-1].replace('.jpg','').replace('.png','')
    objetos = []
    for bb in d["objects"]:
      bounding_box = bb["relative_coordinates"]
      real_bb = convertir_bb(bounding_box["center_x"],bounding_box["center_y"],bounding_box["width"],bounding_box["height"],NET_INPUT_SIZE, IMG_INPUT_SIZE )
      objetos.append(real_bb)
    predicciones.append({ "filename": filename, "bounding_boxes": objetos, "img_path": d["filename"] })
  return predicciones

# Elimna bb que se encuentran dentro de otros
def eliminar_bb_contenidos(detecciones):
  print("Eliminando bounding box contenidos en otro...")
  resultados = []
  for d in detecciones:
    index = 0
    bbs = d["bounding_boxes"] 
    elim = []
    for i in range(len(bbs)):
      #print(i)
      index = i
      p_bb = bbs[index]
      index = index + 1
      while index < len(bbs):        
        s_bb = bbs[index]
        if p_bb[0] >= s_bb[0] and p_bb[1] >= s_bb[1]  and p_bb[2]<= s_bb[2]  and p_bb[3] <= s_bb[3] :
          if not p_bb in elim:
              elim.append(p_bb)
        if s_bb[0] >= p_bb[0] and s_bb[1] >= p_bb[1]  and s_bb[2]<= p_bb[2]  and s_bb[3] <= p_bb[3] :
          if not s_bb in elim:
              elim.append(s_bb)
        index = index + 1
    for e in elim:
      d["bounding_boxes"].remove(e)
    resultados.append(d)
  return resultados

#Funcion para detectar establecimientos comerciales (solo funciona en Google Colab)
def detectar_establecimientos_yolov4(img_list):
  if os.path.exists("results.json"):
    os.remove("results.json")
  #detectar establecimientos
  #%cd darknet
  #!./darknet detector test '{DIR_YOLO_META}' '{DIR_YOLO_CONFIG}' '{DIR_YOLO_WEIGHTS}' -ext_output -dont_show -out ../results.json < ../input.txt 
  #%cd ..
  predicciones = leer_json_detecciones('results.json')
  return predicciones

#Funcion para guardar imagenes con sus bbs detectados
def guardar_detecciones(detecciones, dir_output= 'output_yolov4'):
  os.makedirs(dir_output, exist_ok=True)
  for d in detecciones:
    bounding_boxes = d["bounding_boxes"]
    image = cv2.imread(d["img_path"])
    color = (36, 250, 136) 
    for bb in bounding_boxes:      
      x1, y1, x2, y2 = bb[0], bb[1], bb[2], bb[3]      
      cv2.rectangle(image, (x1,y1), (x2,y2),color, 2)
      cv2.putText(image, "establecimiento", (x1, y1 - 5), cv2.FONT_HERSHEY_PLAIN, 1, [36, 250, 136], 2)
    cv2.imwrite("{}/{}.png".format(dir_output,d["filename"]), image)

