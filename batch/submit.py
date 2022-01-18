#native imports
from typing import Iterable, Tuple
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

#package imports
from ..disk import SerializableClass
from .pbs import FluentPBS
from ..tui import BatchCaseReader, FluentJournal
from .table_parse import partition_boundary_table
from .filesystem import TableFileSystem

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

    def write(self,folder : str) -> None:

        """ 
        writes the fluent journal to a folder along with any additional
        required files.

        if the value of the requested key in the write file attribute is True,
        assume that this is a file that we want to copy to the directory
        """
        
        if not os.path.isdir(folder):
            os.mkdir(folder)
        
        for attr, file_name in self.write_file_attributes.items():
            if isinstance(file_name,bool) and file_name:
                _,fname = os.path.split(attr)
                dst_file = os.path.join(folder,fname)
                shutil.copyfile(attr,dst_file)
            else:
                self.__getattribute__(attr).write(os.path.join(folder,file_name))
    
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

    PACE_PBS = 'fluent.pbs'

    def __init__(self,fluent_journal: FluentJournal,
                      fluent_pbs: FluentPBS) -> None:

        super().__init__(fluent_journal)
        self.write_file_attributes = {'fluent_journal':fluent_pbs.input_file,
                                      'fluent_pbs':self.PACE_PBS}

        self.fluent_pbs = fluent_pbs

    def execute_command(self, f: str) -> str:
        return ['qsub ',self.PACE_PBS]
    
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
    elif os_name == 'linux' or os_name == 'posix':
        BATCH_EXE_EXT = '.sh'
    else:
        raise ValueError('Cannot determine Path structure from platform: {}'.format(os_name))
    
    BATCH_EXE_FNAME = 'batch' + BATCH_EXE_EXT

    _df = None

    def __init__(self,fluent_submission_list: list,
                      index = None,
                      prefix = '',
                      seperator = '-',
                      case_name = None,
                      *args,**kwargs):

        super().__init__()
        index,prefix,seperator = self._initializer_kwarg_parser(len(fluent_submission_list),
                                                                index,prefix,seperator)

        self.prefix = prefix
        self.seperator = seperator
        self.case_name = case_name
        self.__submission_object = dict(zip([prefix + seperator + str(i) for i in index],
                                             fluent_submission_list))


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
    
    @property
    def case_file(self):
        return os.path.split(self.case_file)[1]
    
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
    
    def make_batch_submission(self,parent: str,
                                   verbose = True,
                                   purge = False):
        
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
        
        self._populate_batch_cache_folder(parent)
        
        txt = ''
        for folder,submission in self.submission_object.items():
            if verbose:
                txt += 'echo "executing job located in folder: {}"'.format(folder) + self.LINE_BREAK
            
            command,file = submission.format_submit(os.path.join(parent,str(folder)))
            txt += 'cd '  + str(folder) + self.LINE_BREAK 
            txt += ''.join([command,file,self.LINE_BREAK])
            txt += 'cd ..' + self.LINE_BREAK

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
                   case_name: str,
                   turbulence_model:str,
                   df:DataFrame,
                   submission_args:list,
                   prefix = '',
                   seperator = '-',
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

        if not isinstance(submission_args,list) and not isinstance(submission_args,Tuple):
            submission_args = [submission_args]
        
        index,_,seperator = cls._initializer_kwarg_parser(df.shape[0],
                                                          df.index,prefix,seperator)

        boundary_df = partition_boundary_table(df,turbulence_model)
        _,case_file = os.path.split(case_name)
        
        sl,index = cls._submission_list_from_boundary_df(cls.submission_args_from_boundary_df,
                                                         cls.SUBMISSION_CLASS,
                                                         case_file, boundary_df, submission_args,
                                                          seperator,*frargs,**frkwargs)
        
        _cls = cls(sl,index = index,prefix = index.name,
                    case_name = case_name)
        _cls._df = df

        return _cls

    @staticmethod
    def _submission_list_from_boundary_df(submission_object_parser : callable,
                                            submission_class : object,
                                            case_name: str,
                                            bdf:DataFrame,
                                            submission_args: list,
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
            submission_args = submission_object_parser(submission_args,case_name,
                                                        index,name,seperator,
                                                        *frargs,**frkwargs)

            submit_list.append(
                                submission_class(fluent_journal,
                                                *submission_args)
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
                      case_name = None):

        super().__init__(fluent_submission_list,
                         index = index,
                         prefix = prefix,
                         seperator = seperator,
                         case_name = case_name)
        
        self.BATCH_EXE_FNAME = 'batch.sh'
    
    def generate_submission(self,parent: str,
                            purge=False, 
                            verbose=True) -> None:

        _bf = os.path.join(parent,self.BATCH_EXE_FNAME)
        txt = self.make_batch_submission(parent,
                                        verbose = verbose, 
                                        purge = purge)

        with open(_bf,'w',newline = self.LINE_BREAK) as file:
            file.write(txt)

        _,case_name = os.path.split(self.case_name)
        dst = os.path.join(parent,case_name)
        try:
            shutil.copy2(self.case_name,dst)
        except shutil.Error:
            pass
    
    @staticmethod
    def submission_args_from_boundary_df(submission_args: list,
                                         case_name : str,
                                         index,
                                         name: str,
                                         seperator : str,
                                         *frargs,
                                         **frkwargs) -> Tuple:
        
        _pbs = submission_args[0].copy()
        _pbs.pbs.name = name + seperator + str(index)
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
                submission.serialize(submission_cache_file)
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

    def read_submission_object_cache(self) -> dict:
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
            submission_object[folder] = FluentSubmission.from_file(submission_file_name)
        
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
    
    def remake_batch(self,new_batch_folder: str,
                          missing_criterion: list,
                          **batch_kwargs) -> None:

        """ 
        allows the user to remake a batch based on some missing criterion specificed 
        by COLUMNS
        """
        
        for mc in missing_criterion:
            if mc not in self.COLUMNS:
                raise ValueError('can only remake batch based on missing criterion in: {}'.format(self.COLUMNS))
        
        summary = self.make_summary()
        
        try:
            _summary = summary[missing_criterion]
            exclude_series = _summary.all(axis = 1)
            cached_batch = FluentBatchSubmission.from_batch_cache(self._folder)
            for index in exclude_series.index:
                if exclude_series.loc[index]:
                    cached_batch.submission_object.pop(index.name)
            
            for folder,submission in cached_batch.submission_object.items():
                submission.fluent_journal.reader.pwd = folder
            
            if cached_batch._df is not None:
                new_index = []
                dtype = cached_batch._df.index.dtype
                try:
                    name_length = len(cached_batch._df.index.name)
                except TypeError:
                    name_length = 0
                
                for index in exclude_series.index:
                    new_index.append((index.name[name_length:]))
                
                new_index = np.array(new_index,dtype = dtype)

                _exclude_series = pd.Series(exclude_series.to_numpy(),index = new_index)
                cached_batch._df = cached_batch._df[~_exclude_series]
            
            cached_batch.bash_submit(new_batch_folder,**batch_kwargs)
        except FileNotFoundError:
                raise FileNotFoundError('cannot find batch cache in batch folder')

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
        