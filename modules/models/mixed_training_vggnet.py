# USAGE
# python mixed_training.py

# import the necessary packages
from modules.models import cnn_multi_input
from modules.data.datasets import DatasetBuilder
from modules.data.stim import Stim
from sklearn.metrics import roc_curve
from sklearn.metrics import auc
from matplotlib import pyplot as plt
import yaml
from sklearn.utils import shuffle
from keras.layers.core import Dense
from keras.layers.convolutional import MaxPooling2D
from keras.layers.core import Flatten
from keras.layers.convolutional import Conv2D
from keras.models import Model
from keras.optimizers import Adam
from keras.layers import concatenate
import numpy as np
import pandas as pd
from keras.layers.core import Dropout

import scipy.misc

seed = 10
datasetbuilder = DatasetBuilder()
path = "../../etp_data/processed/fixation_df__40_subjects.pkl"
stimType = "Face"
maps, images, labels, stim_size = datasetbuilder.load_fixations_related_datasets(stimType, path)
split = datasetbuilder.train_test_val_split_subjects_balnced(maps, images, labels, seed)
trainMapsX, valMapsX, testMapsX, trainImagesX, valImagesX, testImagesX, trainY, valY, testY = split

# create the two CNN models
vgg_map_model = cnn_multi_input.create_vggNet(stim_size[0], stim_size[1], 3)
vgg_image_model = cnn_multi_input.create_vggNet(stim_size[0], stim_size[1], 3)

for layer in vgg_map_model.layers:
	layer.name = layer.name + str("_map")
	#layer.trainable = False

for layer in vgg_image_model.layers:
	layer.name = layer.name + str("_image")
	layer.trainable = False

# create the input to our final set of layers as the *output* of both CNNs
combinedInput = concatenate([vgg_map_model.output, vgg_image_model.output])

# Stacking a new simple convolutional network on top of it
x = Conv2D(filters=64, kernel_size=(3, 3), activation='relu')(combinedInput)
x = MaxPooling2D(pool_size=(2, 2))(x)
x = Flatten()(x)
x = Dense(256, activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(1, activation='sigmoid')(x)

# our final model will accept scanpth on one CNN
# input and images on the second CNN input, outputting a single value as high or low bid (1/0)
model = Model(inputs=[vgg_map_model.input, vgg_image_model.input], outputs=x)
print(model.summary())

for layer in model.layers:
  print(layer.name)


# compile the model using mean absolute percentage error as our loss,
# implying that we seek to minimize the absolute percentage difference
# between our price *predictions* and the *actual prices*
opt = Adam(lr=1e-3, decay=1e-3 / 200)
model.compile(loss='binary_crossentropy', optimizer=opt,  metrics=['accuracy'])

# shuffle data
trainMapsX, trainImagesX, trainY = shuffle(trainMapsX, trainImagesX, trainY, random_state=seed)
valMapsX, valImagesX, valY = shuffle(valMapsX, valImagesX, valY, random_state=seed)

# train the model
print("[INFO] training model...")
history = model.fit(
	[trainMapsX, trainImagesX], trainY,
	validation_data=([valMapsX, valImagesX], valY),
	epochs=10, batch_size=16)

# plot metrics
# summarize history for accuracy
fig = plt.figure(2)
plt.plot(history.history['accuracy'])
plt.plot(history.history['val_accuracy'])
plt.title('model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
fig.savefig("../../etp_data/processed/figs/" + stimName + "train_val_acc.pdf", bbox_inches='tight')
plt.show()
# summarize history for loss
fig = plt.figure(3)
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
fig.savefig("../../etp_data/processed/figs/" + stimName + "train_val_loss.pdf", bbox_inches='tight')
plt.show()

# shuffle data
testMapsX, testImagesX, testY = shuffle(testMapsX, testImagesX, testY, random_state=seed)

#model evaluate
results = model.evaluate([testMapsX, testImagesX], testY, batch_size=128)
print('test loss, test acc:', results)
# make predictions on the testing data
predY = model.predict([testMapsX, testImagesX]).ravel()
fpr_keras, tpr_keras, thresholds_keras = roc_curve(testY, predY)

auc_keras = auc(fpr_keras, tpr_keras)

fig = plt.figure(1)
plt.plot([0, 1], [0, 1], 'k--')
plt.plot(fpr_keras, tpr_keras, label='Area Under Roc = {:.3f}'.format(auc_keras))
#plt.plot(fpr_rf, tpr_rf, label='RF (area = {:.3f})'.format(auc_rf))
plt.xlabel('False positive rate')
plt.ylabel('True positive rate')
plt.title('ROC curve')
plt.legend(loc='best')
fig.savefig("../../etp_data/processed/figs/" + stimName + "roc.pdf", bbox_inches='tight')
plt.show()