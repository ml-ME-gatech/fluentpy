#native imports
from abc import ABC,abstractmethod,abstractstaticmethod
import os
from typing import Type
from dynaconf.utils import files
from more_itertools import flatten as mi_flatten

#package imports
from ..io.classes import ReportFileOut, SolutionFile,SolutionFiles
from ..fluentPyconfig import settings as configsettings
from ..io.filesystem import DesignPointFolder, FluentFolder
from .linker_utils import zero_percent_diff_link_verification
from ..link.base import DataLink,DataModule
from .._msg import get_error_message

fluent_settings = configsettings.from_env('fluent-default')

__all__ = [
            'DataModule',
            'ExcelFileModule',
            'ReportFileModule',
            'DefaultFluentFolderModule',
            'DesignPointModule',
            'DefaultFluentFolderLink',
            'DataBaseLink'
]

"""
Creation:
Author(s): Michael Lanahan 
Date: 05.31.2021

Last Edit: 
Editor(s): Michael Lanahan
Date: 06.11.2021

-- Description -- 
The classes that define a data module, and a data link. These classes are inherited to more specific implementations 
for the fluent folder at hand. Everything depends upon the SerializableDataContainer which provides the methods
for writing a class to a binary file
"""

class ExcelFileModule(DataModule):

    def __init__(self,
                 fname,
                 file_parser,
                 env = 'fluent-default'):

        wf,id = os.path.split(fname)
        _,ext = os.path.splitext(fname)
        if ext != '.xlsx':
            raise TypeError('file is not an excel file')
        
        super().__init__([fname],file_parser,id)
        self.write_folder = wf

    @staticmethod
    def _from_file_parser(dmdict):
        return dmdict['files'][0],dmdict['file_parser']

class ReportFileModule(DataModule):

    def __init__(self,
                 fname,
                 id,
                 env = 'fluent-default'):
        
        if isinstance(fname,list):
            if len(fname) != 1:
                raise ValueError('ReportFileModule may only be initialized with a single file name')
            else:
                fname = fname[0]
        elif isinstance(fname,str):
            pass
        else:
            raise ValueError('fname must be a string')
        
        _,ext = os.path.splitext(fname)
        wf,_ = os.path.split(fname)
        required_ext = fluent_settings['report_file_ext']

        if required_ext != ext:
            msg = 'File is not a report file. The required extension is: {}'.format(required_ext)
            raise TypeError(msg)
        
        super().__init__([fname],report_file_parser,id)
        self.__write_folder = wf

    @staticmethod
    def _from_file_parser(dmdict):
        fnames = dmdict['dirs'] + dmdict['files']
        return fnames,dmdict['identifier'],dmdict['file_parser']

class DefaultFluentFolderModule(DataModule):

    def __init__(self,
                 folder,
                 env = 'fluent-default'):

        filesys = FluentFolder(folder)
        try:
            super().__init__([filesys.ff_root,
                            filesys.get_solution_files()[0],
                            filesys.get_report_files()[0]],
                            fluent_folder_parser,filesys.__name__)
        except TypeError:
            msg = get_error_message('fluent_default_module_instantiation_error')
            raise FileNotFoundError(msg.format(filesys.ff_root))

        
        self.write_folder = filesys.ff_root

    @staticmethod
    def _from_file_parser(dmdict):
        fname = dmdict['dirs']
        return fname

class DesignPointModule(DataModule):

    def __init__(self,
                 folder,
                 checkfolder = False,
                 *args,
                 env = 'fluent-default',
                 **kwargs):

        
        filesys = DesignPointFolder(folder)
        super().__init__([],design_point_parser,filesys.__name__)
        self.files = {'report_files':[],'solution_files':[]}
        dirs = filesys.get_fluent_folders()
        self.dirs = [ff.ff_root for ff in dirs]
        for fluent_folder in dirs:
            rfile = fluent_folder.get_report_files()
            sfile = fluent_folder.get_solution_files()
            condition1 = rfile[0] is not None and sfile[0] is not None
            condition2 = len(rfile) == 1 and len(sfile) == 1 
            if condition1 and condition2:
                self.files['report_files'].append(rfile[0])
                self.files['solution_files'].append(sfile[0])
        
        self.write_folder = filesys.dp_root
        self.dirs.insert(0,filesys.dp_root)
    
    @staticmethod
    def _from_file_parser(dmdict):
        return dmdict['dirs'][0],
    
    def __getitem__(self,key):
        return DefaultFluentFolderModule(key)

class DefaultFluentFolderLink(DataLink):

    def __init__(self,
                 DataModule1,
                 DataModule2,
                 *args,
                  **kwargs):

        if not isinstance(DataModule1,DefaultFluentFolderModule):
            raise TypeError('First Data Module must be of DefaultFluentFolderModule Type')
        
        super().__init__(DataModule1,
                         DataModule2,
                         zero_percent_diff_link_verification,
                         *args,
                         **kwargs)

        self.write_folder = DataModule1.write_folder

class DataBaseLink(ABC):

    def __init__(self,srcDataModule,
                      trgtDataModule,
                      linker,
                      link = DataLink,
                      *args,**kwargs):

        self.__link = link
        self.__srcDataModule = srcDataModule
        self.__trgtDataModule = trgtDataModule
        self.__linker = linker
        self.__link_list = []

    @property
    def srcDataModule(self):
        return self.__srcDataModule
    
    @property
    def trgtDataModule(self):
        return self.__trgtDataModule
    
    @property
    def linker(self):
        return self.__linker

    @property
    def link(self):
        return self.__link
    
    @property
    def link_list(self):
        return self.__link_list
    
    @link.setter
    def link(self,lnk):
        self.__link = lnk
    
    @link_list.setter
    def link_list(self,ll):
        self.__link_list = ll
    
    @abstractstaticmethod
    def form_link(self,sdm,tdm):
        self.link_list.append(self.link(sdm,tdm))

    def establish_links(self):
        link_dict = self.linker(self.srcDataModule(),self.trgtDataModule())
        for src_id,trgt_id in link_dict.items():
            self.form_link(self.srcDataModule[src_id],self.trgtDataModule[trgt_id])
             
    @abstractmethod
    def log_links(self):
        for link in self.link_list:
            link.serialize()
        
class DesignPointLink(DataBaseLink):

    def __init__(self,
                 dp_folder,
                 trgtDataModule,
                 linker,
                 checkfolder = False,
                 *args,**kwargs):
        
        srcDataModule = DesignPointModule(dp_folder)
        super().__init__(srcDataModule,trgtDataModule,linker)

def report_file_parser(file_names,dir_names):


    with ReportFileOut(file_names[0]) as rfile:
        data = rfile.readdf(skiprows= 'converged')
    
    return data

def design_point_parser(file_names,dirs_names):

    try:
        solution_files = file_names['solution_files']
    except AttributeError:
        _file_names = mi_flatten(file_names)
        solution_files = [fname for fname in _file_names if fluent_settings['solution_file_ext'] in fname]

    sfiles = SolutionFiles(solution_files)
    return sfiles.params_as_frame()

def fluent_folder_parser(file_names,dir_names):

    for f in file_names:
        if fluent_settings['solution_file_ext'] in f:
            sol_file = f
    
    with SolutionFile(sol_file) as sfile:
        data = sfile.read_params()
    
    return data