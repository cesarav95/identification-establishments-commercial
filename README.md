# Identificación de establecimientos comerciales no registrados en mapas digitales

You can see the english version [here](https://google.com.pe).

El proyecto consiste en detectar establecimientos comerciales analizando imágenes de Google Street View, para ello se analiza datos de Open Street Map para obtener los parámetros correctos para la descarga de imágenes de GSV estén orientadas a las fachadas de los edificios como también se hace uso de métodos de deep learning.  

Este proyecto hace use de YOLOv4 para la detección de establecimientos comerciales, el cual se encuentra implementado en “[Darknet](https://github.com/AlexeyAB/darknet)” y VGG16 para la clasificación. 

....... more información


A continuación, se describe el uso del código implementado:
1. [Geo-procesamiento en QGIS](#geo-processing-in-qgis).
2. [Detección](#detecction-using-yolov4).
3. [Clasificación ](#clasification).
4. [Testing](#Testing)

## Geo-processing in QGIS
Se utilizo el sistema de información geográfico QGIS para el procesamiento de datos de OpenStreetMap y la descarga de imágenes de GSV. El código se encuentra en el archivo "[download_images_gsv.py](https://google.com.pe)", este archivo debe ser ejecutado el QGIS de la siguiente manera:

* Para descargar imágenes primeramente se necesita los datos de OSM los cuales pueden ser descargados desde su página principal ("[OpenStreetMap"]()"). Al descargar el archivo ".osm" se importa a QGIS la capas de "lines" y "multipolygos". Estas dos capas contienen información de calles y edificios del mapa de OSM. Un ejemplo de este archivo de encuentra en la carpeta "[qgis/osm_file/example.osm]()" 
* En [download_images_gsv.py](https://google.com.pe)" se configura como entrada las capas "lines" "multipoligons" en los parametros `nombre_capa_lines` y `nombre_capa_polygons` respectivamente, luego se elige el osm_id de calle que se desea descargar las imágenes (otra opcion es definiar una ruta personalizado en una nueva capa vectorial) indicado en el parámetro `osm_id_calle`. 
* Al correr el código en QGIS (desde e editor de código de QGIS) se genera una carpeta de salida llamada por defecto `output` definido en parámetro `nombre_carpeta_salida`. En este carpeta se guardan las imágenes descargas y un archivo CSV con los metadatos de cada imagen como su ubicación geográfica, parámetros fov , heading, vetor unitario del segmento de línea de la calle y la url del api generado para la descarga.
