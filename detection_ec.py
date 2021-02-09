def init_yolov4():
    # Clonar repositorio de github de YOLO
    if not os.path.exists('darknet'):
    !git clone https://github.com/AlexeyAB/darknet
    # change makefile to have GPU and OPENCV enabled
    %cd darknet
    # Habilitar GPU y OPENCV en Makefile
    !sed -i 's/OPENCV=0/OPENCV=1/' Makefile
    !sed -i 's/GPU=0/GPU=1/' Makefile
    !sed -i 's/CUDNN=0/CUDNN=1/' Makefile
    !sed -i 's/CUDNN_HALF=0/CUDNN_HALF=1/' Makefile
    # make yolov4
    !make
    %cd ..
