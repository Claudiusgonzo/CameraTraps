#
# test_frozen_graph.py
#
# Runs a frozen graph against a set of images with known ground truth classifications, 
# printing accuracy results to the console
#

#%% Imports

import os
import argparse

import tensorflow as tf
import numpy as np
import tqdm
from pycocotools.coco import COCO


#%% Command-line handling

parser = argparse.ArgumentParser('This script evaluates the accuracy of an exported frozen inference graph on the test data of ' + \
                                'a classification dataset generated with the make_classification_dataset.py script. ')
parser.add_argument('--frozen_graph', type=str,
                    help='Frozen graph of detection network as create by export_inference_graph.py of TFODAPI.')
parser.add_argument('--coco_style_output', type=str,
                    help='Path to directory containing the coco-style output of make_classification_dataset.py')
args = parser.parse_args()

TEST_JSON = os.path.join(args.coco_style_output, 'test.json')

# Check that all files exist for easier debugging
assert os.path.exists(args.frozen_graph)
assert os.path.exists(args.coco_style_output)
assert os.path.exists(TEST_JSON), 'Could not find ' + TEST_JSON


#%% Inference and eval

# Load frozen graph
model_graph = tf.Graph()
with model_graph.as_default():
    od_graph_def = tf.GraphDef()
    with tf.gfile.GFile(args.frozen_graph, 'rb') as fid:
      od_graph_def.ParseFromString(fid.read())
      tf.import_graph_def(od_graph_def, name='')
graph = model_graph

coco = COCO(TEST_JSON)

with model_graph.as_default():
    
    with tf.Session() as sess:
        
        # Collect tensors for input and output
        image_tensor = tf.get_default_graph().get_tensor_by_name('input:0')
        predictions_tensor = tf.get_default_graph().get_tensor_by_name('output:0')
        predictions_tensor = tf.squeeze(predictions_tensor, [0])

        total = 0
        correct = 0
        for image_id in tqdm.tqdm(coco.imgs.keys()):
            # Read image
            image_path = os.path.join(args.coco_style_output, coco.imgs[image_id]['file_name'])
            if not os.path.exists(image_path):
                print('Image {} does not exist'.format(image_path))
                continue
            with open(image_path, 'rb') as fi:
                image = sess.run(tf.image.decode_jpeg(fi.read(), channels=3))
                image = image / 255.

            # Run inference
            predictions = sess.run(predictions_tensor, feed_dict={image_tensor: image})
            predicted_class = np.argmax(predictions)

            # Check if correct
            if coco.imgToAnns[image_id][0]['category_id'] == predicted_class:
                correct = correct + 1

            total = total + 1

            if total%100 == 0:
                print('Currently at {:.2f}% top-1 accuracy'.format(correct/total*100))

print('Final result is {:.2f}% top-1 accuracy'.format(correct/total*100))