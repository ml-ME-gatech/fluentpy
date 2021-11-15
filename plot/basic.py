from matplotlib import pyplot as plt
import json
import numpy as np
from matplotlib import rc
import os

#read in format data
path,_ = os.path.split(__file__)
fmtfile = os.path.join(path,'basic_fmt.json')
with open(fmtfile,'r') as file:
    fmtData = json.load(file)

rc('font',**{'family':'serif','serif':[fmtData['FONT_NAME']]})
#rc('text', usetex=True)

def basic_line_plot(ax,X,Y,xlabel,ylabel,names = None,xscale = 'linear',yscale = 'linear',xlim = None,ylim = None):

    if X.ndim != Y.ndim:
        if X.ndim == 1:
            Xt = np.zeros(Y.shape)
            for i in range(Y.shape[1]):
                Xt[:,i] = X.copy()
            
            X = Xt

        else:
            raise ValueError('X and Y must be the same dimension')
    
    if X.ndim == 1:
        X = np.expand_dims(X,axis = 0).T
    
    if Y.ndim == 1:
        Y = np.expand_dims(Y,axis = 0).T

    for i,color,lstyle in zip(range(X.shape[1]),fmtData['PLOT_COLORS'],fmtData['PLOT_STYLES']):
        if names is not None:
            ax.plot(X[:,i],Y[:,i],label = names[i],color =color,linestyle = lstyle,linewidth = fmtData['LINE_WIDTH'])
        else:
            ax.plot(X[:,i],Y[:,i],color =color,linestyle = lstyle,linewidth = fmtData['LINE_WIDTH'])
        
    ax.set_xlabel(xlabel,fontsize = fmtData['AXIS_FONT_SIZE'])
    ax.set_ylabel(ylabel,fontsize = fmtData['AXIS_FONT_SIZE'])

    if names:
        ax.legend(fontsize = fmtData['LEGEND_FONT_SIZE'])

    ax.set_xscale(xscale)
    ax.set_yscale(yscale)

    ax.tick_params(axis = 'both',labelsize = fmtData['TICK_LABEL_SIZE'])

    if xlim:
        ax.set_xlim(xlim)
    
    if ylim:
        ax.set_ylim(ylim)
