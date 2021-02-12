from pyproj import Proj, transform
import math
import os
import urllib
import json
from PIL import Image
import csv
import os.path
#WEB DRIVER
#from selenium import webdriver
import time

#INICIALIZAR WEB DRIVER
#chromedriver = "C:/Users/Cesar/Desktop/chromedriver"
#os.environ["webdriver.chrome.driver"] = chromedriver
#driver = webdriver.Chrome(chromedriver)

#driver.maximize_window()
#driver.set_window_size(1040,708)#(WSVGA) 1024 x 576
#driver.set_window_size(1296,852)#(HD/WXGA)
#estilos_css_js = "document.getElementsByClassName('scene-footer')[0].style.visibility = 'hidden';document.getElementById('image-header').style.visibility = 'hidden'; document.getElementById('watermark').style.visibility = 'hidden'; document.getElementById('content-container').getElementsByClassName('app-viewcard-strip')[0].style.visibility = 'hidden'; document.getElementById('titlecard').style.visibility = 'hidden'"

#PARAMETROS
 
# - API GOOGLE 
#URL_BASE_IMAGEN_GSV = "https://www.google.com/maps/@?api=1&map_action=pano&"
URL_BASE_IMAGE = "https://maps.googleapis.com/maps/api/streetview"
URL_BASE_METADATA = "https://maps.googleapis.com/maps/api/streetview/metadata"
API_KEY = "YOUR API KEY"
nombre_carpeta_salida = "output" # Directorio de salida de las imagenes
usar_heading = True
#MAPA OSM
nombre_capa_lines = "input lines"
nombre_capa_polygons = "input multipolygons"
osm_id_ruta="4821015"
# - CAPAS 
nombre_capa_centro = 'center_points_layer'
fields_capa_centro = ['x', 'y', 'type', 'panoid_filename']
types_fields_capa_centro = ['Double', 'Double','String', 'String']

nombre_capa_izquierda = "left_points_layer"
nombre_capa_derecha = "right_points_layer"
#nombre_capa_metadatos = "metadatos_points_layer"
#fields_capa_metadatos = ['x', 'y', 'osm_id_calle','dist_a_fachada','heading','fov','vector_unit_x','vector_unit_y']
fields_capa_der_iz = ['x', 'y', 'en_poligono', 'osm_id_calle','dist_a_fachada','heading','fov','vector_unit_x','vector_unit_y','seg_i_x', 'seg_i_y', 'seg_f_x', 'seg_f_y']
types_fields_capa_der_iz = ['String', 'String','Int', 'String','Double', 'Double','Double','Double', 'Double','Double', 'Double','Double', 'Double',]
#types_fields_capa_metadatos = ['String', 'String', 'String','Double', 'Double','Double','Double', 'Double']
# - PARAMETROS DE CALCULO PARA LOS PUNTOS DE REFERENCIA
dist_entre_puntos = 2
dist_inicial_a_fachada = 2
step = 1
max_dist_a_fachada = 12#20
dist_sin_fachada= 5
dist_prom_sin_fachadas = True
generar_csv = True
# - FOV
min_fov = 90
max_fov = 40
dist_min_fov = 5
dist_max_fov = 8
usar_dist_prom_fov = True
#GRID
tam_celda = 80

# funcion para recuperar una capa por su nombre
def obtener_capa_por_nombre(nombre):
    capa=None
    for c in QgsProject.instance().mapLayers().values():
        if c.name() == nombre:
            capa = c
            break
    return capa   

#funcion que verifica si una capa existe
def existe_capa(nombre):
    capa=None
    for c in QgsProject.instance().mapLayers().values():
        if c.name() == nombre:
            return True
    return False 

#funcion para crear una capa vectorial, pr defecto creo una capa vectorial de tipo Point y el sistema de referencia EPSG4326
def crear_vector_layer(nombre_capa,nombres_atributos,tipos_atributos, crs='4326', tipo='Point'):
    parametros = tipo+"?crs=EPSG:"+crs
    nueva_capa = QgsVectorLayer(parametros,nombre_capa,"memory")
    dp = nueva_capa.dataProvider()
    atributos = []
    for i in range(len(nombres_atributos)):
        if(tipos_atributos[i] == "Int"):
            atributos.append(QgsField(nombres_atributos[i],QVariant.Int))
        elif(tipos_atributos[i] == "Double"):
            atributos.append(QgsField(nombres_atributos[i],QVariant.Double))
        elif(tipos_atributos[i] == "Bool"):
            atributos.append(QgsField(nombres_atributos[i],QVariant.Bool))
        else:
            atributos.append(QgsField(nombres_atributos[i],QVariant.String))
    dp.addAttributes(atributos)  
    nueva_capa.updateFields()
    QgsProject.instance().addMapLayer(nueva_capa)
    return nueva_capa

#funcion para convertir un punto a otro sistema de referencia
def convertir_punto_crs(punto, crs_from, crs_to):
    crsScr = QgsCoordinateReferenceSystem(crs_from) #definir sistema de coordenada origen
    crsDest = QgsCoordinateReferenceSystem(crs_to) #definir sistema de coordenada destino
    xform = QgsCoordinateTransform(crsScr,crsDest, QgsProject.instance())
    return xform.transform(QgsPointXY(punto.x(),punto.y()))
#funcion para convertir del sistemas 24879() a 4326(LAT, LON)
def convertir_punto_de_24879_a_4326(punto):
    return convertir_punto_crs(punto, 24879, 4326)

#funcion para convertir del sistemas 4326(LAT, LON) a 24879() 
def convertir_punto_de_4326_a_24879(punto):
    #print("CONVERSIN")
    #print(punto)
    return convertir_punto_crs(punto, 4326, 24879)

#funcion para agregar un feature a una capa
def agregar_feature_capa(capa, geometria, val_atributos):
    if(len(val_atributos) != len(list(capa.fields()))):
        raise TypeError("El numero de atributos no coincide con el numero de campos de la capa.")
    feature = QgsFeature() #crear feature
    feature.setFields(capa.fields()) #asignar campos
    feature.setGeometry(geometria) #asignar geometria
    #Asignar valores de los atributos
    for i, atr in enumerate(val_atributos):
        feature.setAttribute(i,atr)
    capa.dataProvider().addFeature(feature) # agregar feature a la capa

#funcion para calcular distancia entre puntos
def calcular_distancia_puntos(p1,p2):
    return math.sqrt((p1.x() - p2.x()) * (p1.x() - p2.x()) + (p1.y() - p2.y()) * (p1.y() - p2.y()))

#funcion para calcular punto a una distancia de otro
def calcular_punto_a_distancia(pinicial, distancia, v_unit):  
    x = pinicial.x() + distancia * v_unit.x()
    y = pinicial.y() + distancia * v_unit.y()
    return QgsPointXY(x,y)
#Calculo de heading
def calcular_heading(punto_inicial, punto_final):

    #===============================================================
    punto_inicial = convertir_punto_de_4326_a_24879(punto_inicial)  
    punto_final = convertir_punto_de_4326_a_24879(punto_final)  
    teta1 = math.radians(punto_inicial.y())
    teta2 = math.radians(punto_final.y())
    delta1 = math.radians(punto_final.y()-punto_inicial.y())
    delta2 = math.radians(punto_final.x()-punto_inicial.x())
    y = math.sin(delta2) * math.cos(teta2)
    x = math.cos(teta1)*math.sin(teta2) - math.sin(teta1)*math.cos(teta2)*math.cos(delta2)
    brng = math.atan2(y,x)
    brng = math.degrees(brng)
    return brng
    #===============================================================


    #heading_value = math.atan2(punto_final.x() - punto_inicial.x(), punto_final.y() - punto_inicial.y())
    #heading_value = math.degrees(heading_value)
    #return heading_value
def calcular_fov(distancia_prom):
    if(distancia_prom<=8):
        return (distancia_prom-5)*(-50/3)+90
    else:
        return (dist_max_fov - 5)*(-50/3)+90
    #fov = math.atan(5/distancia_prom)*2
    #fov_grados = math.degrees(fov)
    #return fov_grados

def ajustar_parametros(array_puntos, distancia_prom, v_unit, direccion):
    for i,arr in enumerate(array_puntos):
        if(arr[2] == 0 or usar_dist_prom_fov):# SI no existe poligono (fachada) o usar distancia promedio
            punto_lat_lon = QgsPointXY(arr[0],arr[1])
            punto = convertir_punto_de_4326_a_24879(punto_lat_lon)            
            new_point_x = punto.x() + direccion*v_unit.x()*(distancia_prom - arr[4])
            new_point_y = punto.y() + direccion*v_unit.y()*(distancia_prom - arr[4])
            array_puntos[i][4] = distancia_prom
            punto = QgsPointXY(new_point_x,new_point_y)
            new_fov = calcular_fov(distancia_prom)
            punto_lat_lon = convertir_punto_de_24879_a_4326(punto) 
            array_puntos[i][0] = punto_lat_lon.x()
            array_puntos[i][1] = punto_lat_lon.y()
            array_puntos[i][6] = new_fov
    return array_puntos
def guardar_puntos_capa(capa,datos_puntos):
    for arr in datos_puntos:
        punto = QgsPointXY(arr[0],arr[1])
        #print(arr)
        agregar_feature_capa(capa,QgsGeometry.fromPointXY(punto),arr)

#Inicializar grid
def crear_grid(filas, columnas):
    grid = []
    for i in range(filas):
        fila = []
        for j in range(columnas):
            fila.append(set())
        grid.append(fila)
    return grid

# Funcion para calcular a que celda del grid se encuentra un punto
def calcular_indice_grid(lim_min, punto):
    lim_min = convertir_punto_de_4326_a_24879(lim_min)    
    dist_x = calcular_distancia_puntos(QgsPointXY(lim_min.x(),punto.y()),QgsPointXY(punto.x(),punto.y()))
    dist_y = calcular_distancia_puntos(QgsPointXY(punto.x(),lim_min.y()),QgsPointXY(punto.x(),punto.y()))
    indice_y = int(dist_y / tam_celda)
    indice_x = int(dist_x / tam_celda)
    return indice_x, indice_y 

def calcular_punto_cercano_a_fachada(lista_poligonos,punto_central,grid,v_unit, lim_inf_map,osm_id_calle, direccion):
    #Veficar si existen poligonos en el mapa
    if(len(lista_poligonos)> 0):
        #print("SI EXISTE POLIGONOS EN EL MAPA")
        #iniciar en un punto a una distancia determinada por la variable dist_inicial_a_fachada
        px = punto_central.x() + direccion*dist_inicial_a_fachada*v_unit.x()
        py = punto_central.y() + direccion*dist_inicial_a_fachada*v_unit.y()
        punto_ref = QgsPointXY(px, py)
        punto_ref_lat_lon = convertir_punto_de_24879_a_4326(punto_ref)
        #obtener indice del grid
        index_x, index_y = calcular_indice_grid(lim_inf_map, punto_ref)
        lista_pol_cercanos = grid[index_y][index_x]
        distancia_recorrida = dist_inicial_a_fachada
        #indice_pol_cercano = list(lista_pol_cercanos)[0]
        indice_pol_cercano = 0 #inicializar poligno mas cercano con el primero de la lista
        #calcular distancia entre punto de referencia y el poligono mas cercano
        poligono_cercano = lista_poligonos[indice_pol_cercano].geometry()
        min_distancia =  poligono_cercano.distance(QgsGeometry.fromPointXY(punto_ref_lat_lon))
        #Buscar poligono mas cercano
        while(not poligono_cercano.contains(QgsGeometry.fromPointXY(punto_ref_lat_lon)) and distancia_recorrida <= max_dist_a_fachada):
            #iavanzar hacia el poligono a una distancia determinada por la variable step
            px = punto_ref.x() + direccion*step*v_unit.x()
            py = punto_ref.y() + direccion*step*v_unit.y()
            punto_ref = QgsPointXY(px, py)
            punto_ref_lat_lon = convertir_punto_de_24879_a_4326(punto_ref)
            #obtener indice del grid
            index_x, index_y = calcular_indice_grid(lim_inf_map, punto_ref)
            lista_pol_cercanos = grid[index_y][index_x]
            distancia_recorrida = distancia_recorrida + step
            #comparar con todos los poligonos
            for index_pol in lista_pol_cercanos:
                poligono = lista_poligonos[index_pol].geometry()
                nueva_dist_min = poligono.distance(QgsGeometry.fromPointXY(punto_ref_lat_lon))
                if (nueva_dist_min < min_distancia):
                    indice_pol_cercano = index_pol
                    min_distancia = nueva_dist_min
            poligono_cercano = lista_poligonos[indice_pol_cercano].geometry()  
        existe_poligono_cercano = False
        #verificar si encontro algun poligono
        if(not poligono_cercano.contains(QgsGeometry.fromPointXY(punto_ref_lat_lon))):
            distancia_a_poligono = dist_sin_fachada        
        else:
            existe_poligono_cercano = True
            distancia_a_poligono = distancia_recorrida  
        px = punto_central.x() + direccion*distancia_a_poligono*v_unit.x()
        py = punto_central.y() + direccion*distancia_a_poligono*v_unit.y()
        punto_ref = QgsPointXY(px, py)    
    else:
        print("NO EXISTE POLIGONOS EN EL MAPA")
        existe_poligono_cercano = False
        distancia_a_poligono = dist_sin_fachada 
        px = punto_central.x() + direccion*distancia_a_poligono*v_unit.x()
        py = punto_central.y() + direccion*distancia_a_poligono*v_unit.y()
        punto_ref = QgsPointXY(px, py)

    return punto_ref, distancia_a_poligono,existe_poligono_cercano

#Funcion para calcular puntos de referencia de las calles
def calcular_puntos_referencia(lista_poligonos,capa_derecha, capa_izquierda, punto_central,v_unit,grid,lim_inf_map,osm_id_calle, v_unit_calle):
    datos_der = []
    datos_iz = []
    punto_central_lat_lon = convertir_punto_de_24879_a_4326(punto_central)
    # Calcular punto referencia para el lado DERECHO
    punto_ref_der, distancia_a_fachada_der,existe_pol_der = calcular_punto_cercano_a_fachada(lista_poligonos,punto_central,grid,v_unit,lim_inf_map,osm_id_calle,1)
    punto_ref_der_lat_lon = convertir_punto_de_24879_a_4326(punto_ref_der)
    fov_der = calcular_fov(distancia_a_fachada_der)
    heading_der = calcular_heading(punto_central_lat_lon,punto_ref_der_lat_lon)
    if(existe_pol_der): 
        datos_der = [punto_ref_der_lat_lon.x(),punto_ref_der_lat_lon.y(),1,osm_id_calle,distancia_a_fachada_der, heading_der,fov_der, v_unit_calle.x(), v_unit_calle.y()]       
    else:
        datos_der = [punto_ref_der_lat_lon.x(),punto_ref_der_lat_lon.y(),0,osm_id_calle,distancia_a_fachada_der, heading_der,fov_der, v_unit_calle.x(), v_unit_calle.y()]       

    # Calcular punto referencia para el lado IZQUIERDO
    punto_ref_iz, distancia_a_fachada_iz,existe_pol_iz = calcular_punto_cercano_a_fachada(lista_poligonos,punto_central,grid,v_unit,lim_inf_map,osm_id_calle,-1)
    punto_ref_iz_lat_lon = convertir_punto_de_24879_a_4326(punto_ref_iz)
    fov_iz = calcular_fov(distancia_a_fachada_iz)
    heading_iz = calcular_heading(punto_central_lat_lon,punto_ref_iz_lat_lon)
    if(existe_pol_iz):  
        datos_iz = [punto_ref_iz_lat_lon.x(),punto_ref_iz_lat_lon.y(),1,osm_id_calle,distancia_a_fachada_iz, heading_iz,fov_iz,v_unit_calle.x(), v_unit_calle.y()]      
    else:
        datos_iz = [punto_ref_iz_lat_lon.x(),punto_ref_iz_lat_lon.y(),0,osm_id_calle,distancia_a_fachada_iz, heading_iz,fov_iz,v_unit_calle.x(), v_unit_calle.y()]      

    return datos_der,datos_iz

#Calcular puntos para la descarga de imagenes de GSV
def calcular_puntos_calle(layer_poligonos ,calles, capa_puntos,capa_puntos_der, capa_puntos_iz, grid, limite_inferior_map):    
    lista_poligonos = list(layer_poligonos.getFeatures())    
    for calle in calles:
        distancia_total_der = 0
        distancia_total_iz = 0
        contador_puntos_der = 0
        contador_puntos_iz = 0
        distancia_promedio_der = 0
        distancia_promedio_iz = 0
        osm_id_calle = calle["osm_id"]
        #osm_id_calle = "giraldo"
        
        # obtener lista de puntos de la calle (geometria de la calle)
        list_puntos = list(calle.geometry().get())
        #print(list_puntos)
        # recorrer lineas
        for index in range(len(list_puntos)-1):
            #convertir sistema de referencia (coordenadas)         
            punto_inicial = convertir_punto_de_4326_a_24879(list_puntos[index])
            punto_final = convertir_punto_de_4326_a_24879(list_puntos[index + 1])
            nuevo_punto = punto_inicial
            datos_puntos_calle_der = []
            datos_puntos_calle_iz = []
            # calcular distancia entre puntos
            dt = calcular_distancia_puntos(punto_inicial, punto_final)

            #Calcular vector unitario
            #determinamos el vector entre los dos puntos
            vx=punto_final.x()-punto_inicial.x()
            vy=punto_final.y()-punto_inicial.y()
            #determinamos el modulo de v
            modulo_v=math.sqrt((vx)**2+(vy)**2)
            #vector unitario
            ux=vx/modulo_v
            uy=vy/modulo_v
            v_unitario = QgsPoint(ux,uy)
            #vector unitario ortogonal
            v_unit_ortogonal = QgsPoint(uy,-ux)
            #calcular puntos para obtener imagenes de GSV
            while(round(dt)>= dist_entre_puntos):
                if(round(dt) == dist_entre_puntos):
                    #agregar punto final dela linea  al capa puntos
                    puntof = convertir_punto_de_24879_a_4326(punto_final)
                    agregar_feature_capa(capa_puntos,QgsGeometry.fromPointXY(puntof),[puntof.x(),puntof.y(),' ',' '])     

                    #calcular puntos de referencia - derecha e izquierda del punto de la calle                   
                    datos_der, datos_iz = calcular_puntos_referencia(lista_poligonos,capa_puntos_der,capa_puntos_iz,punto_final,v_unit_ortogonal,grid,limite_inferior_map,osm_id_calle,v_unitario)
                    #guardar segmento de linea al que pertenece el punto de referencia
                    datos_iz.append(punto_inicial.x())
                    datos_iz.append(punto_inicial.y())
                    datos_der.append(punto_inicial.x())
                    datos_der.append(punto_inicial.y())
                    datos_iz.append(punto_final.x())
                    datos_iz.append(punto_final.y())
                    datos_der.append(punto_final.x())
                    datos_der.append(punto_final.y())
                    #guardar datos
                    datos_puntos_calle_der.append(datos_der)
                    datos_puntos_calle_iz.append(datos_iz)   
                    if(datos_der[2] == 1):# Si existe un poligono(fachada)- lado derecho
                        contador_puntos_der = contador_puntos_der + 1
                        distancia_total_der = distancia_total_der + datos_der[4]
                    if(datos_iz[2] == 1):# Si existe un poligono(fachada)- lado izquierdo
                        distancia_total_iz = distancia_total_iz + datos_iz[4]
                        contador_puntos_iz = contador_puntos_iz + 1
                    
                else:
                    # calcular punto en la recta a n metros                    
                    nuevo_punto = calcular_punto_a_distancia(nuevo_punto,dist_entre_puntos, v_unitario)                    
                    np = convertir_punto_de_24879_a_4326(nuevo_punto)
                    agregar_feature_capa(capa_puntos,QgsGeometry.fromPointXY(np),[np.x(),np.y(),' ',' '])
                    #calcular puntos de referencia - derecha e izquierda del punto de la calle
                    datos_der, datos_iz = calcular_puntos_referencia(lista_poligonos,capa_puntos_der,capa_puntos_iz,nuevo_punto,v_unit_ortogonal,grid,limite_inferior_map,osm_id_calle,v_unitario)
                    #guardar segmento de linea al que pertenece el punto de referencia
                    datos_iz.append(punto_inicial.x())
                    datos_iz.append(punto_inicial.y())
                    datos_der.append(punto_inicial.x())
                    datos_der.append(punto_inicial.y())
                    datos_iz.append(punto_final.x())
                    datos_iz.append(punto_final.y())
                    datos_der.append(punto_final.x())
                    datos_der.append(punto_final.y())
                    #Guardar informacion de los puntos de referencia
                    datos_puntos_calle_der.append(datos_der)
                    datos_puntos_calle_iz.append(datos_iz)   
                    if(datos_der[2] == 1 or dist_prom_sin_fachadas):# Si existe un poligono(fachada)- lado derecho
                        contador_puntos_der = contador_puntos_der + 1
                        distancia_total_der = distancia_total_der + datos_der[4]
                    if(datos_iz[2] == 1 or dist_prom_sin_fachadas):# Si existe un poligono(fachada)- lado izquierdo
                        distancia_total_iz = distancia_total_iz + datos_iz[4]
                        contador_puntos_iz = contador_puntos_iz + 1
                dt = dt - dist_entre_puntos


            if(contador_puntos_der >0):
                distancia_promedio_der =  distancia_total_der / contador_puntos_der
                datos_puntos_calle_der = ajustar_parametros(datos_puntos_calle_der,distancia_promedio_der,v_unit_ortogonal,1)
                print("DISTANIA_PROM DER: ", distancia_promedio_der)
            if(contador_puntos_iz >0):
                distancia_promedio_iz = distancia_total_iz / contador_puntos_iz
                datos_puntos_calle_iz = ajustar_parametros(datos_puntos_calle_iz,distancia_promedio_iz,v_unit_ortogonal,-1)
                print("DISTANIA_PROM IZ: ", distancia_promedio_iz)
            guardar_puntos_capa(capa_puntos_der,datos_puntos_calle_der)
            guardar_puntos_capa(capa_puntos_iz,datos_puntos_calle_iz)

def obtener_calles_id_nombre(capa_calles, nombre_calle):
    features = capa_calles.getFeatures()
    calles = []
    #filtrar features de la capa
    for f in features:
        if(f["name"] == nombre_calle or f["osm_id"]== nombre_calle):
            calles.append(f)
            print(f["name"])
    return calles
    
def inicializar_capas():
    #Crear capas vectoriales
    if not existe_capa(nombre_capa_centro):
        capa_centro = crear_vector_layer(nombre_capa_centro, fields_capa_centro, types_fields_capa_centro)
    else:
        capa_centro = obtener_capa_por_nombre(nombre_capa_centro)
        capa_centro.dataProvider().truncate()
    if not existe_capa(nombre_capa_derecha):
        capa_derecha = crear_vector_layer(nombre_capa_derecha, fields_capa_der_iz, types_fields_capa_der_iz)
    else:
        capa_derecha = obtener_capa_por_nombre(nombre_capa_derecha)
        capa_derecha.dataProvider().truncate()
    if not existe_capa(nombre_capa_izquierda):
        capa_izquierda = crear_vector_layer(nombre_capa_izquierda, fields_capa_der_iz, types_fields_capa_der_iz)
    else:
        capa_izquierda = obtener_capa_por_nombre(nombre_capa_izquierda)
        capa_izquierda.dataProvider().truncate()

    #Capas para mostrar los metadatos del API de Google
    nombre_capa_metadatos = "metadatos_layer"
    if not existe_capa(nombre_capa_metadatos):
        capa_metadatos = crear_vector_layer(nombre_capa_metadatos, [], [])
    else:
        capa_metadatos = obtener_capa_por_nombre(nombre_capa_metadatos)
        capa_metadatos.dataProvider().truncate()

    nombre_capa_metadatos_proy = "metadatos_proy_layer"
    if not existe_capa(nombre_capa_metadatos_proy):
        capa_metadatos2 = crear_vector_layer(nombre_capa_metadatos_proy, [], [])
    else:
        capa_metadatos2 = obtener_capa_por_nombre(nombre_capa_metadatos_proy)
        capa_metadatos2.dataProvider().truncate()
    return capa_centro, capa_derecha, capa_izquierda,capa_metadatos,capa_metadatos2

#Asignar poligonos a grids
def asignar_poligono_celdas(idpoligono,poligono, grid_array,  num_filas, num_cols, min, min_lat_lon, max_lat_lon):
    bbox = poligono.boundingBox()
    min_bbox_x = bbox.xMinimum()
    min_bbox_y = bbox.yMinimum()
    max_bbox_x = bbox.xMaximum()
    max_bbox_y = bbox.yMaximum()    
    #VERIFICAR Y CORREGIR POLIGONOS FUERA DEL GRID
    #EN CASO QUE ESTE FUERA DE LOS GRIDS
    if(max_bbox_x < min_lat_lon.x() or max_bbox_y < min_lat_lon.y()):  
      return
    if(min_bbox_x > max_lat_lon.x() or min_bbox_y >  max_lat_lon.y()):  
      return 
    #LIMITE INFERIOR 
    if(min_bbox_y < min_lat_lon.y()):
        min_bbox_y = min_lat_lon.y()
    if(min_bbox_x < min_lat_lon.x()):
        min_bbox_x = min_lat_lon.x()
    #LIMITE SUPERIOR
    if(max_bbox_y > max_lat_lon.y()):
        max_bbox_y = max_lat_lon.y()
    if(max_bbox_x > max_lat_lon.x()):
        max_bbox_x = max_lat_lon.x()
        
    min_pol_box = QgsPointXY(min_bbox_x,min_bbox_y)
    max_pol_box = QgsPointXY(max_bbox_x,max_bbox_y)    
    
    #convertir a otro sistema de coordenadas
    puntos_box = [(min_pol_box.x(), min_pol_box.y()), (max_pol_box.x(), min_pol_box.y()), (max_pol_box.x(), max_pol_box.y()), (min_pol_box.x(), max_pol_box.y())]   
    polygon = QgsGeometry.fromPolygonXY( [[ QgsPointXY( pair[0], pair[1] ) for pair in puntos_box ]] ) 
    #agregar_poligono_capa_grids(capa_pol_grid,polygon,2,2)
    min_pol_box = convertir_punto_de_4326_a_24879(min_pol_box)
    max_pol_box = convertir_punto_de_4326_a_24879(max_pol_box)
    #Caclular GRID al que pertenece el poligono
    # PUNTO INFERIOS-IZQUIERDO
    dist_x = calcular_distancia_puntos(QgsPointXY(min.x(),min_pol_box.y()),QgsPointXY(min_pol_box.x(),min_pol_box.y()))
    dist_y = calcular_distancia_puntos(QgsPointXY(min_pol_box.x(),min.y()),QgsPointXY(min_pol_box.x(),min_pol_box.y()))
    indice_y = int(dist_y / tam_celda)
    indice_x = int(dist_x / tam_celda)
    #PUNTO SUPERIOR DERECHO
    dist_x4 = calcular_distancia_puntos(QgsPointXY(min.x(),max_pol_box.y()),QgsPointXY(max_pol_box.x(),max_pol_box.y()))
    dist_y4 = calcular_distancia_puntos(QgsPointXY(max_pol_box.x(),min.y()),QgsPointXY(max_pol_box.x(),max_pol_box.y()))
    indice_y4 = int(dist_y4 / tam_celda) 
    indice_x4 = int(dist_x4 / tam_celda)
    
    index_grid_x = indice_x
    index_grid_y = indice_y
   
    num_grids_x = indice_x4 - indice_x + 1
    num_grids_y = indice_y4 - indice_y + 1
    
    for grids_y in range(num_grids_y):
        index_grid_x = indice_x
        for grids_x in range(num_grids_x):            
            if(index_grid_x >= 0 and index_grid_y >= 0 and index_grid_x < num_cols and index_grid_y < num_filas ):
                grid_array[index_grid_y][index_grid_x].add(idpoligono)
            index_grid_x = index_grid_x + 1
        index_grid_y = index_grid_y + 1 


# Generar grid
def generar_grid(layer_poligonos, min_lat_lon, max_lat_lon, dibujar_grid = False):
    
    if(dibujar_grid):
        nombre_capa_grid = "grid"
        if not existe_capa(nombre_capa_grid):
            capa_pol_grid = crear_vector_layer(nombre_capa_grid,[], [], tipo='Polygon')
        else:
            capa_pol_grid = obtener_capa_por_nombre(nombre_capa_grid)
            capa_pol_grid.dataProvider().truncate()    
    
    min = convertir_punto_de_4326_a_24879(min_lat_lon)
    max = convertir_punto_de_4326_a_24879(max_lat_lon)
    #Calcular distancias entre los limites del mapa
    dist_total_y = calcular_distancia_puntos(QgsPointXY(0,min.y()),QgsPointXY(0,max.y()))
    dist_total_x = calcular_distancia_puntos(QgsPointXY(min.x(),0),QgsPointXY(max.x(),0))
    #calular el numero de filas y columnas del grid
    num_div_x = int(dist_total_x / tam_celda) + 1
    num_div_y = int(dist_total_y / tam_celda) + 1
    #Crear matriz del grid
    grid_array = crear_grid(num_div_y, num_div_x)       
    #DIBUJAR GRID    
    nuevo_y = min.y()
    nuevo_x = min.x()
    print("grid x = ",num_div_x)
    print("grid y=", num_div_y)
    
    if(dibujar_grid):
        for i in range(num_div_y):    
            nuevo_x = min.x()
            for j in range(num_div_x):     
                # obtener puntos para formar la geometria del grid
                if(i != num_div_y):            
                    x_min_grid = nuevo_x
                    y_min_grid = nuevo_y
                    x_max_grid = nuevo_x + tam_celda
                    y_max_grid = nuevo_y + tam_celda
                    min_grid = convertir_punto_de_24879_a_4326(QgsPointXY(x_min_grid,y_min_grid))
                    max_grid = convertir_punto_de_24879_a_4326(QgsPointXY(x_max_grid,y_max_grid))
                    puntos_grid = [(min_grid.x(), min_grid.y()), (max_grid.x(), min_grid.y()), (max_grid.x(), max_grid.y()), (min_grid.x(), max_grid.y())]   
                    polygon = QgsGeometry.fromPolygonXY( [[ QgsPointXY( pair[0], pair[1] ) for pair in puntos_grid ]] ) 
                    agregar_feature_capa(capa_pol_grid,polygon,[])
                nuevo_x = x_max_grid     
            nuevo_y = nuevo_y + tam_celda    
    #Asignar poligonos a grids
    features_pol = list(layer_poligonos.getFeatures())
    cont = 0
    for pol in features_pol:
        multi = pol.geometry()
        asignar_poligono_celdas(cont,multi, grid_array, num_div_y, num_div_x, min, min_lat_lon,max_lat_lon )
                   
        cont = cont +1
    return grid_array

def descargar_metadata_imagen(lat, lon, fov=90, pitch=0, use_heading=False,heading_value=20):
    if(use_heading):
        metadata_url = "{}?size=640x640&location={},{}&fov={}&pitch={}&key={}&heading={}".format(URL_BASE_METADATA,str(lat), str(lon), str(fov), str(pitch), API_KEY, heading_value)
    else:
        metadata_url = "{}?size=640x640&location={},{}&fov={}&pitch={}&key={}".format(URL_BASE_METADATA, str(lat), str(lon), str(fov), str(pitch), API_KEY)
        
    try:
        response = urllib.request.urlopen(metadata_url)
        metadata_imagen = json.load(response)
    except:
        print("metadata corrompida {}".format(metadata_url))
        metadata_imagen = {'status':'Corrupted'}
    return metadata_imagen
    
def descargar_imagen(osm_id, file_name,panoids,metadata,csvfilename,img_filename, lat, lon,lat_fachada, lon_fachada,v_unit,dist_a_fachada, fov=90, pitch=0, use_heading=False,heading_value=0):
    if(use_heading):
        image_url = image_url = "{}?size=640x640&location={},{}&fov={}&pitch={}&key={}&heading={}".format(URL_BASE_IMAGE,str(lat), str(lon), str(fov), str(pitch), API_KEY, heading_value)
    else:
        image_url = "{}?size=640x640&location={},{}&fov={}&pitch={}&key={}".format(URL_BASE_IMAGE, str(lat), str(lon), str(fov), str(pitch), API_KEY)
    #print(image_url)
    try:        
        #if metadata['pano_id'] not in panoids:
        #print('DESCARGANDO IMAGEN')
        urllib.request.urlretrieve(image_url, img_filename)
        img_pil = Image.open(img_filename)            
        #panoids.append(metadata['pano_id'])
        print('Downloaded: ',img_filename)
        datos = [file_name,lat_fachada,lon_fachada, metadata['date'],osm_id,v_unit.x(),v_unit.y(),dist_a_fachada,fov,heading_value,image_url ]
        if(generar_csv):
            with open(csvfilename,'a',newline='') as csvfile:
                writer = csv.writer(csvfile,delimiter=';')
                writer.writerow(datos)
        #else:
        #    print('YA SE DESCARGO ANTERIORMENTE')    
    except:
        print("Imagen corrupta {}".format(image_url))
 
def descargar_imagen_webdriver(osm_id, file_name,panoids,metadata,csvfilename,img_filename, lat, lon,lat_fachada, lon_fachada,v_unit,dist_a_fachada, fov=90, pitch=0, use_heading=False,heading_value=0):
    image_url = "{}viewpoint={},{}&heading={}&pitch={}&fov={}".format(URL_BASE_IMAGEN_GSV,str(lat), str(lon),heading_value,str(pitch), str(fov) )
    print(image_url)
    try:        
        if metadata['pano_id'] not in panoids:
            #Descragar imagen GSV
            driver.get(image_url)
            driver.execute_script(estilos_css_js)
            time.sleep(6)
            driver.save_screenshot(img_filename)
                  
            panoids.add(metadata['pano_id'])
            print('Downloaded: ',img_filename)
            datos = [file_name,lat_fachada,lon_fachada, metadata['date'],osm_id,v_unit.x(),v_unit.y(),dist_a_fachada,fov,heading_value,image_url ]
            if(generar_csv):
                with open(csvfilename,'a',newline='') as csvfile:
                    writer = csv.writer(csvfile,delimiter=';')
                    writer.writerow(datos)
            
    except:
        print("Imagen corrupta {}".format(image_url))
    
def verificar_punto_referencia_metadato(metadata,punto_i, punto_f, punto_central_lat_lon,vector, pano_ids_puntos, capa_metadatos, capa_proy, dist_a_fachada, prefijo):
    #Convertir punto central sistema de coordendas proyectado
    punto_central = convertir_punto_de_4326_a_24879(punto_central_lat_lon)
    #calcular vector ortogonal al vector con direccion a  la calle
    v_ortogonal = QgsPoint(vector.y(), -1*vector.x())
    if (metadata['status'] == 'OK' and metadata['copyright'].find('Google')>=0):
        pano_id = metadata['pano_id']
        date = metadata['date']
        lat_img  = metadata['location']['lat']
        lon_img = metadata['location']['lng']
        
        # Verificar si ya se descargo la imagen
        if pano_id not in pano_ids_puntos:
            agregar_feature_capa(capa_metadatos,QgsGeometry.fromPointXY(QgsPointXY(lon_img,lat_img)),[]) 
            punto_metadato = convertir_punto_de_4326_a_24879(QgsPointXY(lon_img,lat_img))

            e1 = QgsPointXY(punto_f.x() - punto_i.x(),punto_f.y() - punto_i.y())
            e2 = QgsPointXY(punto_metadato.x() - punto_i.x(),punto_metadato.y() - punto_i.y())
            dp = e1.x()*e2.x() + e1.y()*e2.y()
            len2_e1 = e1.x()*e1.x() + e1.y()*e1.y()
            new_c_x = punto_i.x() + e1.x()*(dp/len2_e1)
            new_c_y = punto_i.y() + e1.y()*(dp/len2_e1)



            #====================================================================================
            #calcular posicion con relacion al segmento de linea de la calle
            #posicion = (punto_f.x() - punto_i.x())*(punto_metadato.y() - punto_i.y()) - (punto_f.y() - punto_i.y())*(punto_metadato.x() - punto_i.x())
            #a = v_ortogonal.x()
            #b = v_ortogonal.y()
            #new_c_x = 0
            #new_c_y = 0
            #if posicion < 0: # izquierda de la linea                
            #    d = abs(-1*a*(punto_metadato.x() - punto_central.x()) + -1*b*(punto_metadato.y() - punto_central.y())) /  math.sqrt(a*a + b*b)
            #    new_c_x = punto_metadato.x() - d*a
            #    new_c_y = punto_metadato.y() - d*b
            #else:
            #    if posicion > 0: #derecha de la linea
            #        d = abs(a*(punto_metadato.x() - punto_central.x()) + b*(punto_metadato.y() - punto_central.y())) /  math.sqrt(a*a + b*b)
            #        new_c_x = punto_metadato.x() + d*a
            #        new_c_y = punto_metadato.y() + d*b                    
            #    else: # sobre la linea
            #        new_c_x = punto_metadato.x()
            #        new_c_y = punto_metadato.y()     
            #============================================================================================

                   
            #verificar si esta en el segmento de linea
            a = v_ortogonal.x()
            b = v_ortogonal.y()
            v1x = punto_f.x() - punto_i.x()
            v1y = punto_f.y() - punto_i.y()
            v2x = new_c_x - punto_i.x()
            v2y = new_c_y - punto_i.y()
            k1 = v1x*v2x + v1y*v2y
            k2 = v1x*v1x + v1y*v1y
            if k1<0 or k1>k2:
                #print('NO ESTA DENTRO DEL SEGMENTO')
                return False
            else:
                #print('ESAT DENTRO DEL SEGMENTO')
                pano_ids_puntos.append(pano_id)
                # Ajustar punto proyectado a la fachada
                orientacion = 1
                if prefijo == 'iz':
                    orientacion = -1                               
                new_ref_x =  new_c_x + orientacion*dist_a_fachada*a
                new_ref_y =  new_c_y + orientacion*dist_a_fachada*b    
                punto_proyectado_lat_lon = convertir_punto_de_24879_a_4326(QgsPointXY(new_ref_x, new_ref_y))       
                agregar_feature_capa(capa_proy,QgsGeometry.fromPointXY(punto_proyectado_lat_lon) ,[]) 

                return punto_proyectado_lat_lon 
        else:
            #print('YA SE DESACRAGO LA IMAGEN')
            return False

    else:
        return False

def descargar_imagenes_capa(capa_centro,capa_puntos, prefijo,capa_metadatos, capa_proyectados, opcion="api-google", guardar_puntos_proy = True):
    if not os.path.exists(nombre_carpeta_salida):
        os.makedirs(nombre_carpeta_salida)
    csvfilename = "{}/metadata.csv".format(nombre_carpeta_salida)
    #panoids = set()
    #panoids.clear()
    panoids = []
    #Generar archivo CSV de resultados
    if(generar_csv):
        if not os.path.exists(csvfilename):
            with open(csvfilename,'w',newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(['image_name', 'latitude', 'longitude','date','osm_id','vector_unit_x','vector_unit_y','dist_a_fachada','fov','heading','url'])
    
    features = list(capa_puntos.getFeatures())
    features_centro = list(capa_centro.getFeatures())
    for i in range(len(features)):
        #Coordenadas geograficas de las fachadas
        lat_fachada = features[i].attribute("y")
        lon_fachada = features[i].attribute("x")
        #vector unitario en direccion de la calle
        v_unit = QgsPointXY(features[i].attribute("vector_unit_x"),features[i].attribute("vector_unit_y"))
        #Coordendas geograficas del punto central de la calle
        lat = features_centro[i].attribute("y")
        lon = features_centro[i].attribute("x")
        punto_central_lat_lon = QgsPointXY(lon,lat)
        #recuperar fov
        fov_value = features[i].attribute("fov")
        #recuperar osm id
        osm_id = features[i].attribute("osm_id_calle")
        #recuperar puntos inicial y final del segmento de linea en donde se encuentra el punto central de la calle
        punto_i = QgsPointXY(features[i].attribute("seg_i_x"),features[i].attribute("seg_i_y"))
        punto_f = QgsPointXY(features[i].attribute("seg_f_x"),features[i].attribute("seg_f_y"))
        #distancia a fachada
        distancia_a_fachada = features[i].attribute("dist_a_fachada")
        #descargar metadata
        metadata = descargar_metadata_imagen(lat, lon, use_heading=usar_heading)
        #Calcular punto proyectado (mas cercano al real)
        punto_proyectado = verificar_punto_referencia_metadato(metadata,punto_i, punto_f, punto_central_lat_lon,v_unit, panoids, capa_metadatos, capa_proyectados, distancia_a_fachada, prefijo)
        #print('EXISTE PROYECTADO', punto_proyectado)
        if(punto_proyectado):
            pano_id = metadata['pano_id']
            date = metadata['date']
            lat_img  = metadata['location']['lat']
            lon_img = metadata['location']['lng']
            date_image = metadata['date']
            imagen_filename = "{}/{}-{}-{}.jpg".format(nombre_carpeta_salida,prefijo,i,osm_id)
            filename = "{}-{}-{}".format(prefijo,i,osm_id)
            #Agregar feature a capa metadatos           
            descargar_imagen(osm_id,filename,panoids, metadata,csvfilename,imagen_filename, lat_img,lon_img,punto_proyectado.y(),punto_proyectado.x(), v_unit,features[i].attribute("dist_a_fachada"),fov = fov_value ,use_heading=usar_heading, heading_value=features[i].attribute("heading"))  
       
    print("TERMINO")

#funcion para calcular limites de una capa       
def calcular_limites_capa(layer):    
    xmin_layer = (layer.extent().xMinimum()) 
    xmax_layer =  (layer.extent().xMaximum()) 
    ymin_layer = (layer.extent().yMinimum()) 
    ymax_layer = (layer.extent().yMaximum())
    min_layer = QgsPointXY(xmin_layer,ymin_layer)
    max_layer = QgsPointXY(xmax_layer,ymax_layer)
    return min_layer, max_layer

#Funcion ara mostrar detecciones de negocios
def mostrar_resultados(nombre_capa, ruta_csv_detecciones):
    
    #Crear capas vectoriales
    if not existe_capa(nombre_capa):
        capa_deteccines = crear_vector_layer(nombre_capa, ['nombre_imagen','lat','lon','img_name'], ['String','Double','Double','String'])
    else:
        capa_deteccines = obtener_capa_por_nombre(nombre_capa)
        capa_deteccines.dataProvider().truncate()
    with open(ruta_csv_detecciones) as csv_file:
        cont = 0
        csv_reader = csv.reader(csv_file, delimiter=';')
        for line in csv_reader:
            if(not cont == 0):
                agregar_feature_capa(capa_deteccines, QgsGeometry.fromPointXY(QgsPointXY(float(line[3]),float(line[2]))), [line[0],float(line[2]),float(line[3]),line[1]])
            cont = cont + 1

def mostrar_resultados_json(nombre_capa, path_json_file):
    #Crear capas vectoriales
    if not existe_capa(nombre_capa):
        capa_detecines = crear_vector_layer(nombre_capa, ['id_obj','lat','lon','crops_img','class', 'prob'], ['String','Double','Double','String','String','String'])
    else:
        capa_detecines = obtener_capa_por_nombre(nombre_capa)
        capa_detecines.dataProvider().truncate()
    #Leer json resultados
    data = {}
    with open(path_json_file) as f:
        data = json.load(f)
    #print(type(data))
    for obj in data["objetos"]:
        id_obj = obj["id_obj"]
        lat_obj = obj["location"][1]
        lon_obj = obj["location"][0]
        prob = obj["clase"]["prob"][0]
        idx_class = obj["clase"]["class_idx"][0]
        crops = ",".join(obj["crops"])
        agregar_feature_capa(capa_detecines, QgsGeometry.fromPointXY(QgsPointXY(lat_obj,lon_obj)), [id_obj,lat_obj,lon_obj,crops,idx_class,prob])    
    return data

def obtener_puntos_cercanos(punto_central, lista_puntos ,radio = 5):
    indices_cercanos = []
    distancias_cercanos = []
    for i in range(len(lista_puntos)):
        obj_gt = lista_puntos[i]
        punto_gt_lat_lon = QgsPointXY(obj_gt["location"][1], obj_gt["location"][0])
        punto_gt = convertir_punto_de_4326_a_24879(punto_gt_lat_lon)
        distancia = calcular_distancia_puntos(punto_central, punto_gt)
        if distancia <= radio:
            indices_cercanos.append(i)
            distancias_cercanos.append(distancia)
    return indices_cercanos,distancias_cercanos

def dibujar_relacion(capa,punto_init, punto_final):
    lines = QgsGeometry.fromPolyline( [punto_init,punto_final]) 
    agregar_feature_capa(capa,lines,[])

def calcular_metricas( list_gt,list_pred, top_k = 3, dibujar_relaciones = False):
    TP = 0
    TN = 0
    FP = 0
    FN = 0
    
    #img_sin_obj_gt = list_gt["imgs_sin_objetos"] 
    #img_sin_obj_pred = list_pred["imgs_sin_objetos"]
    #val_tn = img_sin_obj_gt
    #if  img_sin_obj_gt> img_sin_obj_pred:
    #    val_tn = img_sin_obj_pred
    #    FP = img_sin_obj_gt - img_sin_obj_pred
    #else:
    #    FN = img_sin_obj_pred - img_sin_obj_gt
    #TN = val_tn
    tmp_list_pred = list_pred["objetos"].copy()
    tmp_list_gt = list_gt["objetos"].copy()
    TN = list_pred["TN"]
    if(dibujar_relaciones):
        print("DIBUJANDO relaciones")
        nombre_capa_r = "relaciones"
        if not existe_capa(nombre_capa_r):
            capa_r = crear_vector_layer(nombre_capa_r,[], [], tipo='LineString')
        else:
            capa_r = obtener_capa_por_nombre(nombre_capa_r)
            capa_r.dataProvider().truncate()    
    for index in range(len(list_pred["objetos"])):
        obj = list_pred["objetos"][index]
        #SI la la mejor prediccion pertenece a la clases SIN NEGOCIO BORRAR EL OBJETO
        if obj["clase"]["class_idx"][0] == 4 and obj["clase"]["prob"][0]>=0.8:
            tmp_list_pred.remove(obj)
        else:
            punto_central_lat_lon = QgsPoint(obj["location"][1], obj["location"][0])
            punto_central = convertir_punto_de_4326_a_24879(punto_central_lat_lon)        
            index_puntos_cercanos, distancias_puntos_cercanos = obtener_puntos_cercanos(punto_central,tmp_list_gt)
            distancia_menor = 9999
            indice_mas_cercano = -1
            existe_compatibles = False
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
                obj_gt = tmp_list_gt[indice_mas_cercano]
                punto_gt_lat_lon = QgsPoint(obj_gt["location"][1], obj_gt["location"][0])
                TP = TP + 1
                tmp_list_gt.pop(indice_mas_cercano)
                tmp_list_pred.remove(obj)
                if dibujar_relaciones:
                    dibujar_relacion(capa_r,punto_central_lat_lon,punto_gt_lat_lon)        
    FP = FP + len(tmp_list_pred)
    FN = FN + len(tmp_list_gt)
    print("METRICAS CLASIFICACION")
    print("TP = ", TP)
    print("TN = ", TN)
    print("FP = ", FP)
    print("FN = ", FN)
    precision = TP/(TP+FP)
    recall = TP/(TP+FN)
    accuracy = (TP + TN)/(TP+FP+TN+FN)
    F1 = 2*(recall*precision)/(recall + precision)
    print("PRECISION = ", precision)
    print("RECALL = ", recall)
    print("ACCURACY = ", accuracy)
    print("F1 = ", F1)

def calcular_metricas_deteccion( list_gt,list_pred, top_k = 3, dibujar_relaciones = False):
    TP = 0
    TN = 0
    FP = 0
    FN = 0
    #img_sin_obj_gt = list_gt["imgs_sin_objetos"] 
    #img_sin_obj_pred = list_pred["imgs_sin_objetos"]
    #val_tn = img_sin_obj_gt
    #if  img_sin_obj_gt> img_sin_obj_pred:
    #    val_tn = img_sin_obj_pred
    #    FP = img_sin_obj_gt - img_sin_obj_pred
    #else:
    #    FN = img_sin_obj_pred - img_sin_obj_gt
    #TN = val_tn
    tmp_list_pred = list_pred["objetos"].copy()
    tmp_list_gt = list_gt["objetos"].copy()
    TN = list_pred["TN"]
    if(dibujar_relaciones):
        print("DIBUJANDO relaciones")
        nombre_capa_r = "relaciones"
        if not existe_capa(nombre_capa_r):
            capa_r = crear_vector_layer(nombre_capa_r,[], [], tipo='LineString')
        else:
            capa_r = obtener_capa_por_nombre(nombre_capa_r)
            capa_r.dataProvider().truncate()    
    for index in range(len(list_pred["objetos"])):
        obj = list_pred["objetos"][index]
        #SI la la mejor prediccion pertenece a la clases SIN NEGOCIO BORRAR EL OBJETO
        #if obj["clase"]["class_idx"][0] == 4 and obj["clase"]["prob"][0]>=0.8:
        #    tmp_list_pred.remove(obj)
        #else:
        punto_central_lat_lon = QgsPoint(obj["location"][1], obj["location"][0])
        punto_central = convertir_punto_de_4326_a_24879(punto_central_lat_lon)        
        index_puntos_cercanos, distancias_puntos_cercanos = obtener_puntos_cercanos(punto_central,tmp_list_gt)
        distancia_menor = 9999
        indice_mas_cercano = -1
        existe_compatibles = False
        for i,indice_cercano in enumerate(index_puntos_cercanos):
            obj_gt = tmp_list_gt[indice_cercano]
            clase_gt = int(obj_gt["clase"]["class_idx"][0])
            clases_pred = obj["clase"]["class_idx"][:top_k]
            #if clase_gt in clases_pred:
            if distancias_puntos_cercanos[i] < distancia_menor:
                existe_compatibles = True
                indice_mas_cercano = indice_cercano
                distancia_menor = distancias_puntos_cercanos[i]
        if existe_compatibles:
            obj_gt = tmp_list_gt[indice_mas_cercano]
            punto_gt_lat_lon = QgsPoint(obj_gt["location"][1], obj_gt["location"][0])
            TP = TP + 1
            tmp_list_gt.pop(indice_mas_cercano)
            tmp_list_pred.remove(obj)
            if dibujar_relaciones:
                dibujar_relacion(capa_r,punto_central_lat_lon,punto_gt_lat_lon)        
    FP = FP + len(tmp_list_pred)
    FN = FN + len(tmp_list_gt)
    print("METRICAS DETECCION")
    print("TP = ", TP)
    print("TN = ", TN)
    print("FP = ", FP)
    print("FN = ", FN)
    precision = TP/(TP+FP)
    recall = TP/(TP+FN)
    accuracy = (TP + TN)/(TP+FP+TN+FN)
    F1 = 2*(recall*precision)/(recall + precision)
    print("PRECISION = ", precision)
    print("RECALL = ", recall)
    print("ACCURACY = ", accuracy)
    print("F1 = ", F1)

if __name__ == '__console__':
    #Crear capas
    start_time = time.time()
    capa_centro,capa_derecha, capa_izquierda, capa_metadatos, capa_metadatos_proy = inicializar_capas()
    #obtener capas de osm
    layer_lines = obtener_capa_por_nombre(nombre_capa_lines)
    layer_poligonos= obtener_capa_por_nombre(nombre_capa_polygons)
    #calcular limites de la capa polygons
    min_layer, max_layer = calcular_limites_capa(layer_poligonos)
    #filtrar calles
    calles = obtener_calles_id_nombre(layer_lines,osm_id_ruta)
    #calles = list(layer_lines.getFeatures())
    #print(calles)
    #generar grid
    grid = generar_grid(layer_poligonos, min_layer,max_layer, dibujar_grid=False)
    calcular_puntos_calle(layer_poligonos, calles,capa_centro,capa_derecha,capa_izquierda,grid,min_layer)
    
    descargar_imagenes_capa(capa_centro,capa_derecha,'der',capa_metadatos, capa_metadatos_proy)
    descargar_imagenes_capa(capa_centro,capa_izquierda,'iz',capa_metadatos, capa_metadatos_proy)
    end_time = time.time()
    print(f"Runtime of the program is {end_time - start_time}")
    
    #driver.quit() 

    # Testing 
    #list_pred = mostrar_resultados_json("pred-zarzuela","C:/Users/Cesar/Documents/data_test_gsv/resultados-new/zarzuela/pred-zarzuela.json")
    #list_gt = mostrar_resultados_json("gt-zarzuela","C:/Users/Cesar/Documents/data_test_gsv/resultados-new/zarzuela/gt-zarzuela.json")
    #calcular_metricas(list_gt,list_pred,top_k = 5, dibujar_relaciones=True)
    #calcular_metricas_deteccion(list_gt,list_pred,top_k = 1, dibujar_relaciones=False)