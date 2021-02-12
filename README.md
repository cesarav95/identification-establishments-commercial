# Identificación de establecimientos comerciales no registrados en mapas digitales

You can see the english version [here](https://google.com.pe).

El proyecto consiste en detectar establecimientos comerciales analizando imágenes de **Google Street View**, para ello se analiza datos de **OpenStreetMap** para obtener los parámetros correctos para la descarga de imágenes apartir del API de **Google Street View**, las cuales estan orientadas a las fachadas de los edificios.  

Este proyecto hace use de YOLOv4 para la detección de establecimientos comerciales, el cual se encuentra implementado en “[Darknet](https://github.com/AlexeyAB/darknet)” , donde los objetos detectados son datos de entrada a una red de clasificacoón VGG16 y a la vez a un detector de textos en imagenes naturales (textos verticales y horizontales).

A continuación, se describe el código implementado:
1. [Geo-procesamiento en QGIS](#geo-processing-in-qgis).
2. [Detección](#detecction-using-yolov4).
3. [Clasificación ](#clasification).
4. [Testing](#Testing)

## Geo-processing en QGIS
Se utilizo el sistema de información geográfico **QGIS** para el procesamiento de datos de OpenStreetMap y la descarga de imágenes de GSV. El código se encuentra en el archivo "[download_images_gsv.py](https://github.com/cesarav95/identification-of-establishments-commercial/blob/main/qgis/download_images_gsv.py)"; este archivo debe ser ejecutado en QGIS de la siguiente manera:

* Para descargar imágenes primeramente se necesita los datos de OSM los cuales pueden ser descargados desde su página principal ("[OpenStreetMap"](http://openstreetmap.org)"). Al descargar el archivo **".osm"** se hace la importación de las capas de "lines" y "multipolygos" en QGIS. Estas dos capas contienen información de calles y edificios del mapa de OSM. Un ejemplo de este archivo de encuentra en la carpeta "[qgis/input.osm](https://github.com/cesarav95/identification-of-establishments-commercial/blob/main/qgis/input.osm)" 
* En el archivo [download_images_gsv.py](https://github.com/cesarav95/identification-of-establishments-commercial/blob/main/qgis/download_images_gsv.py)" se asigna como entrada a las variables `nombre_capa_lines` y `nombre_capa_polygons` con los nombres de las capas "lines" y "multipoligons" respectivamente que adquieren al importar el archivo osm; luego se elige el **osm_id** de calle que se desea descargar las imágenes (otra opcion es definiar una ruta personalizada en una nueva capa vectorial) indicado en el parámetro `osm_id_ruta`. 
* Al correr el código en QGIS (desde el editor de código de QGIS) se genera una carpeta por defecto de salida llamada `output` definido en parámetro `nombre_carpeta_salida`. En este carpeta se guardan las imágenes descargas y un archivo **CSV** con los metadatos de cada imagen como: su ubicación geográfica, parámetros fov , heading, vector unitario del segmento de línea de la calle y la url del API generado para la descarga.

## Detección


Para poder ver nuestro codigo, abrir el cuaderno en colab.
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1JaeBU1IwkXKgi0cJCzJcy4El6NQwqZbV?usp=sharing)
