# Identificación de establecimientos comerciales no registados en mapas digitales

You can see the english version [here](https://google.com.pe).

El proyecto consiste en detectar establecimientos comerciales analizando imagenes de Google Street View, para ello se analiza datos de Open Street Map para obtener los parametros correctos para la descarga de imagenes de GSV esten orientadas a las fachadas de los edificios como tambien se hace uso de metodos de deep learning.  

Este projecto hace use de YOLOv4 para la deteccion de establecimientos comerciales, el cual se encuentra implementado en  "[Darknet](https://github.com/AlexeyAB/darknet)"  y VGG16 para la clasificación. 

....... more information


A contunuacion se describe el el uso del codigo implementado:
1. [Geo-procesamiento en QGIS](#geo-processing-in-qgis).
2. [Deteccion](#detecction-using-yolov4).
3. [Clasificacion ](#clasification).
4. [Testing](#Testing)

## Geo-processing in QGIS
Se utilizo el sistema de informacion geografico QGIS para el procesamiento de datos de OpenStreetMap y la descarga de imagenes de GSV. El codigo se encuentra en el archivo "[download_images_gsv.py](https://google.com.pe)", este archivo debe ser ejecutado el QGIS de la siguiente manera:

* Para decargar imagenes primeramente se necesita los datos de OSM los cuales pueden ser descargados desde su pagina principal ("[OpenStreetMap"]()"). Al descargar el archivo ".osm" se importa a QGIS la capas de "lines" y "multipolygos". Estas dos capas contiene informacion de calles y edificos del mapa de OSM. Un ejemplo de ste archivo de encuentra en la carpeta "[qgis/osm_file/example.osm]()" 
* En [download_images_gsv.py](https://google.com.pe)" se configura como entrada  las capas "lines" "multipoligons" en los parametros `nombre_capa_lines` y `nombre_capa_polygons` respectivamente, luego se elige el osm_id de calle que se desea descargar las imagenes (otra opcion es definiar una ruta personalizado en una nueva capa vectorial) indicado en el paramtro `osm_id_calle`. 
* Al correr el codigo en QGIS (desde e editor de codigo de QGIS) se genera un carpeta de salida llamada por defecto `output` definido en parametro `nombre_carpeta_salida`. En este carpta se guardan las imagenes descargas y un archivo CSV con los metadados de cada imagen como su ubicacion geografoca, parametos fov y heading, vetor unitario del segmento de linea de la calle y la url del api generado para la descarga.



