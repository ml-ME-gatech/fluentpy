#third party imports
import os
from typing import Type
import numpy as np
import shutil
from frozendict import frozendict
import functools
import re
import csv
import sys

#package imports
from ..fluentPyconfig import settings

__all__ = ['']

"""
Creation:
Author(s): Michael Lanahan 
Date: 05.11.2021

Last Edit: 
Editor(s): Michael Lanahan
Date: 05.30.2021

--Descriptin--
General utility functions and classes

"""


def _clear_folder(directory,
                 exception = None,
                 delFolder = True, 
                 leaveRoot = True):

    """
    Description
    ----------
    general clear_folder script. Given directroy as first argument, will delete all files and folders within the directroy
    except for the files and folders placed on the excpetion list if delFolder is set to false, folders will be ignored upon recursive delete
    
    Parameters
    ----------
    directory: string, either relative or absolute that contains the path to the directory of interest
    exception: string or list of strings that contain names of files or folders that should not be
		deleted
    delFolder: boolean variable that indicates if subfolders should be deleted recursively
    leaveRoot: boolean variable to leave the root folder or not
    
    Returns
    ----------
    True if successful, None if not successful
    """

    #make sure the exception list is either a list or None
    if exception is not None:
        if isinstance(exception,list):
            pass
        else:
            exception = [exception]

    #get the  directory to have some slashes at the end so we can add names to it if it does not
    if directory[-1] != '\\' and directory[-1] != '/':
        directory += '\\'

#make sure this directory actually exists, and if it does not, assume that it must be based upon the current
#working directory, and start from there
    if not os.path.exists(directory):
        tdir = os.getcwd()+'\\'+directory

        if not os.path.exists(tdir):
            raise FileNotFoundError("could not find folder {} either from general path or relative".format(directory))
        else:
            directory = tdir

    #check all of the files in the directory
    for fname in os.listdir(directory):
        #deal with the case that the file name represents a directory
        #and ensure that the name is not on the exception list
        if os.path.isdir(directory+fname) and delFolder:
            dFlag = True
            if exception is not None:
                for ex in exception:
                    if fname == ex:
                        dFlag = False

            #recursively deal with this folder
            if dFlag:
                _clear_folder(directory+fname,exception)
                os.rmdir(directory+fname)
            

        #deal with the case that the returned name is a file
        # and ensure that they are not on the exception list 
        else:
            flag = True
            if exception is not None:
                for ex in exception:
                    if fname == ex:
                        flag = False
                        break

            #if we are okayed to delete the file, i.e. the file found is not an exception
            #try and remove the file.
            #if any of the errors seen below are found, continue with the deletion program, but 
            #warn the user that we couldn't delete the file
            #print(flag)
            if flag:
                try:
                    os.remove(directory+fname)
                except(FileNotFoundError,FileExistsError,PermissionError):
                    print('WARNING:: cannot remove: {} from temp directory (located in {})'.format(fname,directory))

    if not leaveRoot:
        os.rmdir(directory)

    return True
            
def _copy_folder(srcFolder: str,
                 dstFolder: str,
                 dstName = None):
    
    """ 
    Description
    ----------
    copys a folder at srcFolder to a destination folder

    Parameters
    ----------
    srcFolder: The source folder to copy, string or path-like
    dstFolder: the destination folder to copy the folder to
    dstName: optional renanming of the copied folder at the desination
    
    Returns
    ----------
    True if succseful, None if not
    """

    if srcFolder[-1] == '\\' or srcFolder[-1] == '/':
        srcFolder = srcFolder[0:-1]

    if dstFolder[-1] == '\\' or dstFolder[-1] == '/':
        dstFolder = dstFolder[0:-1]
    
    assert os.path.exists(srcFolder),'folder does not exist'
    assert os.path.isdir(srcFolder),'this is not a directory'

    _,src_name = os.path.split(srcFolder)
    if dstName is None:
        if src_name not in dstFolder:
            dstFolder = os.path.join(dstFolder,src_name)
    else:
        dstFolder = os.path.join(dstFolder,dstName)

    shutil.copytree(srcFolder,dstFolder)
    
    return True

def _copy_file(srcfile: str,
              dstfolder: str):

    """
    Description
    ----------
    copys a file from a source to a desination folder

    Parameters
    ----------
    srcfile: the string of the source file
    dstfolder: the string of the destination file to copy the file to

    Returns 
    ----------
    returns the destination file
    """

    assert os.path.exists(srcfile),'source file does not exist'
    assert os.path.isfile(srcfile),'source is not a file'

    assert os.path.exists(dstfolder),'destination folder does not exist'
    assert os.path.isdir(dstfolder),'destination is not a folder'
    _,src_name = os.path.split(srcfile)

    dst = os.path.join(dstfolder,src_name)

    if os.path.exists(dst):
        i = 0
        srcname,ext = os.path.splitext(src_name)
        while True:
            dst = srcname + '-' + str(i) + ext
            dst = os.path.join(dstfolder,dst)
            i += 1
            if not os.path.exists(dst):
                break
    
    shutil.copy2(srcfile,dst)

    return dst

def _cache_file(fname:str):

    """
    Description
    ----------
    cache a file in a specified cache folder, i.e. copy a file to a cache folder
    and specify on a manifest where that file came from

    Parameters
    fname: the string of the file to copy

    Returns
    None
    """
    cache_settings = settings.from_env('cache')
    cwd,_ = os.path.split(__file__)
    cache_path = os.path.join(cwd,cache_settings['tempfolder'])
    
    dst = _copy_file(fname,cache_path)
    
    _,record = os.path.split(dst)

    with open(os.path.join(cache_path,cache_settings['manifestfile']),'a+') as file:
        file.write(record + " \t " + fname + "\n")
    
def _restore_files():

    """
    Description
    ----------
    restore all files in the cache to their original location and content subject to the limitations of copy2

    Parameters
    ----------
    None

    Returns 
    ----------
    None
    """

    cache_settings = settings.from_env('cache')
    cwd,_ = os.path.split(__file__)
    cache_path = os.path.join(cwd,'__iotemp__')

    with open(os.path.join(cache_path,cache_settings['manifestfile']),'r') as file:
        csvreader = csv.reader(file,delimiter = '\t')

        for row in csvreader:
            temp = os.path.join(cache_path,row[0].strip())
            restore_dst = row[1].strip()
            shutil.copy2(temp,restore_dst)

