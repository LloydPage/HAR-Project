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
def HARmse(data,size,lags,target):
    window=size
    test=data.shape[0]-size
    if len(data.shape)<=1:
        data=np.reshape(data, (data.shape[0],1))
    preds=np.empty(shape=(test-target,data.shape[1]))
    testing=np.empty(shape=(test-target,data.shape[1]))
    for i in range(data.shape[1]):
        dataEnd=np.roll(np.log(np.array(data[:,i])),-1*target)
        dataEnd[-1*target]=np.nan
        dataExg=np.empty(shape=(data.shape[0],len(lags)))
        for j in range(len(lags)):
            temp=np.zeros(shape=(data.shape[0]))
            if j>0:
                for k in range(lags[j]-lags[j-1]):
                      temp=temp+np.roll(np.log(np.array(data[:,i])),(lags[j]-k+1))
                temp=temp/(lags[j]-lags[j-1])
            else:
                for k in range(lags[j]-0):
                      temp=temp+np.roll(np.log(np.array(data[:,i])),(lags[j]-k+1))
                temp=temp/(lags[j]-0)
            temp[0:lags[j]]=np.nan
            dataExg[:,j]=temp
        dataExg = sm.add_constant(dataExg) #dataset created
        for j in range(test-target):
            try: #Figure out how to do this better?
                model=sm.OLS(dataEnd[j:window+j], dataExg[j:window+j,:], missing='drop',hasconst=True)
                modelResults=model.fit()
                preds[j,i]=modelResults.predict(dataExg[window+j,:])[0]
                testing[j,i]=dataEnd[window+j]
            except ValueError:  #raised if `y` is empty.
                preds[j,i]=np.nan
                testing[j,i]=dataEnd[window+j]
    return MSE(preds,testing)

def TreeModelingF(data,window,maxLags,target,depth):
    valid=list()
    lags=np.empty(depth+1,dtype=int)
    for k in range(depth):
        lags[k]=k+1 #initialized, cannot start at 0
    lags[-1]=maxLags
    valid.append(copy.deepcopy(lags))
    while depth>0:
        counter=0
        for k in range(depth):
            if lags[k]==maxLags-(depth-k):
                counter=counter+1
        if counter==depth:
            break
        lags[-1*(counter)-2]=lags[-1*(counter)-2]+1
        for k in range(counter,0,-1):
              lags[-1*k-1]=lags[-1*(k+1)-1]+1
        valid.append(copy.deepcopy(lags))
    results=Parallel(n_jobs=-1,return_as='list')(delayed(HARmse) (data,window,valid[i],target) for i in range(len(valid)))
    minindex=0
    bestmse=results[minindex]
    bestlags=valid[minindex]
    for i in range(len(results)):
        if results[i]<results[minindex]:
            minindex=i
            bestmse=results[minindex]
            bestlags=valid[minindex]
    return bestmse, list(bestlags)
#DM test code
def HARgen(data,size,lags,target):
    window=size
    test=data.shape[0]-size
    if len(data.shape)<=1:
        data=np.reshape(data, (data.shape[0],1))
    preds=np.empty(shape=(test-target,data.shape[1]))
    testing=np.empty(shape=(test-target,data.shape[1]))
    for i in range(data.shape[1]):
        dataEnd=np.roll(np.log(np.array(data[:,i])),-1*target)
        dataEnd[-1*target]=np.nan
        dataExg=np.empty(shape=(data.shape[0],len(lags)))
        for j in range(len(lags)):
            temp=np.zeros(shape=(data.shape[0]))
            if j>0:
                for k in range(lags[j]-lags[j-1]):
                      temp=temp+np.roll(np.log(np.array(data[:,i])),(lags[j]-k+1))
                temp=temp/(lags[j]-lags[j-1])
            else:
                for k in range(lags[j]-0):
                      temp=temp+np.roll(np.log(np.array(data[:,i])),(lags[j]-k+1))
                temp=temp/(lags[j]-0)
            temp[0:lags[j]]=np.nan
            dataExg[:,j]=temp
        dataExg = sm.add_constant(dataExg) #dataset created
        for j in range(test-target):
            try: #Figure out how to do this better?
                model=sm.OLS(dataEnd[j:window+j], dataExg[j:window+j,:], missing='drop',hasconst=True)
                modelResults=model.fit()
                preds[j,i]=modelResults.predict(dataExg[window+j,:])[0]
                testing[j,i]=dataEnd[window+j]
            except ValueError:  #raised if `y` is empty.
                preds[j,i]=np.nan
                testing[j,i]=dataEnd[window+j]
    return np.reshape(testing,(testing.shape[0],)),np.reshape(preds,(preds.shape[0],))
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

def dm_test(d_lst,h=1):
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

#Multi-horizon DM
def psuedolossgen(losses, L):
    T=losses.shape[0]
    id = np.zeros(shape=(T,),dtype=int)
    id[0] = int(np.floor(T/L*np.random.rand(1,1)).item())*L
    for t in range(1,T):
        if t%L == 0:
          id[t] = int(np.floor(T/L*np.random.rand(1,1)).item())*L
        else:
          id[t] = id[t-1]+1
        if id[t]>=T:
          id[t] = 0
    return losses[id,:]

def Parallelize(losses,targets,L):
    psuedoloss=psuedolossgen(losses,L)
    H=len(targets)
    dm=0
    for j in range(len(targets)):
        dm=dm+dm_test(psuedoloss[:,j],targets[j])
    t_aSPA_bb= dm/H
    return t_aSPA_bb

def bootstrap_aSPA(losses,targets, L):
    B=100000
    T=actual.shape[0]
    H=len(targets)
    dm=0
    for j in range(len(targets)):
        dm=dm+dm_test(losses[:,j],targets[j])
    t_aSPA = dm/H
    t_aSPA_b = np.zeros(shape=(B,1))
    t_aSPA_b=Parallel(n_jobs=-1,return_as='list')(delayed(Parallelize) (losses,targets,L) for b in range(B)) #Should work
    t_aSPA_b=np.array(t_aSPA_b)
    t_aSPA_b=np.reshape(t_aSPA_b,(t_aSPA_b.shape[0],))
    return t_aSPA, t_aSPA_b

def Test_aSPA(losses,targets,L):
    t_aSPA, t_aSPA_b = bootstrap_aSPA(losses,targets, L)
    p_value = np.mean(t_aSPA < t_aSPA_b)
    return t_aSPA.item(), p_value

#utility functions

def MSE(x,y):
    return np.sqrt(np.nanmean((x - y)**2))

"""# Configs

"""

MaxLags=22
MaxDepth=6 #Manually grab further depths if needed
window=500
targets=(1,5,22,44,66)
#names=['AEX','AORD','BFX','BSESN','BVLG','BVSP','DJI','FCHI','FTMIB','FTSE','GDAXI','GSPTSE','HSI','IBEX','IXIC','KSII','KSE','MXX','N225','NSEI','OMXC20','OMXHPI','OMXSPI','OSEAX','RUT','SMSI','SPX','SSEC','SSMI','STI','STOXX50E']
curr=sys.argv[1]
results=np.empty(shape=(len(targets),MaxDepth+3))
lagpicks=np.empty(shape=(len(targets),MaxDepth+1),dtype=object)
losses=np.empty(shape=(datasets[curr].shape[0]-window,len(targets)))
Finals=np.empty(shape=(2*len(targets)+2,))
for j in range(len(targets)):
    for k in range(MaxDepth+1):
          results[j,k],prev=TreeModelingF(datasets[curr],window,MaxLags,targets[j],k)
          lagpicks[j,k]=prev
    results[j,MaxDepth+1]=HARmse(datasets[curr],window,(1,5,22),targets[j])
    minindex=0
    for k in range(MaxDepth+1):
          if results[j,k]<results[j,minindex]:
                minindex=k
    actual,p1=HARgen(datasets[curr],window,lagpicks[j,minindex],targets[j])
    actual,p2=HARgen(datasets[curr],window,(1,5,22),targets[j])
    losses[0:datasets[curr].shape[0]-window-targets[j],j]=loss_gen(actual,p2,p1)
    losses[datasets[curr].shape[0]-window-targets[j]:,j]=np.nan
    results[j,MaxDepth+2]=dm_test(losses[:,j],targets[j]).item()
    HAR=HARmse(datasets[curr],window,(1,5,22),targets[j])
    Finals[2*j]=results[j,minindex]/HAR
    Finals[2*j+1]=results[j,-1]
Finals[-2],Finals[-1]=Test_aSPA(losses,targets,22)
s1="F/"+curr+"lagpicks.txt"
s2="F/"+curr+"results.txt"
s3="F/"+curr+"format.txt"
s4="F/"+curr+"Finals.txt"
Finals=np.reshape(Finals,(1,Finals.shape[0]))
np.savetxt(s1,lagpicks,fmt='%s')
np.savetxt(s2,results)
np.savetxt(s3,results,fmt="%.4f",delimiter=" & " )
np.savetxt(s4,Finals,fmt="%.4f",delimiter=" & " )
