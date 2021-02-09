import os
import sys
import numpy as np
import time

import tensorflow as tf
import matplotlib.gridspec as gridspec
import textwrap
import cv2
import tensorflow as tf

from atten_ocr.util import *
# *******************
import argparse
import atten_ocr.config as cfg
from atten_ocr.common import polygons_to_mask
# *******************


class TextRecognition(object):

    def __init__(
        self,
        pb_file,
        seq_len,
        config,
        ):
        self.pb_file = pb_file
        self.config = config
        self.seq_len = seq_len
        self.init_model()

    def init_model(self):
        self.graph = tf.Graph()
        with self.graph.as_default():
            with tf.io.gfile.GFile(self.pb_file, 'rb') as f:
                graph_def = tf.compat.v1.GraphDef()
                graph_def.ParseFromString(f.read())
                _ = tf.import_graph_def(graph_def, name='')

        self.sess = tf.compat.v1.Session(graph=self.graph,
                config=self.config)

        self.img_ph = self.sess.graph.get_tensor_by_name('image:0')
        self.is_training = \
            self.sess.graph.get_tensor_by_name('is_training:0')
        self.dropout = self.sess.graph.get_tensor_by_name('dropout:0')
        self.preds = \
            self.sess.graph.get_tensor_by_name('sequence_preds:0')
        self.probs = \
            self.sess.graph.get_tensor_by_name('sequence_probs:0')

    def predict(
        self,
        image,
        label_dict,
        EOS='EOS',
        ):
        results = []
        probabilities = []

        (pred_sentences, pred_probs) = self.sess.run([self.preds,
                self.probs], feed_dict={self.is_training: False,
                self.dropout: 1.0, self.img_ph: image})

        for char in pred_sentences[0]:
            if label_dict[char] == EOS:
                break
            results.append(label_dict[char])
        probabilities = (pred_probs[0])[:min(len(results) + 1,
                self.seq_len)]

        return (results, probabilities)


def preprocess(image, points, size=cfg.image_size):
    """
    Preprocess for test.
    Args:
        image: test image
        points: text polygon
        size: test image size
    """

    (height, width) = image.shape[:2]
    mask = polygons_to_mask([np.asarray(points, np.float32)], height,
                            width)
    (x, y, w, h) = cv2.boundingRect(mask)
    mask = np.expand_dims(np.float32(mask), axis=-1)
    image = image * mask
    image = image[y:y + h, x:x + w, :]

    (new_height, new_width) = ((size, int(w * size / h)) if h
                               > w else (int(h * size / w), size))
    image = cv2.resize(image, (new_width, new_height))

    if new_height > new_width:
        (padding_top, padding_down) = (0, 0)
        padding_left = (size - new_width) // 2
        padding_right = size - padding_left - new_width
    else:
        (padding_left, padding_right) = (0, 0)
        padding_top = (size - new_height) // 2
        padding_down = size - padding_top - new_height

    image = cv2.copyMakeBorder(
        image,
        padding_top,
        padding_down,
        padding_left,
        padding_right,
        borderType=cv2.BORDER_CONSTANT,
        value=[0, 0, 0],
        )

    image = image / 255.
    return image

parser = argparse.ArgumentParser(description='OCR')
parser.add_argument('--pb_path', type=str,
                    help='path to tensorflow pb model',
                    default='/content/drive/My Drive/TESIS/AttentionOCR-Deteccion/checkpoint/text_recognition_5435.pb')
parser.add_argument('--img_folder', type=str,
                    help='path to image folder',
                    default='/content/drive/My Drive/TESIS/AttentionOCR-Deteccion/imagenes')
                    #default='/content/drive/My Drive/TESIS/modulos-ocr/result')
parser.add_argument("-f", "--fff", help="a dummy argument to fool ipython", default="1")
args = parser.parse_args()



def test_ocr(array_crops):
    tf_config = \
        tf.compat.v1.ConfigProto(gpu_options=tf.compat.v1.GPUOptions(allow_growth=True),
                                 allow_soft_placement=True)

    model = TextRecognition(args.pb_path, cfg.seq_len + 1, config=tf_config)
    array_text_ocr = []
    for image in array_crops:
        #img_path = os.path.join(args.img_folder, filename)
        #image = cv2.imread(img_path)
        #image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        (height, width) = image.shape[:2]
        if width >0 and height>0:
            points = [[0, 0], [width - 1, 0], [width - 1, height - 1], [0,
                      height - 1]]
    
            image = preprocess(image, points, cfg.image_size)
            image = np.expand_dims(image, 0)
    
            before = time.time()
            (preds, probs) = model.predict(image, cfg.label_dict)
            after = time.time()
            #print (preds, probs)
            #un solo string
            palabra=''.join(preds)
            array_text_ocr.append(palabra)
    return array_text_ocr

