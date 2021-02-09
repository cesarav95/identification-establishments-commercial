from pyproj import Proj, Transformer
import math
import csv
from PIL import Image

def calcular_distancia_puntos(p1,p2):
  return math.sqrt((p1[0] - p2[0] ) * (p1[0] - p2[0] ) + (p1[1] - p2[1] ) * (p1[1] - p2[1] ))

#funcion para convertir un punto a otro sistema de referencia
def convertir_punto_crs(punto, crs_from, crs_to):
  transformer = Transformer.from_crs(crs_from, crs_to)
  return transformer.transform(punto[0], punto[1])

def recuperar_crop_imagen_bb(path_img, bb):
  img = Image.open(path_img).convert('RGB')
  img_crop = img.crop(bb[:4])
  return img_crop