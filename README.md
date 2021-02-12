# Identificación de establecimientos comerciales no registrados en mapas digitales

You can see the english version [here](https://google.com.pe).

El proyecto consiste en detectar establecimientos comerciales analizando imágenes de **Google Street View**, para ello se analiza datos de **OpenStreetMap** para obtener los parámetros correctos para la descarga de imágenes apartir del API de **Google Street View**, las cuales estan orientadas a las fachadas de los edificios.  

Este proyecto hace use de YOLOv4 para la detección de establecimientos comerciales, el cual se encuentra implementado en “[Darknet](https://github.com/AlexeyAB/darknet)” , donde los objetos detectados son datos de entrada a una red de clasificacoón VGG16 y a la vez a un detector de textos en imagenes naturales (textos verticales y horizontales).

A continuación, se describe el código implementado:
1. [Geo-procesamiento en QGIS](#geo-processing-en-qgis).
2. [Detección](#Detección).
3. [Clasificación ](#Clasificación).
4. [Testing](#Testing).

## Geo-processing en QGIS
Se utilizo el sistema de información geográfico **QGIS** para el procesamiento de datos de OpenStreetMap y la descarga de imágenes de GSV. El código se encuentra en el archivo "[download_images_gsv.py](https://github.com/cesarav95/identification-of-establishments-commercial/blob/main/qgis/download_images_gsv.py)"; este archivo debe ser ejecutado en QGIS de la siguiente manera:

* Para descargar imágenes primeramente se necesita los datos de OSM los cuales pueden ser descargados desde su página principal ("[OpenStreetMap"](http://openstreetmap.org)"). Al descargar el archivo **".osm"** se hace la importación de las capas de "lines" y "multipolygos" en QGIS. Estas dos capas contienen información de calles y edificios del mapa de OSM. Un ejemplo de este archivo de encuentra en la carpeta "[qgis/input.osm](https://github.com/cesarav95/identification-of-establishments-commercial/blob/main/qgis/input.osm)" 
* En el archivo [download_images_gsv.py](https://github.com/cesarav95/identification-of-establishments-commercial/blob/main/qgis/download_images_gsv.py)" se asigna como entrada a las variables `nombre_capa_lines` y `nombre_capa_polygons` con los nombres de las capas "lines" y "multipoligons" respectivamente que adquieren al importar el archivo osm; luego se elige el **osm_id** de calle que se desea descargar las imágenes (otra opcion es definiar una ruta personalizada en una nueva capa vectorial) indicado en el parámetro `osm_id_ruta`. 
* Al correr el código en QGIS (desde el editor de código de QGIS) se genera una carpeta por defecto de salida llamada `output` definido en parámetro `nombre_carpeta_salida`. En este carpeta se guardan las imágenes descargas y un archivo **CSV** con los metadatos de cada imagen como: su ubicación geográfica, parámetros fov , heading, vector unitario del segmento de línea de la calle y la url del API generado para la descarga.

## Detección
Para la detección de establecimientos comerciales hicimos uso de YOLOV4, la cual fue entrenada con imagenes obtenidas por el API de GSV que consta de 3000 iteraciones, con una unica clase denominada "establecimiento comercial" (para conocer nuestro codigo de entrenamiento, dirigirse al siguiente cuaderno de colab[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1Qwj6N8Zh4ExD2mi6BOvqPmhTAdrb8kp7?usp=sharing)). Estos elementos detectados son denominados objetos que pasarán a ser clasificados en 8 categorias de acuerdo a sus caracteristicas.

![pred_yolov4](/assets/example_yolov4_pred.png)

Nota: Existen casos de duplicidad de objetos en calles de circunvalación y para evitar tener datos repetidos, se consideró la función "distancia coseno" que permite conocer cuan similares son los objetos consecutivos, tomando asi solo un objeto y el promedio de las coordenadas de los objetos repetidos.
## Clasificación
Para la fase de clasificación, se dividió en dos fases: 
- **Clasificación VGG16:** Se entrenaron con 8 clases de establecimientos comerciales que son : boticas y farmacias, lugares de comida y bebida, lugares de estetica y cuidado, otros, sin negocios, tiendas de materiales de construccion, tiendas de productos de primera necesidad y tiendas de vestir. Haciendo uso de técnicas de "Data Augmentation" y "Transfern Learning" se lograron obtener resultados considerables.
Para poder ver nuestro codigo de entrenamiento, abrir el cuaderno en colab.
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1wBsW5cW34RjFDJWH7wqeClVHjMsiLAvu?usp=sharing)
- **Clasificación atravez de textos en imagenes naturales:**
Para mejorar la clasificación tambien se consideró los textos de los letreros en los negocios, debido a que contienen información del tipo de negocio, para ello se utilizarón las implementaciones de ("[**CRAFT: Character-Region Awareness For Text detection**"](https://github.com/clovaai/CRAFT-pytorch#craft-character-region-awareness-for-text-detection)") y ("[**AttentionOCR for Arbitrary-Shaped Scene Text Recognition**"](https://github.com/zhang0jhon/AttentionOCR)"), considerando lo mas destacable de cada proyecto en una sola implementación para nuestro objetivo. Existen casos donde los textos son cortados o dificiles de detectar, es por ello que se tomo en cuenta la función **Levenshtein** que nos ayuda a conocer si la palabra detectada existe en un determinado porcentaje (80%) de similaridad con respecto a las palabras de nuestro diccionario en español. Dicho diccionario cuenta con palabras clave pertenecientes a una determinada clase.

Por último promediando ambas predicciones se llega a un valor determinado que nos indica a que tipo de negocio pertenecen. Se toma considera las probablidades del **TOP-1**, **TOP-3** y **TOP-5**.
Para poder ver nuestro codigo de implementación, abrir el siguiente cuaderno en colab.
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1JaeBU1IwkXKgi0cJCzJcy4El6NQwqZbV?usp=sharing)


## Testing
Al finalizar el codigo genera un archivo **JSON**, que contiene la información de los objetos unicos como: valores del bounding boxes, path, clasificiación y ubicacion geografica.
Las pruebas se hicieron dentro de la ciudad del Cusco-Perú en 12 diferentes zonas urbanas y se obtuvieron los siguientes resultados.

![pred_yolov4](/assets/tabla_tops.png)
