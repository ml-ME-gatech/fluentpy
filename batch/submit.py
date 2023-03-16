#native imports
from typing import Any, Iterable, Tuple, List, Union
import os
from pandas.core.frame import DataFrame
import numpy as np
import shutil
from pathlib import Path, PosixPath,WindowsPath
from collections.abc import MutableMapping
import pandas as pd
import json
from abc import ABC, abstractmethod, abstractstaticmethod
import sys
import warnings

#package imports
from ..disk import SerializableClass
from ..pace import PaceScript
from .pbs import PBS
from .fluent import FluentPBS
from ..tui import BatchCaseReader, FluentJournal
from .table_parse import partition_boundary_table
from .filesystem import TableFileSystem
from .batch_util import _parse_pykwargs

""" 
Author: Michael Lanahan
Date created: 08.04.2021
Last Edit: 01.03.2022

functions and classes for submitting fluent pace jobs to pace
"""
    
class FluentSubmission(SerializableClass,ABC):
    """
    Class for representing the unit "submission" of a fluent job to pace
    This MUST be instantiated with a FluentJournal as a first argument

    Parameters
    ----------
    fluent_journal : FluentJournal
            an instance of a FluentJournal
    args* : args
            any additional arguments. If additional arguments are specified in the
            write_file_attributes property, they must have a "write" method
    """

    FLUENT_INPUT = 'fluent.input'

    def __init__(self,fluent_journal: FluentJournal,
                      *args,**kwargs):
        
        self.__fluent_journal = fluent_journal
        self.__write_file_attributes = None
    
    @property
    def fluent_journal(self):
        return self.__fluent_journal
    
    @property
    def write_file_attributes(self) -> dict:
        """
        this property must be specified in order to write
        all of the required files to a folder in a batch submission
        folder 

        Property must be specified as a dicitonary: 

        {property_name : file_string}
        """
        if self.__write_file_attributes is None:
            raise NotImplementedError('write_file_attributes cannot be None')
        
        _write_attr = self.__write_file_attributes.copy()

        #determine if there are any udf source files required for compilation
        try:
            for bc in self.fluent_journal.boundary_conditions:
                for udf in bc.udf.values():
                    if udf.file_name is not None:
                        _write_attr[udf.file_name] = True

        except AttributeError:
            pass
    
        return _write_attr

    @write_file_attributes.setter
    def write_file_attributes(self,wfa : dict) -> None:
        self.__write_file_attributes = wfa
     
    @abstractmethod
    def execute_command(self, f: str) -> str:
        """
        abstract method that must take in argument of a folder and returns
        a list of strings (or objects with a string method) that can
        be piped to .subprocess.call()
        """
        pass

    @abstractmethod 
    def pre_write(self,*args,**kwargs) -> Any:

        pass

    def write(self,folder : str) -> None:

        """ 
        writes the fluent journal to a folder along with any additional
        required files.

        if the value of the requested key in the write file attribute is True,
        assume that this is a file that we want to copy to the directory
        """
        
        if not os.path.isdir(folder):
            os.mkdir(folder)
        
        self.pre_write(folder)
        for attr, file_name in self.write_file_attributes.items():
            if isinstance(file_name,bool) and file_name:
                _,fname = os.path.split(attr)
                dst_file = os.path.join(folder,fname)
                shutil.copyfile(attr,dst_file)
            else:
                try:
                    self.__getattribute__(attr).write(os.path.join(folder,file_name))
                except TypeError:
                    self.__getattribute__(attr).write(folder)

    def format_submit(self,f: str) -> list:
        """
        format the submission at the command line in pace
        """
        
        self.write(f)
        return self.execute_command(f)

class PaceFluentSubmission(FluentSubmission):
    """
    The unit submission object for the computing cluster PACE @ GT
    combines the FluentJournal and FluentPBS objects into a single
    folder.
    """

    path,_ = os.path.split(os.path.split(__file__)[0])
    PACE_PBS = 'fluent.pbs'
    script_path = os.path.join(path,'dat','scripts')
    DEFAULT_SCRIPT = 'single_deploy.py'

    def __init__(self,fluent_journal: FluentJournal,
                      fluent_pbs: FluentPBS,
                      python_script = PaceScript,
                      script_name = None,
                      python_libs = [],
                      python_envs = [],
                      python_version = '2021.05',
                      submit_command = 'sbatch',
                      **kwargs) -> None:

        if script_name is None:
            script_name = self.DEFAULT_SCRIPT
        
        super().__init__(fluent_journal)
        self.fluent_pbs = fluent_pbs
        
        script_name = os.path.join(self.script_path,script_name)
        self.submit_command = submit_command
        self.python_script = python_script(script_name,None,libs = python_libs,
                                           envs = python_envs,python_version = python_version)

        self.write_file_attributes = {'fluent_journal':fluent_pbs.input_file,
                                      'fluent_pbs':self.PACE_PBS,
                                      'python_script':self.python_script.script_name}
        

    def execute_command(self, f: str) -> str:
        return ['python ',self.python_script.script_name]
    
    def pre_write(self, folder: str) -> None:
    
        self.python_script.target_dir = folder
        def script_modification(txt:str) -> str:
            text = txt.replace('<file_name>',self.PACE_PBS)
            text = text.replace('<backend>',self.submit_command)
            return text
        
        self.python_script.script_modifications = script_modification

    def _from_file_parser(dmdict : dict) -> Tuple:
        
        fluentpbs = dmdict['fluent_pbs']['class']
        pbs = fluentpbs.from_dict(dmdict['fluent_pbs'])
        fluentrun = dmdict['fluent_journal']['class']
        run = fluentrun.from_dict(dmdict['fluent_journal'])

        return ([run,pbs],)

class FluentBatchSubmission(ABC):

    """
    Base class for representing a batch submission of Fluent computations

    Parameters
    ----------
    fluent_sumission_list : list
            a list of objects with FluentSubmission as their base class. 
    index : Iterable
            an iterable (list, np.ndarray, pandas Series) with the same length as the\
            fluent_submission_list
    prefix : str
            gives the ability to add a prefix to the names in the fluent_submission_list
    seperator : str
            gives the ability to seperate the prefix and the index of the names in the\
            fluent_submission_list
    """

    LINE_BREAK = '\n'
    
    os_name = sys.platform
    if os_name == 'win32' or os_name == 'win64':
        BATCH_EXE_EXT = '.bat'
        TERMINAL_TYPE = 'powershell'
        _PATH = WindowsPath
    elif os_name == 'linux' or os_name == 'posix':
        BATCH_EXE_EXT = '.sh'
        TERMINAL_TYPE = 'bash'
        _PATH = PosixPath
    else:
        raise ValueError('Cannot determine Path structure from platform: {}'.format(os_name))
    
    BATCH_EXE_FNAME = 'batch' + BATCH_EXE_EXT
    path,_ = os.path.split(os.path.split(__file__)[0])
    script_path = os.path.join(path,'dat','scripts')
    BATCH_MONITER_FILE = os.path.join(script_path,'batch_deploy.py')
    POST_SCRIPT_FILE = os.path.join(script_path,'post_batch.py')
    _df = None

    def __init__(self,fluent_submission_list: list,
                      index = None,
                      prefix = '',
                      seperator = '-',
                      case_file = None,
                      move_batch_files = [],
                      submit_command = 'sbatch',
                      check_time = 120,
                      num_resubmit = 5):

        super().__init__()
        index,prefix,seperator = self._initializer_kwarg_parser(len(fluent_submission_list),
                                                                index,prefix,seperator)
        

        self.prefix = prefix
        self.seperator = seperator
        if case_file is not None:
            self.case_file = self._PATH(case_file)
        
        self.__submission_object = dict(zip([prefix + seperator + str(i) for i in index],
                                             fluent_submission_list))
        
        self.move_batch_files = move_batch_files
        self.check_time = check_time
        self.num_resubmit = num_resubmit
        self.batch_moniter_file = None
        self.submit_command = submit_command
        for key,value in self.__submission_object.items():
            try:
                value.fluent_journal.reader.pwd = key
            except AttributeError:
                pass
        

    @staticmethod
    def _initializer_kwarg_parser(n: int,
                                  index: Iterable,
                                  prefix: str,
                                  seperator: str) -> tuple:
        """
        Helper function for parsing the index, prefix, and seperator for initialization

        Parameters
        ----------
        n : int
                length of the submission object
        index : Iterable
                the index of the submission list
        prefix : str
                optional prefix of the index
        seperator : str
                optional seperator between the prefix and the index
        
        Returns
        -------
        tuple : Tuple
                a parsed Tuple containing (index,prefix,seperator)
        """
        if index is None:
            index = range(n)
        
        if prefix is None or prefix == '':
            try:
                if index.name is not None:
                    prefix = index.name
                else:
                    prefix = ''
                    seperator = ''
            except AttributeError:
                prefix = ''
            
        return index,prefix,seperator

    @property
    def submission_object(self):
        return self.__submission_object

    @submission_object.setter
    def submission_object(self,so):
        self.__submission_object = so
        
    def __add__(self,other) -> None:

        if not isinstance(other,FluentBatchSubmission):
            raise TypeError('can only add one fluent batch submission with another')

        def _add_df(df1,df2):

            return pd.concat([df1,df2],axis = 0)

        def _add_submission_object(so1,so2):
            
            so = dict.fromkeys(list(so1.keys()) + list(so2.keys()))

            for key in so2:
                if key in so1:
                    raise ValueError('ALl keys in submission object (controlled by the index) must be unique between the added batch submission')

            for key, values in so1.items():
                so[key] = values
            
            for key, values in so2.items():
                so[key] = values

            return so
        
        self.submission_object = _add_submission_object(self.submission_object,
                                                        other.submission_object)
        
        self._df = _add_df(self._df,other._df)
        
        return self

    def _populate_batch_cache_folder(self,parent: str) -> None:
        """
        make the cache to access later
        """
        batch_cache = BatchCache(parent)
        batch_cache.cache_batch(self.submission_object,
                                self._df,
                                prefix = self.prefix,
                                seperator = self.seperator)
    
    def _setup_batch_moniter_file(self,parent: str) -> None:

        def script_modification(txt:str) -> str:
            text = txt.replace('<submit_file>',self.PACE_PBS)
            text = text.replace('<solution_file_name>','solution.trn')
            text = text.replace('<check_time>',str(self.check_time))
            text = text.replace('<num_resubmit>', str(self.num_resubmit))
            text = text.replace('<backend>',self.submit_command)

            return text

        self.batch_moniter_file = PaceScript(self.BATCH_MONITER_FILE,
                                             parent,
                                             script_modifications= script_modification,
                                             libs = [os.path.join(self.path,'pace.py')])
    
    def _setup_post_file(self,parent: str) -> None:

        def script_modification(txt: str) -> str:
            text = txt.replace('<submit_file>',self.PACE_PBS)
            text = text.replace('<solution_file_name>','solution.trn')
            text = text.replace('<backend>',self.submit_command)

            return text
        
        self.post_script_file = PaceScript(self.POST_SCRIPT_FILE,
                                            parent,
                                            script_modifications=script_modification)
    
    def move_fluent_post_files(self,folder: str,
                                    submission: FluentSubmission):

        for p in submission.fluent_journal.post:
            try:
                p.write(folder)
            except AttributeError:
                pass

    def make_batch_submission(self,parent: str,
                                   verbose = True,
                                   purge = False,
                                   overwrite = False):
        
        """
        Formatting the submission
        makes appropriate directories if they do not exist
        and optionally purges data using a safety delete that does not allow
        recursion past a level of 2 on file folders, and will not delete .cas
        or .dat files

        Parameters
        ----------
        parent : str
                the parent or root directory of the submission to make
        verbose : bool
                if True will print information during runtime
        purge : bool
                if True will purge the parent folder of any files or folders prior to 
                populating with current batch information
        """
        
        

        if not os.path.isdir(parent):
            os.mkdir(parent)
        else:
            if purge:
                _safety_delete(parent,max_depth= 2, keep_exts= ['.cas','.dat'])
            
            try:
                os.mkdir(parent)
            except FileExistsError:
                pass
        
        for file in set(self.move_batch_files):
            if file is not None:
                try:
                    shutil.copy2(file,parent)
                except shutil.Error as fe:
                    if overwrite:
                        os.remove(parent,os.path.split(file)[0])
                        shutil.copy2(file,parent)
                    else:
                        raise FileExistsError(fe)
        
        #write some scripts to the folder that help with monitering
        #and an additonal post re-run script
        self._setup_batch_moniter_file(parent)
        self._setup_post_file(parent)
        self.batch_moniter_file.write(parent)
        self.post_script_file.write(parent)

        self._populate_batch_cache_folder(parent)
        keys = list(self.submission_object.keys())
        python_version = self.submission_object[keys[0]].python_script.python_version

        
        txt = 'module load anaconda3/' + python_version + self.LINE_BREAK
        txt += 'conda init ' + self.TERMINAL_TYPE + self.LINE_BREAK
        txt += 'conda activate' + self.LINE_BREAK
        
        for folder,submission in self.submission_object.items():
            if verbose:
                txt += 'echo "executing job located in folder: {}"'.format(folder) + self.LINE_BREAK
            
            command,file = submission.format_submit(os.path.join(parent,str(folder)))
            self.move_fluent_post_files(os.path.join(parent,str(folder)),submission)
            txt += 'cd '  + str(folder) + self.LINE_BREAK 
            txt += ''.join([command,file,' &',self.LINE_BREAK])
            txt += 'cd ..' + self.LINE_BREAK

        txt += 'python ' + self.batch_moniter_file.script_name + ' &' + self.LINE_BREAK
        txt += 'conda deactivate' + self.LINE_BREAK
        txt += 'module unload anaconda3/' + python_version + self.LINE_BREAK

        return txt

    @abstractmethod
    def generate_submission(parent : str,
                             *args,
                             purge = False,
                             verbose = True,
                             **kwargs) -> None:
        
        pass
    
    @classmethod
    def from_batch_cache(cls,
                         batch_folder: str): 
        """
        read in the batch_cache
        """
        batch_cache = BatchCache(batch_folder)
        so = batch_cache.read_submission_object_cache()
        fmt_kwargs = batch_cache.read_formatting_cache()
        df = batch_cache.read_df_cache()

        _cls = cls(list(so.values()),index = list(so.keys()),
                    **fmt_kwargs)

        #there are some troublesome classes that I have to hack to make work here
        for pwd,fluent_submission in _cls.submission_object.items():
            fluent_submission.fluent_journal.reader.pwd = pwd 
                
        _cls._df = df
        return _cls

    @classmethod
    def from_frame(cls,
                   case_file: str,
                   turbulence_model:str,
                   df:DataFrame,
                   submission_args:List,
                   prefix = '',
                   seperator = '-',
                   script_name = None,
                   python_libs = [],
                   python_envs = [],
                   python_version = '2019.10',
                   submit_command = 'sbatch',
                   *frargs,
                   **frkwargs):

        """
        Class method for creating a fluent batch submission using a data frame
        refer to the util.py document for details on the specification of the input dataframe

        the SAME pbs script is used for each of the runs - if there needs to be a different pbs script for 
        each run you should consider manually building the list

        frargs and frkwargs are passed to the fluent run objects for each of the FluentSubmissions - so they will
        be the same for each run - again if you need these to be different you should consider building the
        batch submission differently or submitting seperate jobs
        """
        
        submission_kwargs = {'script_name': script_name,
                             'python_libs': python_libs,
                             'python_envs': python_envs,
                             'python_version': python_version}
        
        if not isinstance(submission_args,list) and not isinstance(submission_args,Tuple):
            submission_args = [submission_args]
        
        index,_,seperator = cls._initializer_kwarg_parser(df.shape[0],
                                                          df.index,prefix,seperator)

        boundary_df = partition_boundary_table(df,turbulence_model)
        _,case_name = os.path.split(case_file)
        
        sl,index = cls._submission_list_from_boundary_df(cls.submission_args_from_boundary_df,
                                                         cls.SUBMISSION_CLASS,
                                                         case_name, boundary_df, submission_args,
                                                          submission_kwargs,
                                                          seperator,*frargs,**frkwargs)
        
        _cls = cls(sl,index = index,prefix = index.name,
                    case_file = case_file,submit_command = submit_command)

        _cls._df = df

        return _cls

    @staticmethod
    def _submission_list_from_boundary_df(submission_object_parser : callable,
                                            submission_class : object,
                                            case_name: str,
                                            bdf:DataFrame,
                                            submission_args: list,
                                            submission_kwargs: dict,
                                            seperator: str,
                                            *frargs,
                                            **frkwargs) -> list:

        """
        make a submission object from a boundary DataFrame i.e. a DataFrame of
        FluentBoundaryConditions.
        """
        
        submit_list = []
        name = '' if bdf.index.name is None else bdf.index.name
        for index in bdf.index:
            fluent_journal = FluentJournal(case_name,
                                            reader = BatchCaseReader,
                                            *frargs,**frkwargs)
            
            fluent_journal.reader.pwd = name + seperator + str(index)
            fluent_journal.boundary_conditions = list(bdf.loc[index])
            submission_args =\
                 submission_object_parser(submission_args,
                                          case_name,index,name,seperator,
                                          *frargs,**frkwargs)

            submit_list.append(
                                submission_class(fluent_journal,
                                                *submission_args,
                                                **submission_kwargs)
                                )
        
        return submit_list,bdf.index

    @abstractstaticmethod
    def submission_args_from_boundary_df(submission_args: list,
                                         case_name : str,
                                         index,
                                         name: str,
                                         seperator : str,
                                         *frargs,
                                         **frkwargs) -> Tuple:
        pass

class PaceBatchSubmission(FluentBatchSubmission):

    PACE_PBS = 'fluent.pbs'
    SUBMISSION_CLASS = PaceFluentSubmission

    def __init__(self,fluent_submission_list: list,
                      index = None,
                      prefix = '',
                      seperator = '-',
                      case_file = None,
                      submit_command = 'sbatch'):

        super().__init__(fluent_submission_list,
                         index = index,
                         prefix = prefix,
                         seperator = seperator,
                         case_file= case_file,
                         submit_command = submit_command)
        
        #these are fixed on PACE
        self.BATCH_EXE_FNAME = 'batch.sh'
        self.TERMINAL_TYPE = 'bash'
    
    def generate_submission(self,parent: str,
                            purge=False, 
                            verbose=True,
                            overwrite = False) -> None:
        
        self.move_batch_files.append(self.case_file)

        _bf = os.path.join(parent,self.BATCH_EXE_FNAME)
        txt = self.make_batch_submission(parent,
                                        verbose = verbose, 
                                        purge = purge,
                                        overwrite = overwrite)

        with open(_bf,'w',newline = self.LINE_BREAK) as file:
            file.write(txt)


    @staticmethod
    def submission_args_from_boundary_df(submission_args: list,
                                         case_name : str,
                                         index,
                                         name: str,
                                         seperator : str,
                                         *frargs,
                                         **frkwargs) -> Tuple:
        
        _pbs = submission_args[0].copy()
        _pbs.script_header.name = name + seperator + str(index)
        return (_pbs,)

class BatchCache:
    
    LINE_BREAK = '\n'
    _BATCH_CACHE_FOLDER = '_batchcache_'
    _SUBMISSION_CACHE_FILE = '.submission'
    _FRAME_CACHE_FILE = '.frame'
    _FORMATTING_CACHE_FILE = '.fmt'
    
    def __init__(self,batch_folder: str):

        self.batch_folder = batch_folder

        #check to see if the cache folder exists
        if not os.path.isdir(self.batch_cache):
            os.mkdir(self.batch_cache)

    @property
    def batch_cache(self):
        return os.path.join(self.batch_folder,self._BATCH_CACHE_FOLDER)

    def cache_submission_object(self,submission_object:dict) -> None:
        """
        cache the submission object for later retrieval
        """

        sf = os.path.join(self.batch_cache,self._SUBMISSION_CACHE_FILE)
        with open(sf,'w') as sf_file:
            for folder,submission in submission_object.items():
                submission_cache_file = os.path.join(self.batch_cache,folder)
                try:
                    submission.serialize(submission_cache_file)
                except TypeError as t:
                    warnings.warn(str(t))
                
                sf_file.write(folder + self.LINE_BREAK)
    
    def cache_df(self, df: pd.DataFrame) -> None:
        """
        cache the data frame if there is one associated with the batch
        """

        frame_file = os.path.join(self.batch_cache,self._FRAME_CACHE_FILE)
        df.to_csv(frame_file)
    
    def cache_batch_formatting(self,kwargs) -> None:
        """
        cache the formatting arguments
        """

        with open(os.path.join(self.batch_cache,self._FORMATTING_CACHE_FILE),'w') as file:
            json.dump(kwargs,file)
    
    def cache_batch(self,submission_object: dict,
                         df = None,
                         **fmtkwargs) -> None:
        """
        cache everything associated with the batch for rebuild
        """
        
        self.cache_submission_object(submission_object)
        if df is not None:
            self.cache_df(df)
        
        self.cache_batch_formatting(fmtkwargs)

    def read_submission_object_cache(self, so_class: FluentSubmission) -> dict:
        """
        read in the submission object cache
        """
        sf = os.path.join(self.batch_cache,self._SUBMISSION_CACHE_FILE)
        with open(sf,'r') as file:
            folders = []
            for line in file.readlines():
                folders.append(line.strip())
        
        submission_object = dict.fromkeys(folders)
        for folder in folders:
            submission_file_name = os.path.join(self.batch_cache,folder)
            submission_object[folder] = so_class.from_file(submission_file_name)
        
        return submission_object
    
    def read_df_cache(self) -> pd.DataFrame:
        """
        read in the cached data frame
        """
        try:
            df_file = os.path.join(self.batch_cache,self._FRAME_CACHE_FILE)
            return pd.read_csv(df_file,header = 0,index_col= 0)
        except FileNotFoundError:
            return None
        
    def read_formatting_cache(self) -> dict:
        """
        read in the cached formatting
        """
        with open(os.path.join(self.batch_cache,self._FORMATTING_CACHE_FILE),'r') as file:
            fmt_data = json.load(file)
        
        return fmt_data

class BatchSubmissionSummary:

    FLUENT_SOLUTION_EXT = '.trn'
    FLUENT_REPORT_FILE_EXT = '.out'
    FLUENT_DATA_EXT = '.dat'
    FLUENT_CASE_EXT = '.cas'
    COLUMNS = ['data','case','solution','report','completed']

    def __init__(self, folder: str):
        
        self._folder= folder
        self.filesys = TableFileSystem(folder)
    
    def get_folders_with_data(self):

        return list(self.filesys._find_ext_in_submission_folders(self.FLUENT_DATA_EXT).keys())
    
    def get_folders_with_case(self):
        return list(self.filesys._find_ext_in_submission_folders(self.FLUENT_CASE_EXT).keys())

    def get_folders_with_solution(self):
        self.filesys.map_solution_files()
        return list(self.filesys.solution_file_dict.keys())
    
    def get_folders_with_report_file(self):
        self.filesys.map_report_files()
        return list(self.filesys.report_file_dict.keys())
    
    def get_folders_with_completed_solution(self):
        
        folders = []
        self.filesys.solution_files
        for solution_file in self.filesys.solution_files.keys:
            with self.filesys.solution_files[solution_file] as sf:
                if sf.STATUS:
                    folder = self.filesys.Path(os.path.join(self._folder,sf.fluent_folder))
                    folders.append(folder)
        
        return folders
    
    def make_summary(self):

        dfolders = self.get_folders_with_data()
        cfolders = self.get_folders_with_case()
        sfolders = self.get_folders_with_solution()
        rfolders = self.get_folders_with_report_file()
        csfolders = self.get_folders_with_completed_solution()

        index = np.array(list(set(dfolders + cfolders + sfolders + rfolders + csfolders)))
        data = np.zeros(shape = [index.shape[0],len(self.COLUMNS)],dtype = bool)
        for i,_list in enumerate([dfolders,cfolders,sfolders,rfolders,csfolders]):
            for j in range(len(index)):
                if index[j] in _list:
                    data[j,i] = True
        
        return pd.DataFrame(data,index = index,columns = self.COLUMNS)

class FileSystemTree:

    def __init__(self,root: str,
                      os_system = 'windows'):

        self.os_system = os_system.lower()
        self.__path = self._get_path(root)
        if self.os_system == 'windows':
            self.delim = '\\'
        else:
            self.delim = '/'
        
        self.__tree = None
        self.__depth = None

    @property
    def path(self):
        return self.__path

    @property
    def tree(self):
        if self.__tree is None:
            self.tree_contents()
        return self.__tree
    
    @tree.setter
    def tree(self,t):
        self.__tree = t

    @property
    def depth(self):
        return self.__depth
    
    @depth.setter
    def depth(self,d):
        self.__depth = d

    def iterfile(self):
        flattend = _flatten_dict(self.tree)
        for key in flattend:
            yield key

    def tree_contents(self):
        self.depth = 0
        self.tree = self._make_tree(self.path)
        return self.tree
    
    def _make_tree(self,root:str):
        
        if not issubclass(type(root),Path): 
            _root = self._get_path(root)
        else:
            _root = root
        
        contents = dict.fromkeys(_root.iterdir())
        for f in contents:
            if f.is_dir():
                contents[f] = self._make_tree(f)
            else:
                self.depth = max(self.depth,len(str(f.parent).split(self.delim)))
                contents[f] = None
            
        return contents
    
    def _get_path(self,path: str):
        
        if self.os_system == 'windows':
            path = WindowsPath(path)
        elif self.os_system == 'linux' or self.os_system == 'posix':
            path = PosixPath(path)
        else:
            raise ValueError("os_system must be specified by strings: (1) windows (2) linux or (3) posix")

        return path

def _flatten_dict(d, 
                  parent_key='', 
                  sep='\\') -> dict:
    
    """
    flatten a dictionary, concatenating the keys as string representations
    using sep as the seperator. 

    meant to flatten dictionaries of path from the pathlib library so will error out 
    if you pass something else
    """ 

    items = []
    for k, v in d.items():
        new_key = str(parent_key.parent) + sep + str(parent_key.name) + sep + str(k.name) if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    
    return dict(items)

def _safety_delete(root: str,
                   max_depth = 3,
                   keep_files = [],
                   keep_exts = []) -> None:
    """
    removes a folder in its entirety only if the folder specified by 
    root contains a tree structure with a maximum number of levels specified by 
    max_depth below it. 

    Will not delete the whole root if keep_files or keep_exts is not empty,
    will delete every other file that is not
    not contained in keep_files and does not have an extension in keep_exts

    makes sure you don't accidently do something stupid like delete your whole system
    or rather makes it really hard to do this
    """

    tree = FileSystemTree(root)
    tree.tree

    if tree.depth > max_depth:
        pass
    else:
        if not keep_files and not keep_exts:
            shutil.rmtree(root)
        else:
            for file in tree.iterfile():
                ext = os.path.splitext(file)[1]
                if file not in keep_files and ext not in keep_exts:
                    os.remove(file)

