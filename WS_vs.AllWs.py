#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 17 09:13:55 2018

@author: feebr01
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#bring in splunk query csv (see query in notes below)
all_ws = pd.read_csv('CiscoTest.csv')


#df of just the workspace in question
ws = all_ws.query('workspaceOid == 251635506')


#df of all other workspaces
other_ws = all_ws.query('workspaceOid != 251635506')


#pivot the other workspaces on page index and average their apdex
other_pivot = pd.pivot_table(other_ws, index = 'cleanedPageHash', 
                           values ='apdex_avg', aggfunc = 'mean')
other_pivot.reset_index(inplace=True)


#merge averages to ws dataframe based on pagehash name
output = pd.merge(ws, other_pivot, how = 'inner', on='cleanedPageHash')


#clean up column naming in combined dataframe
output.rename(columns = {'apdex_avg_x': 'apdex_avg_ws', 
                         'apdex_avg_y': 'apdex_avg_other'}, inplace=True)


# create delta column between the workspace and all other (+ is good)
output['apdex_avg_delta'] = output['apdex_avg_ws'] - output['apdex_avg_other']


#sort output dataframe for charting
output.sort_values('apdex_avg_delta', ascending = 0, inplace=True)



################## Simple Apdex Delta Chart
ax = output.plot('cleanedPageHash', 'apdex_avg_delta', kind='bar', figsize=(10,5), color = 'b')
ax.set_xlabel('Page')
ax.set_ylabel('Apdex Delta (WS-Avg)')



################## Apdex Delta vs. Page Loads Chart
#set default style
print(plt.style.available)
plt.style.use('default')


#format ticker library
from matplotlib.ticker import FuncFormatter as fmt

#define base chart 
fig, (ax1,ax2)  = plt.subplots(2, 1, figsize=(7, 5), sharex=True)

#define figure 1 
fig1 = output.plot('cleanedPageHash', 'apdex_avg_delta', kind='bar', ax=ax1, color = 'g')
ax1.set_yticks(np.linspace(-.25, .25, 5))
ax1.set_ylabel('Apdex Delta (WS-Avg)')
ax1.legend( loc = 'upper left')

#define figure 2
fig2 = output.plot('cleanedPageHash', 'loads', kind='bar', ax=ax2, color='b')

#comma format y axis on figure 2 
ax2.get_yaxis().set_major_formatter(fmt(lambda x, p: format(int(x), ',')))
ax2.set_ylabel('Page Loads')
ax2.set_xlabel('Page')

'''

SPLUNK QUERY -7D Time Limit - Export result for csv read in

sourcetype="dapper-spans" subId=2001 requestSpan.stack= prod
componentType="pageNavigationMetrics"
NOT traceSummary.CRT=null
| rex mode=sed field=cleanedPageHash "s/detail.*/detail/g"
| rex mode=sed field=cleanedPageHash "s/workviews.*/workviews/g"
| rex mode=sed field=cleanedPageHash "s/_[0-9]{1}$//g"
| rex mode=sed field=cleanedPageHash "s/:[a-z0-9A-Z_]*$//g"
| rex mode=sed field=cleanedPageHash "s/\/$//g"
| rex mode=sed field=cleanedPageHash "s/\/.*error.*/\/error/g"
| eval pageType=case(
    cleanedPageHash="/backlog","deprecated",
    cleanedPageHash="/defects","deprecated",
    cleanedPageHash="/detail","deprecated",
    cleanedPageHash="/releasemetrics","deprecated",
    cleanedPageHash="/releasestatus","deprecated",
    cleanedPageHash="/tasks","deprecated",
    cleanedPageHash="/teamstatus","deprecated",
    cleanedPageHash="/testcases","deprecated",
    cleanedPageHash="/testfolders","deprecated",
    cleanedPageHash="/userstories","deprecated",
    
    cleanedPageHash="/capacityplanning","core",
    cleanedPageHash="/custom","core",
    cleanedPageHash="/dashboard","core",
    cleanedPageHash="/iterationstatus","core",
    cleanedPageHash="/portfolioitemstreegrid","core",
    cleanedPageHash="/releasetracking","core",
    cleanedPageHash="/search","core",
    cleanedPageHash="/teamplan","core",
    cleanedPageHash="/timeboxes","core",
    
    cleanedPageHash="/planprogression","new",
    cleanedPageHash="/teamboard","new",    
    cleanedPageHash="/workviews","new",
    
    cleanedPageHash="/error","error",
    
    true(),"other"
)
| rename requestSpan.traceId AS trace 
| join userId type="inner" [inputlookup cisco_user_to_workspace.csv]
| rename traceSummary.errors as errors
| rename traceSummary.CRT as csrt 
| rename requestSpan.stack as stack
| eval apdex = case(errors>0,0.0,csrt<2000,1.0,csrt<8000,0.5,true(),0.0)
| stats c(trace) as loads avg(apdex) as apdex_avg  by workspaceOid cleanedPageHash pageType
| where loads > 5
| sort -apdex_avg

'''