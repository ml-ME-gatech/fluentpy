#third party imports
import os

#package imports
from .classes import ReportFileOut,ReportFilesOut
from .._msg import get_report_message
from ._util import _clear_folder,_cache_file
from ..fluentPyconfig import settings

"""
This file "post.py" contains the highest level interface for interacting with data produced 
by ANSYS workbench fluent. Essentially, using the lower level functions from _util and _file_scan and the
classes from classes.py may produce longer files to do one task that may be succicnelty pacakged into a 
single function. So if I find myself writing the same lines of code over and over again,
it is often easier to turn it into a function with a clear, high level purpose.
"""

#modify headers in the results file to the name replacements
#that are mapped to one another in nameMap

#do this for all of the files contained within "files" using the "fileModification"
#interface where the action is recorded and cached into a temporary directory lest
#there be some reason to restore the files
def modify_header_names(nameMap,files,env = 'default'):

    if not isinstance(nameMap,dict):
        raise TypeError("The map of names must be a dictionary")
    
    def action(fname):

        recordAction = 'attempted to replace the following names\n'
        with open(fname,'r') as file:
            text = file.read()
        
        for name,new in nameMap.items():
            text = text.replace(str(name),str(new))
            recordAction += str(name) + ' : ' + str(new) + '\n'
        
        with open(fname,'w') as file:
            file.write(text)
        
        return recordAction

    fileModification(files,action,'modifyHeaderNames',env = env)

#generic interface for modification of the files.
#a supplied action must be callable, and must return a string summarizing the
#the action performanced on the only argument allowed to an action which is the
#file name upon which to act upon
def fileModification(fnames : list,         #list of file names to apply file modifications too
                     action: callable,      #callable action to perform on files
                     func_name: str,        #name of the function applying the action
                     env = 'default'        #environment name
                     ):    

    envsettings = settings.from_env(env)
    temp_name = settings.from_env('cache')['tempfolder']
    #clear the cache where we will store file modifiction
    path,_ = os.path.split(__file__)
    _clear_folder(os.path.join(path,temp_name))

    #do the action on the list of files provided
    #and record it into a report
    filetxt = ''
    for fname in fnames:
        filetxt += fname + '\n'

        if envsettings.safe:
            _cache_file(fname)
        
        filetxt += action(fname) +'\n'

    #compile the report message
    msg = get_report_message('restore_file_modification')
    restore_func_name = 'restore_files'
    msg = msg.format(func_name,filetxt,temp_name,restore_func_name)
    
    #print the report
    if envsettings.print:
        print(msg)