# -*- coding: utf-8 -*-
import torch
import sys
sys.path.append('../')
from models import Variable
from sklearn.utils import shuffle
import matplotlib as mpl
import numpy as np

def init(epochs, log_file_name):
    use_cuda = torch.cuda.is_available()
    log = open(log_file_name, "w+")
    x_dtype = torch.cuda.FloatTensor if use_cuda else torch.FloatTensor
    y_dtype = torch.cuda.LongTensor if use_cuda else torch.LongTensor
    n_epochs = epochs
    criterion = torch.nn.CrossEntropyLoss()

    return  use_cuda, log, x_dtype, y_dtype, n_epochs, criterion


def train_by_one_epoch(model, X_train, Y_train, X_val, Y_val, criterion, use_cuda, log, x_dtype, y_dtype, n_epochs):
    if (use_cuda):
        model.cuda()

    print("use_cuda:",use_cuda)
    print("epochs:",n_epochs)

    """
    Train the network using Adam optimizer. 
    Train the network and test it for each line in the dataset 
    """
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-7)

    n_train = len(X_train)
    X_train = torch.from_numpy(X_train).type(x_dtype)
    Y_train = torch.from_numpy(Y_train).type(y_dtype)
    X_train = X_train.view(n_train, 1, 1, 431, 575)

    n_test = len(X_val)
    X_test = torch.from_numpy(X_val).type(x_dtype)
    Y_test = torch.from_numpy(Y_val).type(y_dtype)
    X_test = X_test.view(n_test, 1, 1, 431, 575)

    train_loss_curve = []
    val_loss_curve = []

    for epoch in range(n_epochs):
        model.train()
        epoch_loss_mean = []
        #Train the model
        idx = shuffle(range(n_train))
        print("Train size:", n_train)
        for i in idx :
            data_point = i

            x_var = Variable(X_train[data_point])
            y_var = Variable(Y_train[data_point])

            optimizer.zero_grad()
            y_pred = model(x_var)

            y_var.unsqueeze_(dim=0)
            train_loss = criterion(y_pred, y_var)
            train_loss.backward()
            optimizer.step()
            epoch_loss_mean.append(train_loss)

        #compute train loss
        train_total_loss = sum(epoch_loss_mean) / len(epoch_loss_mean)
        train_loss_curve.append(train_total_loss.item())
        print("Epoch: {0}, Train Loss: {1}, ".format(epoch, train_total_loss.item()))
        log.write("Epoch: {0}, Train Loss: {1}, \n".format(epoch, train_total_loss.item()))

        #compute Validation loss
        model.eval()
        epoch_loss_mean = []
        for data_point in range(n_test):
            x_var = Variable(X_test[data_point])
            y_var = Variable(Y_test[data_point])
            y_var.unsqueeze_(dim=0)
            y_pred = model(x_var)
            test_loss = criterion(y_pred, y_var)
            epoch_loss_mean.append(test_loss)
        test_total_loss = sum(epoch_loss_mean) / len(epoch_loss_mean)
        val_loss_curve.append(test_total_loss.item())
        log.write("Epoch: {0}, Validation Loss: {1},\n ".format(epoch, test_total_loss.item()))
        print("Epoch: {0}, Validation Loss: {1}, ".format(epoch, test_total_loss.item()))


    return train_loss_curve, val_loss_curve

def train_by_batches(model, X_train, Y_train, X_val, Y_val, criterion, use_cuda, log, x_dtype, y_dtype, n_epochs, batchSize):
    if (use_cuda):
        model.cuda()

    print("use_cuda:",use_cuda)
    print("num epochs:",n_epochs)
    print("batch size: ", batchSize)

    learning_rate = 1e-7

    """
    Train the network using Adam optimizer. 
    Train the network and validate it for each line in the dataset 
    """
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    n_train = batchSize
    n_val = round(0.2 * batchSize)
    train_loss_curve = []
    val_loss_curve = []

    for epoch in range(n_epochs):
        for batch in range(round(len(X_train)/batchSize)):
            """sample train val according to batch size"""
            indices = shuffle(range(batchSize))
            x = []
            for i in indices:
                x.append(X_train[i])
            x = np.asanyarray(x)
            y = np.take(Y_train, indices)

            indx = shuffle(range(n_val))
            x_val = []
            for i in indx:
                x_val.append(X_val[i])
            x_val = np.asanyarray(x_val)
            y_val = np.take(Y_val, indx)

            x = torch.from_numpy(x).type(x_dtype)
            y = torch.from_numpy(y).type(y_dtype)
            x = x.view(n_train, 1, 431, 575)

            x_val = torch.from_numpy(x_val).type(x_dtype)
            y_val = torch.from_numpy(y_val).type(y_dtype)
            x_val = x_val.view(n_val, 1, 431, 575)

            model.train()
            epoch_loss_mean = []
            #Train the model
            print("Train size:", n_train)

            x_var = Variable(x)
            y_var = Variable(y)

            optimizer.zero_grad()
            y_pred = model(x_var)

            train_loss = criterion(y_pred, y_var)
            train_loss.backward()
            optimizer.step()
            epoch_loss_mean.append(train_loss)

            #compute train loss
            train_total_loss = sum(epoch_loss_mean) / len(epoch_loss_mean)
            train_loss_curve.append(train_total_loss.item())
            print("Epoch: {0}, Train Loss: {1}, ".format(epoch, train_total_loss.item()))
            log.write("Epoch: {0}, Train Loss: {1}, \n".format(epoch, train_total_loss.item()))

            #compute Validation loss
            model.eval()
            epoch_loss_mean = []
            x_var = Variable(x_val)
            y_var = Variable(y_val)
            y_pred = model(x_var)
            test_loss = criterion(y_pred, y_var)
            epoch_loss_mean.append(test_loss)
            test_total_loss = sum(epoch_loss_mean) / len(epoch_loss_mean)
            val_loss_curve.append(test_total_loss.item())
            log.write("Epoch: {0}, Validation Loss: {1},\n ".format(epoch, test_total_loss.item()))
            print("Epoch: {0}, Validation Loss: {1}, ".format(epoch, test_total_loss.item()))


    return train_loss_curve, val_loss_curve

def test(model, X_test, Y_test, criterion, log, x_dtype, y_dtype):
    # compute test loss
    model.eval()
    epoch_loss_mean = []
    n_test = len(X_test)
    X_test = torch.from_numpy(X_test).type(x_dtype)
    Y_test = torch.from_numpy(Y_test).type(y_dtype)
    X_test = X_test.view(n_test, 1, 1, 431, 575)
    for data_point in range(n_test):
        x_var = Variable(X_test[data_point])
        y_var = Variable(Y_test[data_point])
        y_var.unsqueeze_(dim=0)
        y_pred = model(x_var)
        test_loss = criterion(y_pred, y_var)
        epoch_loss_mean.append(test_loss)
    test_total_loss = sum(epoch_loss_mean) / len(epoch_loss_mean)
    log.write("Final Test Loss: {0},\n ".format(test_total_loss.item()))
    print("Final Test Loss: {0}, ".format(test_total_loss.item()))

    return test_total_loss

def plot_train_val_loss_curve(use_cuda, n_epochs, train_loss_curve, val_loss_curve):
    if use_cuda:
        mpl.use('Agg')
        import matplotlib.pyplot as plt

        plt.ioff()  # http://matplotlib.org/faq/usage_faq.html (interactive mode)
    else:
        import matplotlib.pyplot as plt

    plt.title('Loss function value for validation and train after each epoch')
    plt.xlabel('epoch')
    plt.ylabel('loss')

    epochs = list(range(1, 850 + 1))
    plt.plot(epochs, train_loss_curve, 'b', label='Q1 Train Data')
    plt.plot(epochs, val_loss_curve, 'r', label='Q1 Validation Data')

    plt.legend(loc='best')
    plt.savefig('cnn_train_val_plot.png')

    return plt