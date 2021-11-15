#native & common package imports
from typing import final
import pandas as pd
from scipy.spatial.distance import cdist
import numpy as np

#package imports
from .link_exceptions import DataLinkException

__all__ =  [
        'zero_diff_link_verification',
        'zero_norm_linker_dict'
]

"""
Creation:
Author(s): Michael Lanahan 
Date: 05.31.2021

Last Edit: 
Editor(s): Michael Lanahan
Date: 06.08.2021

-- Description -- 
utilities for the linker classes and for working with the linker classes in classes.py

"""

def zero_diff_link_verification(df1,
                                df2,
                                columns = 'intersection',
                                ignore_columns = [],
                                decimals = False):


    df1 = df1.astype(float)
    df2 = df2.astype(float)
    if columns == 'intersection':
        _df1,_df2 = _df_intersection_parser(df1,df2,ignore_columns)
    if columns == 'union':
        _df1,_df2 = _df_union_parser(df1,df2,ignore_columns)
    
    if decimals is not False:
        _df1 = _df1.round(decimals = decimals)
        _df2 = _df2.round(decimals = decimals)
    diff = np.sum(_df1 - _df2 )
    
    if diff == 0:
        return True
    else:
        return False

def zero_percent_diff_link_verification(df1,
                                        df2,
                                        columns = 'intersection',
                                        ignore_columns = [],
                                        precision = 3):

    df1 = df1.astype(float)
    df2 = df2.astype(float)
    if columns == 'intersection':
        _df1,_df2 = _df_intersection_parser(df1,df2,ignore_columns)
    if columns == 'union':
        _df1,_df2 = _df_union_parser(df1,df2,ignore_columns)

    sum_percent_diff = _zero_percent_diff(_df1,_df2,precision = precision)

    if sum_percent_diff == 0:
        return True
    else:
        return False

def _zero_percent_diff(array_like1,array_like2,precision = 3):
    
    ignore = 10**(-precision)
    diff = array_like1 - array_like2
    try:
        absdiff = diff.abs()
    except AttributeError:
        absdiff = np.abs(diff)
    
    percent_diff = absdiff/array_like1
    percent_diff[percent_diff< ignore] = 0.0

    sum_percent_diff = np.sum(np.abs(percent_diff))
    return sum_percent_diff


def zero_percent_diff_linker_dict(df1,df2,columns = 'intersection',ignore_columns = [],*dist_args,**dist_kwargs):

    columns = columns.lower()
    for df in [df1,df2]:
        if not isinstance(df,pd.DataFrame):
            raise TypeError('arguments must be pandas DataFrames')

    df1 = df1.astype(float)
    df2 = df2.astype(float)
    
    if columns == 'intersection':
        _df1,_df2 = _df_intersection_parser(df1,df2,ignore_columns)
    if columns == 'union':
        _df1,_df2 = _df_union_parser(df1,df2,ignore_columns)

    _df1,_df2 = _df1.align(_df2,axis = 1,join = 'outer')


    def dist_wrapped(*args,**kwargs):

        def dist(df1_,df2_):

            return _zero_percent_diff(df1_,df2_,*args,**kwargs)
        
        return dist
    
    dist_func = dist_wrapped(*dist_args,**dist_kwargs)
    x = cdist(_df1,_df2,metric = dist_func)
    idx1,idx2 = np.where(x == 0)

    return dict(zip(idx1,idx2))

def zero_norm_linker_dict(df1,df2,columns = 'intersection',ignore_columns = [],*dist_args,**dist_kwargs):
    
    columns = columns.lower()
    for df in [df1,df2]:
        if not isinstance(df,pd.DataFrame):
            raise TypeError('arguments must be pandas DataFrames')
    
    if columns == 'intersection':
        _df1,_df2 = _df_intersection_parser(df1,df2,ignore_columns)
    if columns == 'union':
        _df1,_df2 = _df_union_parser(df1,df2,ignore_columns)
    
    x = cdist(_df1,_df2,*dist_args,**dist_kwargs)
    idx1,idx2 = np.where(x == 0)
    
    return dict(zip(idx1,idx2))

def _df_intersection_parser(df1,df2,ignore_columns):

   return _df_col_parser(df1,df2,_col_intersection,ignore_columns)

def _df_union_parser(df1,df2,ignore_columns):

    return _df_col_parser(df1,df2,_col_union,ignore_columns)

def _df_col_parser(df1,df2,columns_set,ignore_columns):

    def _as_frame(df):
        if isinstance(df,pd.DataFrame) or isinstance(df,np.ndarray):
            df_ = df
        elif isinstance(df,pd.Series):
            _array = np.expand_dims(np.array(df),1).T
            df_ = pd.DataFrame(_array,index = [0],columns = list(df.index))
        else:
            raise TypeError('must be a pandas Frame or Series')

        return df_
    
    df1_ = _as_frame(df1)
    df2_ = _as_frame(df2)

    try:
        df1_ = df1_.drop(ignore_columns)
    except KeyError:
        df1_ = df1_.drop(ignore_columns,axis = 1)

    try:
        df2_ = df2_.drop(ignore_columns)
    except KeyError:
        df2_ = df2_.drop(ignore_columns,axis = 1)
     
    columns = columns_set(df1_,df2_)
    return df1[columns],df2[columns]
    
def _col_intersection(columns1,columns2):

    return list(filter(lambda x:x in columns1, columns2))

def _col_union(columns1,columns2):

    return list(set(columns1+columns2))