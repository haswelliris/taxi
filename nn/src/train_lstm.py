#! /usr/bin/env python

from config import Train_CSV_Path,Test_CSV_Path
from config import dis_size,emb_size,MAX_LENGTH
from utils import load_emb_input,load_te_seq_input,load_con_input
from utils import caluate_point,hdist
from utils import prepare_inputX,save_results
from utils import train_generator,getValData


import h5py
import numpy as np
import pandas as pd
import math as Math
from time import time
import cPickle as pickle

from keras.models import model_from_json,Sequential
from keras.layers.core import Dense,Dropout,Activation,Flatten,Masking,Merge,Lambda
from keras.layers.recurrent import LSTM
from keras.layers.embeddings import Embedding
from keras.optimizers import SGD,Adagrad
from keras.layers import BatchNormalization
from keras.callbacks import EarlyStopping,ModelCheckpoint


model_name = 'LSTM_0.1'
result_csv_path = 'result/'+model_name+'.csv'



def load_test_dataset():
    tr_con_input,te_con_input = load_con_input()
    te_con_feature = te_con_input['con_input']

    tr_emb_input,te_emb_input, vocabs_size = load_emb_input()
    te_emb_feature = te_emb_input['emb_input']

    te_seq_input = load_te_seq_input()
    te_seq_feature = te_seq_input['seq_input']

    return te_con_feature,te_emb_feature,te_seq_feature,vocabs_size


def build_lstm(n_con,n_emb,vocabs_size,n_dis,emb_size,cluster_size):
    hidden_size = 800
    
    con = Sequential()
    con.add(Dense(input_dim=n_con,output_dim=emb_size))

    emb_list = []
    for i in range(n_emb):
        emb = Sequential()
        emb.add(Embedding(input_dim=vocabs_size[i],output_dim=emb_size,input_length=n_dis))
        emb.add(Flatten())
        emb_list.append(emb)


    in_dimension = 2
    seq = Sequential()
    seq.add(BatchNormalization(input_shape=((MAX_LENGTH,in_dimension))))
    seq.add(Masking([0]*in_dimension,input_shape=(MAX_LENGTH,in_dimension)))
    seq.add(LSTM(emb_size,return_sequences=False,input_shape=(MAX_LENGTH,in_dimension)))

    model = Sequential()
    model.add(Merge([con]+emb_list+[seq],mode='concat'))
    model.add(BatchNormalization())
    model.add(Dense(hidden_size,activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(cluster_size,activation='softmax'))
    model.add(Lambda(caluate_point,output_shape=[2]))
    return model

def main():
    batches_per_epoch = 250
    generate_size = 200
    nb_epoch = 20
    print('1. Loading data.............')
    te_con_feature,te_emb_feature,te_seq_feature,vocabs_size = load_test_dataset()
    
    n_con = te_con_feature.shape[1]
    n_emb = te_emb_feature.shape[1]
    print('1.1 merge con_feature,emb_feature,seq_feature.....')
    test_feature = prepare_inputX(te_con_feature,te_emb_feature,te_seq_feature)

    print('2. cluster.........')
    cluster_centers = h5py.File('cluster.h5','r')['cluster'][:]

    print('3. Building model..........')
    model = build_lstm(n_con,n_emb,vocabs_size,dis_size,emb_size,cluster_centers.shape[0])
    checkPoint = ModelCheckpoint('weights/' + model_name +'.h5',save_best_only=True)
    earlystopping = EarlyStopping(patience = 500)
    model.compile(loss=hdist,optimizer='rmsprop') #[loss = 'mse',optimizer= Adagrad]
    tr_generator = train_generator(generate_size)
    model.fit_generator(
        tr_generator,
        samples_per_epoch = batches_per_epoch* generate_size,
        nb_epoch = nb_epoch,
        validation_data = getValData(),
        verbose = 1,
        callbacks = [checkPoint,earlystopping]
    )

    print('4. Predicting result .............')
    te_predict = model.predict(test_feature)
    save_results(te_predict,result_csv_path)

if __name__=='__main__':
    start = time()
    main()
    end = time()
    print('Time:\t'+str((end-start)/3600)+' hours')
