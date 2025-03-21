# -*- coding: utf-8 -*-
"""3rdYearHAR.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1PFTmKTMhj1lRhzKGSNkppmx8VNuL1LoO

# Imports, Data Handling
"""

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
import datetime

#Load Data and process data
prices=pd.read_csv('/work/users/l/p/lpage2/data.csv')
prices[['date','time']]=prices.timestamp.str.split(' ',expand=True)
prices=prices.drop(columns=['timestamp'])
dates=prices.date.unique()
times=["09:30","09:35","09:40","09:45","09:50","09:55"]
for i in range(10,16):
    for j in range(0,60,5):
        if j<10:
            times.append(str(i)+":0"+str(j))
        else:
            times.append(str(i)+":"+str(j))
times.append("16:00")
#Assuming that missing values are only present on half-days and the start.
returns=np.zeros((len(dates),len(times)+1))
for i in range(returns.shape[0]):
    for j in range(returns.shape[1]-1):
        if i==0 and j==0:
            returns[i,j]=0 #no returns prior to start
        elif prices.iloc[i*len(times)+j,1]!=prices.iloc[i*len(times)+j-1,1]:
            #overnight clause
            if prices.iloc[i*len(times)+j-1,2]!="16:00":
                #need to handle adding rows to prices for missing values
                time=datetime.datetime.strptime(prices.iloc[i*len(times)+j-1,2],"%H:%M")
                skipper=datetime.timedelta(minutes=5)
                time=time+skipper
                line=pd.DataFrame((prices.iloc[i*len(times)+j-1,0],prices.iloc[i*len(times)+j-1,1],time.strftime("%H:%M")))
                returns[i,j]=0
            else:
                returns[i,j]=(np.log(prices.iloc[i*len(times)+j,0])-np.log(prices.iloc[i*len(times)+j-1,0]))**2
        else:
            returns[i,j]=(np.log(prices.iloc[i*len(times)+j,0])-np.log(prices.iloc[i*len(times)+j-1,0]))**2
    returns[i,-1]=sum(returns[i])
times.append("RV")
times=",".join(str(x) for x in times)
np.savetxt("returns.csv",returns,delimiter=",", header=times)
