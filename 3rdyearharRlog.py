# -*- coding: utf-8 -*-
"""3rdYearHAR.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1PFTmKTMhj1lRhzKGSNkppmx8VNuL1LoO

# Imports, Data Handling
"""

import numpy as np
import pandas as pd
import os
import scipy as sp
from joblib import Parallel, delayed
import random
import statsmodels.api as sm
import sys
import copy
import numpy.matlib
import math
import matplotlib.pyplot as plt


#Load Data, uncomment when you need to load a dataset. This chunk is for the realized volatility dataset
temp=pd.read_csv('oxfordmanrealizedvolatilityindices.csv')
tickers=temp.Symbol.unique()
temp=temp.rename({'Unnamed: 0':'timestamps'},axis='columns')
groups=temp.groupby('Symbol')
data=temp.timestamps.unique()
data=pd.DataFrame(data)
data.columns=['timestamps']
for s in tickers:
  temp=groups.get_group(s)
  temp=temp.drop('Symbol',axis=1)
  colnames=temp.columns
  for name in colnames:
    if name=='timestamps':
      continue
    else:
      temp=temp.rename({name:s+name},axis='columns')
  data=data.merge(temp,how='left',on='timestamps')
data=data.drop(columns=['timestamps'])
data=data.values
data=data.astype('float64')
i=list(range(3,561,18))
data=data[:,i]
data=np.sqrt(data)
data[data==0]=np.nan


#Modeling for HAR
datasets={}
names=['AEX','AORD','BFX','BSESN','BVLG','BVSP','DJI','FCHI','FTMIB','FTSE','GDAXI','GSPTSE','HSI','IBEX','IXIC','KSII','KSE','MXX','N225','NSEI','OMXC20','OMXHPI','OMXSPI','OSEAX','RUT','SMSI','SPX','SSEC','SSMI','STI','STOXX50E']
for i in range(len(names)):
    datasets[names[i]]=data[:,i]

"""# Models"""



#HAR Stuff
def dataExgGen(data,lags):
    dataExg=np.empty(shape=(data.shape[0],len(lags)))
    for j in range(len(lags)):
        temp=np.zeros(shape=(data.shape[0]))
        if j>0:
            for k in range(lags[j]-lags[j-1]):
                temp=temp+np.roll(np.log(np.array(data[:])),(lags[j]-k+1))
            temp=temp/(lags[j]-lags[j-1])
        else:
            for k in range(lags[j]-0):
                temp=temp+np.roll(np.log(np.array(data[:])),(lags[j]-k+1))
            temp=temp/(lags[j]-0)
        temp[0:lags[j]]=np.nan
        dataExg[:,j]=temp
    dataExg = sm.add_constant(dataExg) #dataset created
    return dataExg

def dataEndGen(data,target):
    dataEnd=np.roll(np.log(np.array(data[:])),-1*target)
    dataEnd[-1*target]=np.nan
    return dataEnd

def HARmse(data,target,lags,window,val):
    dataEnd=dataEndGen(data,target)
    dataExg=dataExgGen(data,lags)
    maxLags=lags[-1]
    preds=np.empty(shape=(val,))
    testing=np.empty(shape=(val,))
    for j in range(val):
        try: #Figure out how to do this better?
            model=sm.OLS(dataEnd[j+maxLags:window+j+maxLags], dataExg[j+maxLags:window+j+maxLags,:], missing='drop',hasconst=True)
            modelResults=model.fit()
            preds[j]=modelResults.predict(dataExg[window+j+maxLags,:])[0]
            testing[j]=dataEnd[window+j+maxLags]
        except ValueError:  #raised if `y` is empty.
            preds[j]=np.nan
            testing[j]=dataEnd[window+j+maxLags]
    return AIC(preds,testing,len(lags))

def TreeModelingR(data,depth,MaxLags,loc,window,val,target):
    prev=(MaxLags,)
    bestmse=HARmse(data[loc-MaxLags:window+loc+val+1+target],target,prev,window,val)
    bestlags=prev
    update=prev
    for i in range(depth):
        depthmse=100000 #should be larger than any mse by like 8 orders of magnitude
        valid=list()
        for j in range(1,MaxLags):
       #Somehow recursively build tree? 
            if j in prev:
                continue
            else:
                testlags=(*prev,j,)
                testlags=tuple(sorted(testlags))
                valid.append(testlags)
        mses=Parallel(n_jobs=len(valid),return_as='list')(delayed(HARmse) (data[loc-MaxLags:window+loc+val+1+target],target,valid[j],window,val) for j in range(len(valid)))
        for j in range(len(mses)):
            if mses[j]<bestmse:
                bestmse=mses[j]
                bestlags=valid[j]
            if mses[j]<depthmse:
                depthmse=mses[j]
                update=valid[j]
        prev=update
    return bestlags

#DM test code
def HARgen(data,target,lags,window,val,testsize):
    dataEnd=dataEndGen(data,target)
    dataExg=dataExgGen(data,lags)
    maxLags=lags[-1]
    preds=np.empty(shape=(testsize,))
    testing=np.empty(shape=(testsize,))
    for j in range(1,testsize+1):
        try: #Figure out how to do this better?
            model=sm.OLS(dataEnd[j+val+maxLags:window+j+val+maxLags], dataExg[j+val+maxLags:window+j+val+maxLags,:], missing='drop',hasconst=True)
            modelResults=model.fit()
            preds[j-1]=modelResults.predict(dataExg[window+j+val+maxLags,:])[0]
            testing[j-1]=dataEnd[window+j+val+maxLags]
        except ValueError:  #raised if `y` is empty.
            preds[j-1]=np.nan
            testing[j-1]=dataEnd[window+j+val+maxLags]
    return np.reshape(testing,(testing.shape[0],)),np.reshape(preds,(preds.shape[0],))

def predsgen(data,depth,MaxLags,loc,window,val,testsize,target):
    tracker=0
    pick=TreeModelingR(data,depth,MaxLags,loc,window,val,target)
    if len(pick)==depth:
        tracker=tracker+1
    actual,preds=HARgen(data[loc-MaxLags:window+val+loc+testsize+1+target],target,pick,window,val,testsize)
    return actual,preds,tracker,pick

def loss_gen(actual, p1, p2):
    # Initialise lists
    e1_lst = np.empty(shape=actual.shape)
    e2_lst = np.empty(shape=actual.shape)
    d_lst  = np.empty(shape=actual.shape)
    # construct d according to crit
    e1=np.square(actual - p1)
    e2=np.square(actual - p2)
    d_lst=e1-e2
    return d_lst

def dm_test(d_lst,h):
    # Mean of d
    mean_d = np.nanmean(d_lst)
    T = float(d_lst.size - np.isnan(d_lst).sum())
    # Find autocovariance and construct DM test statistics
    def autocovariance(Xi, N, k, Xs):
        autoCov = 0
        T = 0
        for i in np.arange(0, N-k):
              if np.isnan((Xi[i+k]-Xs)*(Xi[i]-Xs)):
                  continue
              else:
                  autoCov += (Xi[i+k]-Xs)*(Xi[i]-Xs)
                  T=T+1
        return (1/(T))*autoCov
    gamma = []
    for lag in range(0,h):
        gamma.append(autocovariance(d_lst,len(d_lst),lag,mean_d)) # 0, 1, 2
    V_d=0
    if gamma[0]==np.nan:
        V_d = 2*np.nansum(gamma[1:])/T
    else:
        V_d = (gamma[0]+ 2*np.nansum(gamma[1:]))/T
    DM_stat=(np.abs(V_d)**(-0.5))*mean_d
    harvey_adj=((T+1-2*h+h*(h-1)/T)/T)**(0.5)
    DM_stat = harvey_adj*DM_stat
    return  DM_stat


"""# Utility Functions"""

#utility functions

def MSE(x,y):
    return np.sqrt(np.nanmean((x - y)**2))
def AIC(x,y,t):
    n=np.count_nonzero(~np.isnan(x))
    try:
        score=n*np.log(np.nanmean((x-y)**2))+2*t
    except ValueError:
        score=np.inf
    return score

"""# Configs

"""

MaxLags=22
MaxDepth=3 #Capped due to computational limits
window=500
targets=(1,5,22,44,66) #add other horizons?
val=2500
testsize=1#test other ideas
#names=['AEX','AORD','BFX','BSESN','BVLG','BVSP','DJI','FCHI','FTMIB','FTSE','GDAXI','GSPTSE','HSI','IBEX','IXIC','KSII','KSE','MXX','N225','NSEI','OMXC20','OMXHPI','OMXSPI','OSEAX','RUT','SMSI','SPX','SSEC','SSMI','STI','STOXX50E']
curr=sys.argv[1]
data=datasets[curr]
Finals=np.empty(shape=(3*len(targets),))
for i in range(len(targets)):
    actual,preds,tracker,picks=zip(*Parallel(n_jobs=-1, return_as='list')(delayed (predsgen)(data,MaxDepth,MaxLags,j,window,val,testsize,targets[i]) for j in range(MaxLags,datasets[curr].shape[0]-window-val-testsize,testsize)))
    print(sum(tracker))
    actual=np.array(actual)
    preds=np.array(preds)
    _,hars=zip(*Parallel(n_jobs=-1,return_as='list') (delayed (HARgen) (data[j-MaxLags:window+j+val+testsize+1+targets[i]],targets[i],(1,5,22),window,val,testsize) for j in range(MaxLags,datasets[curr].shape[0]-window-val-testsize,testsize)))
    hars=np.array(hars)
    actual=np.reshape(actual,actual.shape[0]*actual.shape[1],)
    preds=np.reshape(preds,preds.shape[0]*preds.shape[1],)
    hars=np.reshape(hars,hars.shape[0]*hars.shape[1],)
    Finals[3*i]=MSE(actual,preds)/MSE(actual,hars)
    losses=loss_gen(actual,hars,preds)
    print(MSE(actual, hars))
    print(len(set(picks)))
    Finals[3*i+1]=dm_test(losses,targets[i])
    Finals[3*i+2]=MSE(actual,preds)
s4="R/"+curr+"logFinals.txt"
Finals=np.reshape(Finals,(1,Finals.shape[0]))
np.savetxt(s4,Finals,fmt="%.4f",delimiter=" & ")
