import numpy as np
import cv2
import pandas as pd
from modules.data.visualization import DataVis
from sklearn.utils import shuffle
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from keras.utils import to_categorical
import scipy.misc
import os
from modules.data.stim import Stim
import yaml
import random
from modules.data.preprocessing import DataPreprocess


class DatasetBuilder:

    def __init__(self):
        currpath = os.getcwd()
        self.datapath = "/export/home/DATA/schonberglab/pycharm_eyePredict/etp_data/processed/"
        self.imgpath = "/export/home/DATA/schonberglab/pycharm_eyePredict/etp_data/"
        expconfig = "/experimentconfig.yaml"
        with open(currpath + expconfig, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)

        self.stimSnack = Stim(cfg['exp']['etp']['stimSnack']['name'], cfg['exp']['etp']['stimSnack']['id'],
                         cfg['exp']['etp']['stimSnack']['size'])
        self.stimFace = Stim(cfg['exp']['etp']['stimFace']['name'], cfg['exp']['etp']['stimFace']['id'],
                        cfg['exp']['etp']['stimFace']['size'])
        self.stims_array = [self.stimFace, self.stimSnack]
        self.data_process = DataPreprocess(cfg['exp']['etp']['name'],
                              cfg['exp']['etp']['both_eye_path'],
                              cfg['exp']['etp']['one_eye_path1'],
                              cfg['exp']['etp']['trial_start_str'],
                              cfg['exp']['etp']['trial_end_str'],
                              cfg['exp']['etp']['output_file_both_eye'],
                              cfg['exp']['etp']['output_file_one_eye1'], [self.stimSnack, self.stimFace])
        self.screen_resolution = cfg['exp']['etp']['screen_resolution']
        self.fixation_only = False


    def get_fixation_dataset(self, data_df):
        print('Log..... Build fixation dataset')
        fixation_dataset = []
        for sampleId in data_df.sampleId.unique():
            sample_data = []
            bid = data_df[data_df['sampleId'] == sampleId].bid.unique()
            stimName = data_df[data_df['sampleId'] == sampleId].stimName.unique()
            stimType = data_df[data_df['sampleId'] == sampleId].stimType.unique()
            sample = data_df[data_df['sampleId'] == sampleId].sampleId.unique()
            for stim in self.stims_array:
                if stim.name == stimType:
                    fixationMap = self.data_to_fixation_map_by_sampleId(data_df, sampleId, stim)

            if type(fixationMap) is not np.ndarray:
                continue
            sample_data.append(stimName[0])
            sample_data.append(stimType[0])
            sample_data.append(sample[0])
            sample_data.append(fixationMap)
            sample_data.append(bid[0])
            fixation_dataset.append(sample_data)

        fixation_df = pd.DataFrame(fixation_dataset)
        fixation_df.columns = ['stimName', 'stimType', 'sampleId', 'fixationMap', 'bid']

        return fixation_df

    def data_to_fixation_map_by_sampleId(self, data_df, sampleId, stim):
        print('Log..... get fixation map for sampleId: ', sampleId)
        x = data_df[data_df['sampleId'] == sampleId].X_axis
        y = data_df[data_df['sampleId'] == sampleId].Y_axis
        if len(x) | len(y) < 5:
            print('Fixation data is None for sampleId: ', sampleId)
            return None
        xedges = np.arange(stim.size[0])
        yedges = np.arange(stim.size[1])

        heatmap, xedges, yedges = np.histogram2d(x, y, bins=(xedges, yedges))
        heatmap = heatmap.T  # Let each row list bins with common y range.

        return heatmap

    def get_scanpath_dataset(self, data_df):
        print('Log..... Build scanpath dataset')
        scanpath_dataset = []
        for sampleId in data_df.sampleId.unique():
            sample_data = []
            bid = data_df[data_df['sampleId'] == sampleId].bid.unique()
            #subjectID = data_df[data_df['sampleId'] == sampleId].subjectID.unique()
            stimName = data_df[data_df['sampleId'] == sampleId].stimName.unique()
            stimType = data_df[data_df['sampleId'] == sampleId].stimType.unique()
            sample = data_df[data_df['sampleId'] == sampleId].sampleId.unique()
            scanpath = self.data_to_scanpath(data_df, sampleId)
            if type(scanpath) is not np.ndarray:
                continue
            #sample_data.append(subjectID[0])
            sample_data.append(stimName[0])
            sample_data.append(stimType[0])
            sample_data.append(sample[0])
            sample_data.append(scanpath)
            sample_data.append(bid[0])
            scanpath_dataset.append(sample_data)

        scanpath_df = pd.DataFrame(scanpath_dataset)
        scanpath_df.columns = ['stimName', 'stimType', 'sampleId', 'scanpath', 'bid']

        return scanpath_df

    def data_to_scanpath(self, data_df, sampleId):
        print('Log..... get scanpath data for sampleId: ', sampleId)
        # todo - add downsampling option for the data poinnts
        scanpath = []
        t = data_df[data_df['sampleId'] == sampleId].timeStamp.astype(int)
        x = data_df[data_df['sampleId'] == sampleId].X_axis.astype(int)
        y = data_df[data_df['sampleId'] == sampleId].Y_axis.astype(int)
        if len(x) | len(y) < 5:
            print('Scanpath data is None for sampleId: ', sampleId)
            return None
        # scanpath.append(t)
        scanpath.append(x)
        scanpath.append(y)

        scanpath = np.asanyarray(scanpath).T

        return np.asanyarray(scanpath)

    def load_fixation_maps_dataset(self, df):
        print("Log.....Loading maps")
        df['fixationMap'] = df['fixationMap'].apply(lambda x: np.pad(x, [(0, 1), (0, 1)], mode='constant'))
        df['fixationMap'] = df['fixationMap'].apply(lambda x: cv2.cvtColor(np.uint8(x), cv2.COLOR_GRAY2RGB) * 255)
        df['fixationMap'] = df['fixationMap'].apply(lambda x: x / 255)

        return df[["sampleId", "fixationMap"]]

    def load_scanpath_dataset(self, df):
        print("Log.....Loading scanpaths")
        return df[["sampleId", "scanpath"]]

    def load_images_dataset(self, currpath, df, img_size):
        print("Log.....Loading images")
        img_dict = {}
        for image in np.asanyarray(df.stimName.unique()):
            #print("loading image - " + image)
            img = DataVis.stimulus(currpath, "Stim_0/", image)
            img = cv2.resize(img, img_size)
            img = img / 255
            img_dict[image] = img
        img_df = pd.DataFrame(list(img_dict.items()), columns=['stimName', 'img'])
        #scipy.misc.imsave("../../etp_data/processed/temp0.jpg", img_dict["1_1027.jpg"])
        newdf = pd.merge(df, img_df, on='stimName', how='left')
        #x = dfnew[dfnew['stimName'] == "1_1027.jpg"]
        #scipy.misc.imsave("../../etp_data/processed/temp1.jpg", x["img"].values[0])

        return newdf[["sampleId", "stimName", "img"]]

    def load_images_for_scanpath_dataset(self, currpath, df, img_size):
        print("Log.....Loading images")
        img_dict = {}
        for image in np.asanyarray(df.stimName.unique()):
            #print("loading image - " + image)
            img = DataVis.stimulus(currpath, "Stim_0/", image)
            img = cv2.resize(img, img_size)
            img_dict[image] = img
        img_df = pd.DataFrame(list(img_dict.items()), columns=['stimName', 'img'])
        newdf = pd.merge(df, img_df, on='stimName', how='left')

        return newdf[["sampleId", "stimName", "img"]]

    def load_labels_dataset(self, df):
        print("Log.....Loading labels")
        df['binary_bid'] = pd.qcut(df.bid, 2, labels=[0, 1])
        df['binary_bid_n'] = pd.qcut(df.bid, 2, labels=[-1, 1])
        df['five_bins_bid'] = pd.qcut(df.bid, 5, labels=[0, 1, 2, 3, 4])

        return df[["sampleId", "bid", "five_bins_bid", "binary_bid", "binary_bid_n"]]

    def find_sparse_samples(self, df, sparse_threshold):
        df['scanpath_len'] = 0
        for i in range(df.scanpath.size):
            df.at[i, 'scanpath_len'] = len(df.scanpath[i])
        # getting spars samples indexes
        sparse_indexes = df.index[df.scanpath_len < sparse_threshold].tolist()  # > 85%

        return sparse_indexes

    def datasets_loader(self, fixation_df, scanpath_df, stimType, colorpathTimeSet):
        print("Log.....Loading datasets")
        # choose stim to run on
        for stim in self.stims_array:
            if stim.name == stimType:
                stim_name = stim.name
                stim_size = stim.size
        fixation_df_by_stim = fixation_df[fixation_df['stimType'] == stim_name]
        fixation_df_by_stim.reset_index(inplace=True)
        scanpath_df_by_stim = scanpath_df[scanpath_df['stimType'] == stim_name]
        scanpath_df_by_stim.reset_index(inplace=True)
        stim_size = (stim_size[0], stim_size[1])

        scanpaths = self.load_scanpath_dataset(scanpath_df_by_stim)
        maps = self.load_fixation_maps_dataset(fixation_df_by_stim)
        images = self.load_images_dataset(self.imgpath, fixation_df_by_stim, stim_size)
        labels = self.load_labels_dataset(fixation_df_by_stim)
        colorpath = self.get_time_colored_dataset(scanpaths, maps, images, labels, stimType, colorpathTimeSet)

        return scanpaths, maps, colorpath, images, labels, stim_size

    def load_fixations_related_datasets(self, fixation_df, stimType):
        print("Log.....Reading fixation data")
        # choose stim to run on
        for stim in self.stims_array:
            if stim.name == stimType:
                stim_name = stim.name
                stim_size = stim.size
        fixation_df_by_stim = fixation_df[fixation_df['stimType'] == stim_name]
        fixation_df_by_stim.reset_index(inplace=True)
        stim_size = (stim_size[0], stim_size[1])

        maps = self.load_fixation_maps_dataset(fixation_df_by_stim)
        images = self.load_images_dataset(self.imgpath, fixation_df_by_stim, stim_size)
        labels = self.load_labels_dataset(fixation_df_by_stim)

        return maps, images, labels, stim_size

    def load_scanpath_related_datasets(self, scanpath_df, stimType):
        print("Log.....Reading scanpath data")
        scanpath_df = scanpath_df
        # choose stim to run on
        for stim in self.stims_array:
            if stim.name == stimType:
                stim_name = stim.name
                stim_size = stim.size
        scanpath_df_by_stim = scanpath_df[scanpath_df['stimType'] == stim_name]
        scanpath_df_by_stim.reset_index(inplace=True)
        stim_size = (stim_size[0], stim_size[1])

        scanpaths = self.load_scanpath_dataset(scanpath_df_by_stim)
        images = self.load_images_for_scanpath_dataset(self.imgpath, scanpath_df_by_stim, stim_size)
        labels = self.load_labels_dataset(scanpath_df_by_stim)

        return scanpaths, images, labels, stim_size

    def train_test_val_split_stratify_by_subject(self, df, seed, is_fixation, is_patch, is_colored_path, binary_bid, binary_bid_n, five_bins_bid):

        try:
            print("Log... reading train test json files")
            train = pd.read_json(self.datapath + "train_set.json")
            test = pd.read_json(self.datapath + "test_set.json")
        except:
            print("Building train, val, test datasets...")
            df["subjectId"] = df['sampleId'].apply(lambda x: x.split("_")[0])
            train, test = train_test_split(df, stratify=df[['subjectId']],
                                         test_size=0.20, random_state=seed)
            train.to_json(self.datapath + "train_set.json")
            test.to_json(self.datapath + "test_set.json")

        train, val = train_test_split(train, stratify=train[['subjectId']],
                                     test_size=0.20, random_state=seed)
        if is_patch:
            trainMapsX = np.asanyarray(train.patch.tolist())
            valMapsX = np.asanyarray(val.patch.tolist())
            testMapsX = np.asanyarray(test.patch.tolist())
        elif is_colored_path:
            trainMapsX = np.asanyarray(train.colored_path.tolist())
            valMapsX = np.asanyarray(val.colored_path.tolist())
            testMapsX = np.asanyarray(test.colored_path.tolist())
        elif is_fixation:
            trainMapsX = np.asanyarray(train.fixationMap.tolist())
            valMapsX = np.asanyarray(val.fixationMap.tolist())
            testMapsX = np.asanyarray(test.fixationMap.tolist())
        else:
            trainMapsX = np.asanyarray(train.sacnpath.tolist())
            valMapsX = np.asanyarray(val.sacnpath.tolist())
            testMapsX = np.asanyarray(test.sacnpath.tolist())
        trainImagesX = np.asanyarray(train.img.tolist())
        valImagesX = np.asanyarray(val.img.tolist())
        testImagesX = np.asanyarray(test.img.tolist())
        if binary_bid:
            trainY = np.asanyarray(train.binary_bid.tolist())
            valY = np.asanyarray(val.binary_bid.tolist())
            testY = np.asanyarray(test.binary_bid.tolist())
        elif five_bins_bid:
            trainY = np.asanyarray(train.five_bins_bid.tolist())
            valY = np.asanyarray(val.five_bins_bid.tolist())
            testY = np.asanyarray(test.five_bins_bid.tolist())
        elif binary_bid_n:
            trainY = np.asanyarray(train.binary_bid_n.tolist())
            valY = np.asanyarray(val.binary_bid_n.tolist())
            testY = np.asanyarray(test.binary_bid_n.tolist())

        return trainMapsX, valMapsX, testMapsX, trainImagesX, valImagesX, testImagesX, trainY, valY, testY


    def create_patches_dataset(self, currpath, scanpaths, images, labels, num_patches, patch_size, saliency):
        print("Log.....Building patches")
        df = scanpaths.merge(images, on='sampleId').merge(labels,on='sampleId')
        sparse_indexes = self.find_sparse_samples(df, 2300)
        df.drop(df.index[sparse_indexes], inplace=True)
        df.reset_index(inplace=True)
        patches_list = []
        for scanpath, img in zip(df.scanpath, df.img):
            #scipy.misc.imsave(currpath + "/etp_data/processed/patches/" + "original_img.jpg", img)
            if saliency:
                # initialize OpenCV's static saliency spectral residual detector and
                # compute the saliency map
                saliency = cv2.saliency.StaticSaliencyFineGrained_create()
                (success, img) = saliency.computeSaliency(img)
                img = (img * 255).astype("uint8")
                #scipy.misc.imsave("../../etp_data/processed/patches/" + "saliency_img.jpg", img)
            # Compute clusters Means through time
            fixations_centers = []
            clusters = np.array_split(scanpath, num_patches)
            for i in clusters:
                center = np.mean(i, axis=0).round().astype(int)
                fixations_centers.append(center)
            #build patches around the fixations_centers
            patches = []
            patch_num = 1
            for xi, yi in fixations_centers:
                length = int(patch_size/2)
                patch = img[yi - length: yi + length, xi - length: xi + length]
                padx = patch_size - patch.shape[0]
                pady = patch_size - patch.shape[1]
                patch = cv2.copyMakeBorder(patch, 0, padx, 0, pady, cv2.BORDER_CONSTANT)
                #scipy.misc.imsave("../../etp_data/processed/patches/" + str(patch_num) + "_patch_ORG.jpg", patch)
                patch = patch/255
                if saliency:
                    patch = patch[:, :, np.newaxis]
                patches.append(patch)
                patch_num += 1
            patches_list.append(np.asanyarray(patches))

        df["patch"] = patches_list
        df['img'] = df['img'].apply(lambda x: x / 255)
        df = df[["sampleId", "patch", "img", "five_bins_bid", "binary_bid", "binary_bid_n"]]

        return df

    def create_stacked_frames_dataset(self, df):
        print("Log.... Stacking frames")
        df['patch'] = df['patch'].apply(lambda x: np.concatenate(x, axis=2))
        print(df['patch'][0].shape)
        return df


    def get_scanpath_for_simple_lstm(self, scanpaths, images, labels):
        df = scanpaths.merge(images,on='sampleId').merge(labels,on='sampleId')
        sparse_indexes = self.find_sparse_samples(df, 2300)
        df.drop(df.index[sparse_indexes], inplace=True)
        df.reset_index(inplace=True)

        return df

    def get_fixations_for_cnn(self, scanpaths, maps, images, labels):
        df = maps.merge(images,on='sampleId').merge(labels,on='sampleId').merge(scanpaths,on='sampleId')
        sparse_indexes = self.find_sparse_samples(df, 2300)
        df.drop(df.index[sparse_indexes], inplace=True)
        df.reset_index(inplace=True)

        return df

    def get_datasets_df(self, scanpaths, maps, colorpath, images, labels):
        print("Log.....Datasets to DF")
        df = maps.merge(images, on='sampleId').merge(labels, on='sampleId').merge(scanpaths, on='sampleId').merge(colorpath, on='sampleId')
        sparse_indexes = self.find_sparse_samples(df, 2300)
        df.drop(df.index[sparse_indexes], inplace=True)
        df.reset_index(inplace=True)

        return df

    def get_scanpath_df(self, scanpaths, images, labels):
        print("Log.....Datasets to DF")
        df = scanpaths.merge(images, on='sampleId').merge(labels, on='sampleId')
        sparse_indexes = self.find_sparse_samples(df, 2300)
        df.drop(df.index[sparse_indexes], inplace=True)
        df.reset_index(inplace=True)

        return df

    def get_time_colored_dataset(self, df, stimType, timePeriodMilisec):
        colored_path_list = []

        for stim in self.stims_array:
            if stim.name == stimType:
                stim_size = stim.size
        print("Log... Building time colored dataset")
        for scanpath in df.scanpath:
            blank_img = np.zeros((stim_size[0], stim_size[1], 3), np.uint8)
            toPlot = [cv2.resize(blank_img, (stim_size[0], stim_size[1]))]

            for i in range(np.shape(scanpath)[0]):
                if (i % timePeriodMilisec) == 0:
                    r = random.randint(0, 255)
                    g = random.randint(0, 255)
                    b = random.randint(0, 255)
                    rgb = [r, g, b]
                fixation = scanpath[i].astype(int)

                frame = np.copy(toPlot[-1]).astype(np.uint8)

                if i > 0:
                    prec_fixation = scanpath[i - 1].astype(int)
                    cv2.line(frame, (prec_fixation[0], prec_fixation[1]), (fixation[0], fixation[1]), rgb,
                             thickness=3, lineType=8, shift=0)

                toPlot.append(frame)

            colored_path_list.append(frame)

        df["colored_path"] = colored_path_list
        df['colored_path'] = df['colored_path'].apply(lambda x: x / 255)
        df.to_json(self.datapath + "colored_path_dataset_" + stimType + "_" + str(timePeriodMilisec) + "_milisec.json")

        return df[["sampleId", "colored_path"]]

    def processed_scanpath_data_loader(self):
        print("Log... reading scanpath df's")
        scanpath_df = pd.read_pickle(self.datapath + "scanpath_df_52_subjects.pkl")

        return self.stims_array, scanpath_df

    def processed_data_loader(self):
        print("Log... reading fixation and scanpath pickle's")
        fixation_df = pd.read_pickle(self.datapath + "fixation_df_52_subjects.pkl")
        scanpath_df = pd.read_pickle(self.datapath + "scanpath_df_52_subjects.pkl")

        return self.stims_array, scanpath_df, fixation_df

    def new_data_process(self, x_subjects):
        print("Log... processing raw data to csv")
        both_eye_data_path = self.data_process.read_eyeTracking_data_both_eye_recorded(self.fixation_only)
        one_eye_data_path = self.data_process.read_eyeTracking_data_one_eye_recorded(self.fixation_only)
        both_eye_data = pd.read_csv(both_eye_data_path)
        one_eye_data = pd.read_csv(one_eye_data_path)
        all_data = pd.concat([both_eye_data, one_eye_data])
        tidy_data = self.data_process.data_tidying_for_dataset_building(all_data, self.screen_resolution)
        tidy_data.to_pickle(self.datapath + "tidy_data_" + x_subjects + "_subjects.pkl")
        fixation_df = self.get_fixation_dataset(tidy_data)
        scanpath_df = self.get_scanpath_dataset(tidy_data)
        fixation_df.to_pickle(self.datapath + "fixation_df__" + x_subjects + "_subjects.pkl")
        scanpath_df.to_pickle(self.datapath + "scanpath_df__" + x_subjects + "_subjects.pkl")

    def train_test_val_split(self, stimType, scanpath_df, fixation_df, seed):

        try:
            print("Log... reading train test json files")
            train = pd.read_json(self.datapath + stimType + "train_set.json")
            test = pd.read_json(self.datapath + stimType + "test_set.json")
        except:
            print("Log... Building train, val, test datasets...")
            df = scanpath_df.merge(fixation_df, on='sampleId')
            df = df[['stimName_x', 'stimType_x', 'sampleId', 'scanpath', 'fixationMap', 'bid_x']]
            df.rename(columns={"stimName_x": "stimName", "stimType_x": "stimType", "bid_x": "bid"}, inplace=True)
            sparse_indexes = self.find_sparse_samples(df, 2300)
            df.drop(df.index[sparse_indexes], inplace=True)
            df.reset_index(inplace=True)
            df_by_stim = df[df['stimType'] == stimType]

            df_by_stim["subjectId"] = df_by_stim['sampleId'].apply(lambda x: x.split("_")[0])
            train, test = train_test_split(df_by_stim, stratify=df_by_stim[['subjectId']], test_size=0.10, random_state=33)

            print("Log... Saving train, test datasets to json...")
            train.to_json(self.datapath + stimType + "train_set.json")
            test.to_json(self.datapath  + stimType + "test_set.json")

        train, val = train_test_split(train, stratify=train[['subjectId']],
                                     test_size=0.10, random_state=seed)

        return train, val, test

    def preper_data_for_model(self, df, stimType, is_scanpath, is_fixation, is_coloredpath,
                              color_split, is_img):

        for stim in self.stims_array:
            if stim.name == stimType:
                stim_size = stim.size
        labels = self.load_labels_dataset(df)
        if is_scanpath:
            scanpaths = self.load_scanpath_dataset(df)
            final_df = scanpaths.merge(labels, on='sampleId')
        if is_fixation:
            maps = self.load_fixation_maps_dataset(df)
            final_df = maps.merge(labels, on='sampleId')
        if is_coloredpath:
            colorpath = self.get_time_colored_dataset(df, stimType, color_split)
            final_df = colorpath.merge(labels, on='sampleId')
        if is_img:
            images = self.load_images_dataset(self.imgpath, df, stim_size)
            final_df = final_df.merge(images, on='sampleId')


        return final_df





