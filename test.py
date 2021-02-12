import craft_test as craft
import atten_ocr_test as ocr
import similarity as sim
import utils
import object_location as objl
import detection_ec as det_ec
import classification_ec as class_ec
import os
import csv

DIR_YOLO_CONFIG = '/content/identification-of-establishments-commercial/config/yolov4-custom_ec.cfg'
DIR_YOLO_WEIGHTS = '/content/identification-of-establishments-commercial/yolov4-custom_ec.weights'
DIR_YOLO_META = '/content/identification-of-establishments-commercial/config/obj.data'
BATCH_YOLO = 1
NET_INPUT_SIZE = 608
IMG_INPUT_SIZE = 640
IMG_INPUT_WIDTH = 640
IMG_INPUT_HEIGTH = 640
#SIMILARIDAD
DIR_PTH_SIMILARIDAD = '/content/identification-of-establishments-commercial/vgg16_bn_sim_ec.pth'
THRESH_SIMILARIDAD = 0.40
THRESH_DIST_ENTRE_IMGS = 15

# RECONOCIMENTO TEXTO
DIR_PB_ATTEN_OCR = '/content/identification-of-establishments-commercial/text_recognition_5435.pb'
DIR_PTH_CRAFT = '/content/identification-of-establishments-commercial/craft_mlt_25k.pth'

DIR_PTH_CLASIFICACION = "/content/identification-of-establishments-commercial/vgg16_bn_class_ec.pth"
class_names =  ['boticas y farmacias', 'lugares de comida y bebida', 'lugares de estetica y cuidado', 'otros', 'sin negocios', 'tiendas de materiales de construccion', 'tiendas de productos de primera necesidad', 'tiendas de vestir']
class_to_idx = {'boticas y farmacias': 0, 'lugares de comida y bebida': 1, 'lugares de estetica y cuidado': 2, 'otros': 3, 'sin negocios': 4, 'tiendas de materiales de construccion': 5, 'tiendas de productos de primera necesidad': 6, 'tiendas de vestir': 7}
idx_to_class = { v : k for k,v in class_to_idx.items()}
DIR_DICCIONARIO = "/content/identification-of-establishments-commercial/config/diccionario_ec.txt"

# DATOS DE ENTRADA
DIR_IMGS = '/content/drive/MyDrive/input_images_gsv'
DIR_CSV_IMGS_GSV = '/content/drive/MyDrive/input_images_gsv/metadata.csv'
#DIR_IMGS = '/content/drive/My Drive/TESIS/input_images_gsv'
#DIR_CSV_IMGS_GSV = '/content/drive/My Drive/TESIS/input_images_gsv/metadata.csv'
DIR_OUTPUT_JSON_PRED = '/content/final_pred_ec.json'
#Test
DIR_JSON_GT = 'input_pred_ec.json'
DIR_OUTPUT_JSON_GT = 'input_gt_ec.json'


def obtener_puntos_cercanos(punto_central, lista_puntos ,radio = 5):  
  indices_cercanos = []
  distancias_cercanos = []
  print("OBTENIENDO PUNTOS CERCANOS")
  for i in range(len(lista_puntos)):
    obj_gt = lista_puntos[i]
    punto_gt_lat_lon = obj_gt["location"]
    #punto_gt = convertir_punto_de_4326_a_24879(punto_gt_lat_lon)
    punto_gt = utils.convertir_punto_crs(punto_gt_lat_lon,4326,24879) 
    distancia = utils.calcular_distancia_puntos(punto_central, punto_gt)
    if distancia <= radio:
      indices_cercanos.append(i)
      distancias_cercanos.append(distancia)
  return indices_cercanos,distancias_cercanos

def calcular_metricas_clasificacion(c_name, list_gt,list_pred,ouput_path_csv,criterio, top_k = 3):
  TP = 0
  TN = 0
  FP = 0
  FN = 0
  tmp_list_pred = list_pred["objetos"].copy()
  tmp_list_gt = list_gt["objetos"].copy()
  TN = list_pred["TN"]    
  print("CALCULANDO METRICAS DE CLASIFICACION")
  for index in range(len(list_pred["objetos"])):
      obj = list_pred["objetos"][index]
      #SI la la mejor prediccion pertenece a la clases SIN NEGOCIO BORRAR EL OBJETO
      if obj["clase"]["class_idx"][0] == 4 and obj["clase"]["prob"][0]>=0.8:
          tmp_list_pred.remove(obj)
      else:
          punto_central_lat_lon = obj["location"]
          punto_central = utils.convertir_punto_crs(punto_central_lat_lon,4326,24879)   
          print("LONGITUD DE GT: ", len(tmp_list_gt))   
          index_puntos_cercanos, distancias_puntos_cercanos = obtener_puntos_cercanos(punto_central,tmp_list_gt)
          distancia_menor = 9999
          indice_mas_cercano = -1
          existe_compatibles = False
          print("BUSCANDO EN INDICES CERCANOS......")
          for i,indice_cercano in enumerate(index_puntos_cercanos):
              obj_gt = tmp_list_gt[indice_cercano]
              clase_gt = int(obj_gt["clase"]["class_idx"][0])
              clases_pred = obj["clase"]["class_idx"][:top_k]
              if clase_gt in clases_pred:
                  if distancias_puntos_cercanos[i] < distancia_menor:
                      existe_compatibles = True
                      indice_mas_cercano = indice_cercano
                      distancia_menor = distancias_puntos_cercanos[i]
          if existe_compatibles:
              TP = TP + 1
              tmp_list_gt.pop(indice_mas_cercano)
              tmp_list_pred.remove(obj)    
  print("CALCULANDO METRICAS..................") 
  FP = FP + len(tmp_list_pred)
  FN = FN + len(tmp_list_gt)   
  precision = TP/(TP+FP)
  recall = TP/(TP+FN)
  accuracy = (TP + TN)/(TP+FP+TN+FN)
  F1 = 2*(recall*precision)/(recall + precision) 
  datos = [c_name,criterio, TP,TN,FP,FN,precision,recall,accuracy,F1]
  print(datos)
  with open(ouput_path_csv,'a',newline='') as csvfile:
    writer = csv.writer(csvfile,delimiter=';')
    writer.writerow(datos)

def calcular_metricas_deteccion(c_name, list_gt,list_pred,ouput_path_csv,criterio):
  TP = 0
  TN = 0
  FP = 0
  FN = 0
  tmp_list_pred = list_pred["objetos"].copy()
  tmp_list_gt = list_gt["objetos"].copy()
  TN = list_pred["TN"]    
  for index in range(len(list_pred["objetos"])):
      obj = list_pred["objetos"][index]
      punto_central_lat_lon = obj["location"]
      punto_central = utils.convertir_punto_crs(punto_central_lat_lon,4326,24879)         
      index_puntos_cercanos, distancias_puntos_cercanos = obtener_puntos_cercanos(punto_central,tmp_list_gt)
      distancia_menor = 9999
      indice_mas_cercano = -1
      existe_compatibles = False
      for i,indice_cercano in enumerate(index_puntos_cercanos):
          obj_gt = tmp_list_gt[indice_cercano]
          if distancias_puntos_cercanos[i] < distancia_menor:
              existe_compatibles = True
              indice_mas_cercano = indice_cercano
              distancia_menor = distancias_puntos_cercanos[i]
      if existe_compatibles:            
          TP = TP + 1
          tmp_list_gt.pop(indice_mas_cercano)
          tmp_list_pred.remove(obj)                    
  FP = FP + len(tmp_list_pred)
  FN = FN + len(tmp_list_gt)
  precision = TP/(TP+FP)
  recall = TP/(TP+FN)
  accuracy = (TP + TN)/(TP+FP+TN+FN)
  F1 = 2*(recall*precision)/(recall + precision)
  datos = [c_name,criterio, TP,TN,FP,FN,precision,recall,accuracy,F1]
  with open(ouput_path_csv,'a',newline='') as csvfile:
    writer = csv.writer(csvfile,delimiter=';')
    writer.writerow(datos)
   

def leer_path_data(path, output_path):
  list_paths_files = []
  if not os.path.exists(output_path): # Si no existe crear la carpeta de salida
    os.makedirs(output_path)
  list_carpetas = os.listdir(path)# obtener lista de nombres archivos del directorio path
  for c in list_carpetas:
    folder_path = path +'/'+ c
    print("Reading... ",folder_path)
    list_imgs = os.listdir(folder_path)
    print("Imagenes: ",len(list_imgs))
    file_path = output_path+"/"+c+".txt"
    list_paths_files.append(file_path)
    if os.path.exists(file_path):
      os.remove(file_path)
    file_input = open(file_path, "w")
    for dir in list_imgs:
      if '.jpg' in dir or '.png' in dir: 
        img_path = folder_path + "/" + dir            
        file_input.write(img_path) 
        file_input.write("\n")
    file_input.close()
  return list_paths_files

def leer_json_gt_procesado(path_json_file):
  #Leer json resultados
  data = {}
  with open(path_json_file) as f:
    data = json.load(f)
  return data

def calcular_TN(lista_imagenes, pred, gt):
  TN = 0
  for img in lista_imagenes:
    filename = img.split('/')[-1]
    if pred[filename] == 0  and gt[filename] == 0:
      TN = TN + 1
  return TN

def analizar_datos(input_imgs_data,input_txt_path, metadata_path,gts_path,output_path):

  resultado_final_pred={}
  resultado_final_gt = {}
  if not os.path.exists(output_path): # Si no existe crear la carpeta de salida
    os.makedirs(output_path)
  list_input = os.listdir(input_txt_path)
  for c in list_input:
    c_path = input_txt_path+'/'+c
    print(c_path)
    c_name = c.replace('.txt','')
    c_output = output_path+'/result_'+c_name+'.json'
    metadata_csv_path = metadata_path + '/' + c_name +'.csv'
    #===========================================================================
    # ANALIZAR PREDICCIONES
    #===========================================================================
    detecciones_yolo = det_ec.detectar_establecimientos_yolov4(c_path, c_output)
    total_imagenes = len(detecciones_yolo)
    #OBTENER INFORMACION DE METADATA DE LAS IMAGENES
    datos_csv, lista_imagenes = objl.leer_csv_imagenes_gsv(metadata_csv_path)
    #ELIMINAR BOUNDING BOXES CONTENIDO EN OTROS
    predicciones_yolo_tmp = det_ec.eliminar_bb_contenidos(detecciones_yolo)
    #AGRUPAR OBJETOS REPETIDOS 
    objetos_finales, imgs_sin_objetos_pred, imagenes_bbs_pred = sim.agrupar_objetos_similares(predicciones_yolo_tmp, datos_csv,DIR_PTH_SIMILARIDAD)
    #DETECTAR LETREROS EN LAS IMAGENES Y SACAR PALABRAS
    objetos_finales_ocr = class_ec.obtener_textos_objetos(objetos_finales)
    #CLASIFICAR OBJETOS
    objetos_finales_clasificados = class_ec.clasificar_objetos_detectados(objetos_finales_ocr, DIR_PTH_CLASIFICACION, DIR_DICCIONARIO, False)
    # UBICACIONES GEOGRAFICAS PREDICCIONES YOLO
    ubicaciones_geograficas = objl.calcular_ubicacion_geografica_detecciones(objetos_finales_clasificados,datos_csv)
    resultado_final_pred = {"nro_imagenes": total_imagenes, "imgs_sin_objetos":imgs_sin_objetos_pred,"objetos":ubicaciones_geograficas}
    print("TOTAL OBJETOS DETETCTADOS : ", len(resultado_final_pred["objetos"]))

    #===========================================================================
    # ANALIZAR GROUND TRUTH
    #===========================================================================
    # ANALIZAR GT
    gt_path = gts_path +'/'+c_name+'/'+c_name+'.json'
    #json_gt = leer_json_gt(gt_path)
    #imgs_path = input_imgs_data +'/'+ c_name
    #bb_gt = obtener_gt_test(lista_imagenes,json_gt,input_imgs_data+'/'+c_name)
    #total_imagenes_gt = len(bb_gt)
    #objetos_finales_gt,imgs_sin_objetos_gt,imagenes_bbs_gt = agrupar_objetos_similares(bb_gt,datos_csv, tipoconsulta='GT')
    #locations_gt = calcular_ubicacion_geografica_detecciones(objetos_finales_gt,datos_csv)
    #resultado_final_gt = {"nro_imagenes": total_imagenes_gt, "imgs_sin_objetos":imgs_sin_objetos_gt,"objetos":locations_gt}
    #print("TOTAL OBJETOS GT : ", len(resultado_final_gt["objetos"]))
    #GROUND TRUTH CORREGIDO

    #gt_path = gts_path +'/'+c_name+'/'+c_name+'.json'
    #json_gt = leer_json_gt_procesado(gt_path)
    #imgs_path = input_imgs_data +'/'+ c_name
    #bb_gt = obtener_gt_test(lista_imagenes,json_gt,input_imgs_data+'/'+c_name)

    #objetos_finales_gt,imgs_sin_objetos_gt,imagenes_bbs_gt = agrupar_objetos_similares(bb_gt,datos_csv, tipoconsulta='GT')
    #gt_path = gts_path +'/'+c_name+'/gt-'+c_name+'.json'
    resultado_final_gt = leer_json_gt_procesado(gt_path)
    #===========================================================================
    # METRICAS
    #===========================================================================
    list_imagenes = os.listdir(input_imgs_data+'/'+c_name)
    TN = calcular_TN(list_imagenes, imagenes_bbs_pred, imagenes_bbs_gt)
    resultado_final_pred["TN"] = TN
    #Guardar resultados en un archivo csv
    file_name_csv_output = output_path +'/results_ocr.csv'
    #break
    if not os.path.exists(file_name_csv_output):
      with open(file_name_csv_output,'w',newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['CALLE','CRITERIO' ,'TP', 'TN','FP','FN','PRESICION','RECALL','ACCURACY','F1','TP', 'TN','FP','FN','PRESICION','RECALL','ACCURACY','F1'])
    calcular_metricas_clasificacion(c_name,resultado_final_gt,resultado_final_pred,file_name_csv_output,'CLASIFICACION TOP 1',top_k = 1)
    calcular_metricas_clasificacion(c_name,resultado_final_gt,resultado_final_pred,file_name_csv_output,'CLASIFICACION TOP 3',top_k = 3)
    calcular_metricas_clasificacion(c_name,resultado_final_gt,resultado_final_pred,file_name_csv_output,'CLASIFICACION TOP 5',top_k = 5)
    calcular_metricas_deteccion(c_name,resultado_final_gt,resultado_final_pred,file_name_csv_output,'DETECCION')
  return resultado_final_pred, resultado_final_gt
