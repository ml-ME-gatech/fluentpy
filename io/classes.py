#third party imports
from ast import Index
from operator import concat, index
from typing import Iterable,Union
import more_itertools
import numpy as np
import pandas as pd 
import os
import re
from abc import ABC,abstractmethod
from itertools import islice
import itertools
from more_itertools import peekable
from pandas.core.algorithms import isin

#package imports
from ._file_scan import _get_repeated_text_phrase_lines,_get_text_between_phrase_lines,_convert_delimited_text
from .filesystem import FluentFolder,DesignPointFolder
from .._msg import get_error_message,get_warning_message
from ..fluentPyconfig import settings

__all__ = [
           'ReportFileOut',
           'SolutionFile',
           'ReportFilesOut',
           'SolutionFiles',
           'DesignPoint'
           ]

"""
Creation:
Author(s): Michael Lanahan 
Date: 05.10.2021

Last Edit: 
Editor(s): Michael Lanahan
Date: 10.01.2021

-- Description -- 
These are the work horse classes for reading, interpreting, and
interfacing with workbench fluent folder files. Classes are much much easier in this context
as they lend themselves to easily and concicsely representing file folder information
"""

LINE_BREAK = '\n'

#base class for fluent files
#could be useful to add stuff on here later
class FluentFile(ABC):

    def __init__(self,fname: str,               #full path to folder name
                      read_length = False,      #read the length of the file, if file is huge we may not want to do this for performance issues.
                      fluent_folder = None,     #option to provide the fluent Folder name if it is already known.
                      case_name = None,         #option to provide the case name
                      *args,**kwargs):

        self.__fname = fname
        self.file = None
        self.length = None
        self.__df = None

        #determine from whence the folder comes
        if fluent_folder is None:
            try:
                ff = FluentFolder(fname)
                self.__fluent_folder = ff.ff_root
            except AttributeError:
                self.__fluent_folder = None
        else:
            self.__fluent_folder = fluent_folder
        
        self.__case_name = case_name
        
        #if the file is very long may not want to do this if the information is not neccessaary
        if read_length:
            self._get_length()
            
    
    #"official" string representation of an object
    def __repr__(self):
        return "File: {} \nCase: {} \nFolder: {}".format(self.fname,self.caseName,self.fluent_folder)

    #"informal" string represetnation
    def __str__(self):
        return "File Name: {}".format(self.fname)

    def __enter__(self):
        #context manager enter
        self.file = open(self.fname,"r")
        return self
    
    def __exit__(self,exc_type, exc, exc_tb):
        #context manager exit
        self.file.close()   

    def _get_length(self):
        """
        get length of the file - notice that this has to iterate
        through the entire file which may not be advisable for very long files
        """
        def __getit(fp):
            for (self.length,_) in enumerate(fp,1):
                pass

        if self.file:
            self.file.seek(0)
            __getit(self.file)
        else:
            with open(self.fname,'r') as file:
                __getit(file)
        
        self.file.seek(0)
    
    def __len__(self):
        return self.length
        
    @property
    def length(self):
        if self.__length is None:
            self._get_length()
        
        return self.__length
        
    @length.setter
    def length(self,flen):
        self.__length = flen
    
    @property
    def case_name(self):
        return self.__case_name

    @property
    def fluent_folder(self):
        return self.__fluent_folder
    
    @property
    def fname(self):
        return self.__fname

    @fname.setter
    def fname(self,f):
        self.__fname = f
    
    @property
    def df(self):
        return self.__df

    @df.setter
    def df(self,df):
        self.__df = df

    @abstractmethod
    def readdf(self):
        pass

#base class for fluent file(s) as in more than one files
class FluentFiles(dict):

    def __init__(self,flist: list,
                      *args,**kwargs):

        self.component_class = None
        self.keys = flist
        self.__data = {}
        self.__df = None
        self.__columns = []
        super().__init__(*args,**kwargs)

    @property
    def data(self):
        return self.__data
    
    @data.setter
    def data(self,d):
        self.__data = d
    
    @property
    def df(self):
        return self.__df
    
    @df.setter
    def df(self,df):
        self.__df = df

    def _set_component_class(self,fluent_folders = []):
        if self.component_class is None:
            raise NotImplementedError('Must set Class in subclasses of fluentFiles')
        
        if not fluent_folders:
            fluent_folders = [None for _ in range(len(self.keys))]

        for key,ff in zip(self.keys,fluent_folders):
            self.__setitem__(key,self.component_class(str(key),
                                 fluent_folder = ff)) 
        
    def __setitem__(self,key,item):
        self.__dict__[key] = item
    
    def __getitem__(self,key):
        return self.__dict__[key]

    @property
    def columns(self):
        return self.__columns
    
    @columns.setter
    def columns(self,c):
        self.__columns = c
    
    #convenience function
    def _parsedicts(self,edict,name,fill_value = None):

        if edict:
            if len(edict) != len(self.keys):
                raise AttributeError("The length of the list: {} must be equal to the length of the filelist".format(name))
        else:
            edict = {key:fill_value for key in self.keys}
        
        return edict

    #load the data set into a list of fluent files
    def load(self,
              skiprows = [],    #list of lists 
              nrows = [],       #list of lists
              convergedResult = False,
              index = []):
        
        if convergedResult:
            skiprows = self._parsedicts(skiprows,'skiprows',fill_value = 'converged')
        else:
            skiprows = self._parsedicts(skiprows,'skiprows',fill_value = [])
    
        nrows = self._parsedicts(nrows,'nrows',fill_value = None)

        for key in self.keys:
            with self.__getitem__(key) as ffile:
                self.data[key] = ffile.readdf(skiprows[key],nrows[key])
                self.columns += list(ffile.df.columns)
        
        self.columns = list(set(self.columns))

    #get data from a particular variable name from each result file
    def get_variable(self,varname: str,
                          ignore_missing = False) -> pd.DataFrame:
        """
        get the data for a particular variable from each result file
        with an optional keyword argument to permit ignoring variables that
        appear in some files but not another. This can be dangerous
        so I have made the default to NOT ignore missing
        """
        if not self.data:
            self.load()

        dat = []
        for key in self.keys:
            try:
                with self.__getitem__(key) as ffile:
                    dat.append(ffile.readdf()[varname].rename(ffile.fluent_folder))
            except KeyError as ke:
                if ignore_missing:
                    dat.append(None)
                else:
                    raise KeyError(ke)
        
        data = pd.concat(dat,axis = 1)
        return data
    
class SurfaceFile(FluentFile):

    LINE_BREAK = '\n'
    SURFACE_CMD = 'surface'
    CREATE_SL_CMD = None
    EXIT_CMD = 'q'
    EXPORT_CMD = 'file/export/ascii'

    def __init__(self,fname,
                      fluent_folder = None) -> None:

        super().__init__(fname,fluent_folder= fluent_folder)

    def readdf(self):
        """
        this will output as a table of values like:
        cellnumber,xcoordinate,y-coordinate,z-coordinate,var1,var2,....

        where in the cellnumber column, the counting is local to the surface
        and will restart at 1 each time a new surface is defined
        """

        self.df = pd.read_csv(self.fname,sep = ',',header= 0)
        self.df.columns = [c.strip() for c in self.df.columns]
        return self.df

    
    def get_surface_list(self):

        """
        create a list of dataframes where each entry in the list
        is a dataframe containing the values of the variables
        at the surface
        """

        if self.df is None:
            self.readdf()
        
        idxs = np.where(self.df['cellnumber'] == 1)[0]
        surface_list = []
        for i in range(idxs.shape[0]-1):
            surface_list.append(self.df.iloc[idxs[i]:idxs[i+1]])
        
        surface_list.append(self.df.iloc[idxs[-1]:])
        
        return surface_list

    def _parse_from_table_input(array: Union[pd.DataFrame,np.ndarray],
                                R: Union[np.ndarray,float]) -> pd.DataFrame:

        """
        ensure that the input data has the following form:
        array is n x 3 where n is the number of points
        if array is a data frame the columns MUST be x,y,z
        """

        if array.ndim != 2:
            raise ValueError('Array must be two-dimensional')
        
        if array.shape[1] != 3:
            raise ValueError('table input only supported for 3D input i.e. x,y,z')
        
        if isinstance(array,np.ndarray):            
            
            df = pd.DataFrame(array,columns = ['x','y','z'])
        
        elif isinstance(array,pd.DataFrame):

            columns = [c.lower() for c in array.columns]
            if set(columns) != {'x','y','z'}:
                raise ValueError('Data frame columns must be x,y,z')
            
            df = array
        
        else:
            raise TypeError('Input array is not a np.ndarray or a pandas dataframe')

        if R is None:
            r = R
        else:
            if isinstance(R,pd.DataFrame):
                if not R.index.equals(df.index):
                    raise ValueError('R index does not much point index')
                
                r = R

            elif isinstance(R,np.ndarray):
                R = np.squeeze(R)
                if R.ndim != 1:
                    raise ValueError('Radius dimension must be a one-d array')
                if R.shape[0] != df.shape[0]:
                    raise ValueError('if Radius is specific as an array it must have the same dimension as input points')
                
                r = pd.Series(R,index = df.index)
            

            else:
                if not isinstance(R,(float,int)):
                    raise ValueError('R must be numeric if not an array')
                
                r = pd.Series(np.ones(df.shape[0])*R,index = df.index)
            
        return df,r
    
    def format_text(self):
        """
        plug-in to work with the pace-fluent module,allow creation of
        the script for point surface reading
        """
        text = 'file/read-journal' + LINE_BREAK
        text += self.fname + LINE_BREAK
        text += ',' + LINE_BREAK
        return text

    @staticmethod
    def _row_to_text(line_break: str,
                     row: np.ndarray) -> str:

        txt = ''
        for i in range(row.shape[0]):
            txt += str(row[i]) + line_break
        
        return txt

    @classmethod
    def create_fluent_input_from_table(cls, df: Union[pd.DataFrame, np.ndarray],
                                            R: Union[float,np.ndarray],
                                            prefix = None,
                                            seperator = '-',
                                            file_name = None) -> None:
        """
        convert a pandas dataframe to a series of TUI commands to create the
        poitns listed in the dataframe
        """
        cls.fname = file_name
        df,R = cls._parse_from_table_input(df,R)
        txt = cls.SURFACE_CMD + cls.LINE_BREAK
        names = []
        for i in df.index:
            txt += cls.CREATE_SL_CMD + cls.LINE_BREAK
            txt += prefix + seperator + str(i) + cls.LINE_BREAK
            names.append(prefix + seperator + str(i))
            txt += cls._row_to_text(cls.LINE_BREAK,df.loc[i])
            txt += str(R[i]) + cls.LINE_BREAK
        
        txt += cls.EXIT_CMD

        return txt,names

    @classmethod
    def write_fluent_input_from_table(cls, df: Union[pd.DataFrame,np.ndarray],
                                           R: Union[float,np.ndarray,pd.DataFrame],
                                           file_name: str,
                                           export_variables: list,
                                           prefix = None,
                                           seperator = '-',
                                           create_surfaces = True) -> None:

        """
        write the fluent TUI command to a file
        """
        text,names = cls.create_fluent_input_from_table(df,R,prefix = prefix,seperator = seperator,file_name = file_name)
        _txt =  cls.LINE_BREAK + cls.format_export_command(names,export_variables,file_name + '.out')
        if create_surfaces:
            text += _txt
        else:
            text = _txt
        
        with open(file_name,'w') as file:
            file.write(text)
        
        return cls(file_name)
    
    @classmethod
    def format_export_command(cls,
                              names: list,
                              field_variables: list,
                              file_name: str) -> None:

        txt = cls.EXPORT_CMD + cls.LINE_BREAK
        txt += file_name + cls.LINE_BREAK
        #format surfaces for output
        for name in names:
            txt += name + cls.LINE_BREAK
        
        txt += ',' + cls.LINE_BREAK                  #end of names
        txt += 'yes' + cls.LINE_BREAK                #give commma delimiter
        
        #format variables for output
        for fv in field_variables:
            txt += fv + cls.LINE_BREAK
        
        txt += ',' + cls.LINE_BREAK
        txt += 'yes' + cls.LINE_BREAK               #yes to cell-centered

        return txt

class SphereSliceFile(SurfaceFile):

    CREATE_SL_CMD = 'sphere-slice'

    def __init__(self,fname,
                      fluent_folder = None) -> None:

        super().__init__(fname,fluent_folder= fluent_folder)

    def readdf(self):
        return super().readdf()

    def get_sphere_surface_data(self,
                                statistic: callable,
                                dimension = 3):
        """
        convinience function for applying a statistic to the data
        of the spheres and returning the result as a dataframe with each
        row the result of that statistic applied to each variable in the dataframe
        the center of the sphere is taken as the mean
        """
        
        sl = self.get_surface_list()

        data = np.zeros([len(sl),sl[0].shape[1]-1])
        field_variables = [column for column in sl[0].columns if 
                         column not in ['x-coordinate','y-coordinate','z-coordinate','cellnumber']]
        
        for i,df in enumerate(sl):
            if dimension == 3:
                data[i,0:dimension] = np.mean(df[['x-coordinate','x-coordinate','z-coordinate']],axis = 0)
            elif dimension == 2:
                data[i,0:dimension] = np.mean(df[['x-coordinate','y-coordinate']],axis = 0)
            
        
            for k,var in enumerate(field_variables): 
                data[i,dimension + k] = statistic(df[var],axis = 0)
            
        
        columns = list(sl[0].columns)
        columns.pop(0)
        return pd.DataFrame(data,columns = columns)

    @classmethod
    def write_fluent_input_from_table(cls, df: Union[pd.DataFrame,np.ndarray],
                                           R: Union[float,np.ndarray,pd.DataFrame],
                                           file_name: str,
                                           export_variables,
                                           prefix = 'sphere',
                                           seperator = '-',
                                           create_surfaces = True) -> None:

        return super().write_fluent_input_from_table(df,R,file_name,export_variables,
               prefix = prefix,seperator=  seperator,create_surfaces = create_surfaces)

class SurfacePointFile(SurfaceFile):

    CREATE_SL_CMD = 'point-surface'

    def __init__(self,fname,
                      fluent_folder = None) -> None:

        super().__init__(fname,fluent_folder= fluent_folder)

    def readdf(self):
        return super().readdf()

    @classmethod
    def create_fluent_input_from_table(cls, df: Union[pd.DataFrame, np.ndarray],
                                            R,
                                            prefix = 'point',
                                            seperator = '-',
                                            file_name = None) -> None:
        """
        convert a pandas dataframe to a series of TUI commands to create the
        poitns listed in the dataframe
        """
        cls.fname= file_name
        df,_ = cls._parse_from_table_input(df,None)
        txt = cls.SURFACE_CMD + cls.LINE_BREAK
        names = []
        for i in df.index:
            txt += cls.CREATE_SL_CMD + cls.LINE_BREAK
            txt += prefix + seperator + str(i) + cls.LINE_BREAK
            names.append(prefix + seperator + str(i))
            txt += cls._row_to_text(cls.LINE_BREAK,df.loc[i])
        
        txt += cls.EXIT_CMD

        return txt,names

    @classmethod
    def write_fluent_input_from_table(cls, df: Union[pd.DataFrame,np.ndarray],
                                           file_name: str,
                                           export_variables: list,
                                           prefix = 'point',
                                           seperator = '-',
                                           create_surfaces = True) -> None:


        return super().write_fluent_input_from_table(df,None,file_name,export_variables,
        prefix = prefix,seperator=  seperator,create_surfaces = create_surfaces)
    
    def get_point_surface_data(self):
        """
        convinience function for turning the list of surfaces into an
        array
        """

        sl = self.get_surface_list()
        data = np.zeros([len(sl),sl[0].shape[1]])
        for i,df in enumerate(sl):
            data[i,:] = np.squeeze(df.to_numpy())
        
        return pd.DataFrame(data,columns = sl[0].columns)
    


class XYDataFile(FluentFile):

    DATA_DELIM = '((xy/key/label'
    LINE_BREAK = '\n'
    COLUMN_DELIM = '\t'
    SERIES_SPACING = 2
    DATA_END_LINE = ')'

    def __init__(self, fname: str,
                        fluent_folder= None):

        super().__init__(fname,fluent_folder = fluent_folder)
        self.__data_names = {}

    @property
    def data_names(self):
        return self.__data_names

    @data_names.setter
    def data_names(self,dn):
        self.__data_names = dn

    def _parse_text_block(self,txt_block: str) -> np.ndarray:

        return _convert_delimited_text(txt_block,self.COLUMN_DELIM,self.LINE_BREAK,
                                        float, force_columns= False)
    
    def deliminate_data_file(self) -> pd.DataFrame:

        self.file.seek(0)
        len_data_delim = len(self.DATA_DELIM)+2
        txt = ''
        data = []
        c = 0
        name = None

        column_name = next(self.file)[8:-3].strip()
        next(self.file)
        next(self.file)

        for line in self.file:
            if self.DATA_DELIM in line:
                if name is not None:
                    
                    dat = self._parse_text_block(txt)
                    data.append(dat)
                    self.data_names[name] = [c,c+dat.shape[0]]
                    c += dat.shape[0]
                    txt = ''
            
                name = line[len_data_delim:-3]
                
            else:
                if line.strip() != self.DATA_END_LINE and line.strip() != '':
                    txt += line
            
        dat = self._parse_text_block(txt)
        self.data_names[name] = [c,-1]
        data.append(dat)

        data = np.concatenate(data,axis = 0)
        self.df = pd.DataFrame(data[:,1:],index = data[:,0],
                              columns = [column_name])

        return self.df

    def readdf(self):
        return self.deliminate_data_file()
    
    def __getitem__(self,key):
        
        try:
            if self.data_names[key][1] == -1:
                return self.df.iloc[self.data_names[key][0]:]
            else:
                return self.df.iloc[self.data_names[key][0]:self.data_names[key][1]]
        except KeyError:
            raise KeyError('no domain entitled: {} in file'.format(key))
    
    def keys(self):
        return self.data_names.keys()

    
class PostDataFile(FluentFile):

    DATA_DELIM = '[Name]'
    DATA_START = '[Data]'
    LINE_BREAK = '\n'
    COLUMN_DELIM = ','

    def __init__(self,fname,fluent_folder = None):

        super().__init__(fname,fluent_folder= fluent_folder)
        self.__data_names = {}
    
    @property
    def data_names(self):
        return self.__data_names

    @data_names.setter
    def data_names(self,dn):
        self.__data_names = dn
    
    def _parse_consistent_text_block(self,txt_block):
        
        start = txt_block.find(self.DATA_START)+len(self.DATA_START) + 1
        txt_block = txt_block[start:]
        
        columns_end = txt_block.find(self.LINE_BREAK)
        columns = [c.strip() for c in txt_block[0:columns_end].split(self.COLUMN_DELIM)]
        txt_block = txt_block[columns_end+1:].strip() + self.LINE_BREAK

        return columns,_convert_delimited_text(txt_block,self.COLUMN_DELIM,
                                        self.LINE_BREAK,float,force_columns= False)


    def deliminate_consistent_data_file(self):

        self.file.seek(0)
        name = None
        txt = ''
        data = []
        c = 0
        for line in self.file:
            if self.DATA_DELIM in line:
                if name is not None:
                    _,dat = self._parse_consistent_text_block(txt)
                    data.append(dat)
                    self.data_names[name] = [c,c+dat.shape[0]]
                    c += dat.shape[0]
                    txt = ''
                
                _line = next(self.file)
                txt = _line
                name = _line.strip()
                
            else:
                txt += line
        
        columns,dat = self._parse_consistent_text_block(txt)
        self.data_names[name] = [c,-1]
        data.append(dat)

        data = np.concatenate(data,axis = 0)
        self.df = pd.DataFrame(data,columns = columns)
    
    def readdf(self):
        
        self.deliminate_consistent_data_file()
        return self.df
    
    def __getitem__(self,key):
        
        try:
            if self.data_names[key][1] == -1:
                return self.df.iloc[self.data_names[key][0]:]
            else:
                return self.df.iloc[self.data_names[key][0]:self.data_names[key][1]]
        except KeyError:
            raise KeyError('no domain entitled: {} in file'.format(key))
    
    def keys(self):
        return self.data_names.keys()


#class for supporting the report file from fluent
class ReportFileOut(FluentFile):

    _STR_REMOVE = [')','"','\n','(']
    _HEADER_LINE = 2
    _DATA_START = 3

    def __init__(self,fname,fluent_folder = None):

        super().__init__(fname,fluent_folder = fluent_folder)

    ##get headers in a custom fashion because .out files are annoying
    def _get_headers(self):
        iterdat = islice(self.file,self._HEADER_LINE,self._DATA_START)
        listHeaders = list(next(iterdat).split("\" \""))
        for i,lh in enumerate(listHeaders):
            for char in self._STR_REMOVE:
                listHeaders[i] = listHeaders[i].replace(char,'')
        
        return listHeaders

    #decide what rows to skip depending on user input
    #this starts on the first row of DATA, not the first line of the file
    def _parse_skip_rows(self,skiprows: int):

        if skiprows:
            try:
                skiprows = skiprows.lower()
            except AttributeError:
                pass
            if skiprows == 'converged':
                skiprows = self.length-self._DATA_START-1
        else:
            skiprows = None
        
        return skiprows

    #get data from the report file
    def _get_data_frame(self,skiprows: int ,
                             nrows: int):

        #parse skip rows and such key words
        skiprows = self._parse_skip_rows(skiprows)
        #reset file
        self.file.seek(0)
        return pd.read_csv(self.file,header = None,
                           skiprows = skiprows ,names = self._get_headers(),
                           nrows = nrows,index_col = 0,sep = ' ')
    
    #parse the report file header and data
    def readdf(self, 
                  skiprows = [],  #refer to pandas.read_csv documentation
                  nrows = None,    #refer to pandas.read_csv documentation
                  ):
        
        self.df = self._get_data_frame(skiprows,nrows)
        return self.df

class SolutionFile(FluentFile):

    _PARAM_PHRASE = r'WB->Fluent:Parameter name:'
    _SOL_START_PHRASE = r'  iter  '
    _SOL_END_PHRASE = r'Writing "| gzip -2cf >'
    _ITERATE_PHRASES = ['> solve/iterate',
                       'solve/iterate',
                       '> iterate',
                       'iterate']
    
    """
    The STATUS property of the SolutionFile indicates if the solution has 
    completed or not, determined by the logic in _get_status()
    False - solution is not finished
    True - solution is finished
    """
    def __init__(self,fname,
                      fluent_folder = None):

        super().__init__(fname,fluent_folder = fluent_folder)
        self.__input_parameters = None
        self.__STATUS = None
    
    @property
    def STATUS(self):
        if self.__STATUS is None:
            self._get_status()
        
        return self.__STATUS
    
    @STATUS.setter
    def STATUS(self,s):
        self.__STATUS = s

    @property
    def input_parameters(self):
        return self.__input_parameters
    
    @input_parameters.setter
    def input_parameters(self,fp):
        self.__input_parameters = fp
    
    #parses text from params and converts it into a dataframe 
    #with labeled columns which is 1 row with p (the number of paramters)
    #columns
    def read_params(self):
        """
        I may want to deprecciated this - or maybe provide better documentataion
        This only works with Workbench parameters - i.e. finds all of the parameters
        that are passed from workbench to fluent and this limiatations should be understood
        so as not to confuse the user on what boundary condition settings are being obtained
        """
        paramText = _get_repeated_text_phrase_lines(self.file,self._PARAM_PHRASE) +'\n'
        self.file.seek(0)
        paramDict = {}

        N = re.finditer(self._PARAM_PHRASE,paramText)
        T = re.finditer(',',paramText)
        E = re.finditer('\n',paramText)
        V = re.finditer('value:',paramText)
       
        for n,t,e,v in zip(N,T,E,V):
            name = paramText[n.end():t.start()]
            value = float(paramText[v.end():e.start()])
            paramDict[name] = value
        
        self.input_parameters = pd.Series(paramDict.values(),index = paramDict.keys())
        return self.input_parameters
    
    #parse the solution folder file in post into a pandas dataframe with the
    #columns being the various values tracked over the course of the solver
    #and the rows the iterations.
    def parse_solution_text(self,solution_text: str,
                                  eol1: Iterable,
                                  eol2: Iterable):
        skipchars = ['\n','!']
        endchars = ['>']
        if solution_text == '':
            return solution_text
        else:
            cleanedText = ''
            for e2,e1 in zip(eol2,eol1):
                line = solution_text[e2.start():e1.start()+1].strip() +'\n'
                try:
                    #check to see if we should consider this line
                    if line[0] in skipchars or 'Solution' in line:
                        continue
                    #check to see if this line indicates an end to the data we are interested in
                    elif line[0] in endchars:
                        break
                    else:
                        try:
                            int(line[0])

                            #ugly block here deals with annoying time/iter format
                            #data at the last column
                            _temp_end = line.find(':')
                            _i = 1
                            while line[_temp_end - _i] != ' ':
                                _i +=1
                            line = line[0:_temp_end-_i] + '\n'
                            
                            #add okay line to the cleaned text
                            cleanedText += line
                        except ValueError:
                            continue
                except IndexError:
                    continue
        
        return cleanedText

    def get_data(self,eof = True):

        cleaned_text = ''
        columns = []
        solution_text = _get_text_between_phrase_lines(self.file,
                                                        [self._SOL_START_PHRASE ,self._SOL_END_PHRASE],
                                                        include_pairs = True)

        eol = itertools.tee(re.finditer('\n',solution_text))
        eol1 = peekable(eol[0])
        eol2 = peekable(eol[1])
        columns = re.split('\s+',solution_text[0:next(eol1).start()].strip())[0:-1]

        while True:
            try:
                eol1.peek()
                eol2.peek()
                ct = self.parse_solution_text(solution_text,eol1,eol2)
                cleaned_text += ct
            except StopIteration:
                break
        
        return cleaned_text,columns

    def readdf(self,
                skiprows = [],
                nrows = [],
                eof = True,
                ) -> pd.DataFrame:

        """
        main reading of data frame occurs here which goes through four main phases: 
        (1) the text containing the residual information is located
        (2) the solution text is parsed according to the annoying format presented
            into digestable form -essentially space delimited rows
        (3) the text is converted to a numpy array - allowing for empty end rows
        (4) the numpy data frame is converted into a pandas dataframe using the columns
            gleaned from the np array converter

        """
        
        cleaned_text,columns = self.get_data(eof = eof)
        #hope that you can convert the text - deals with (or tries to) deal
        #with recorded data with inconsistent reporting width
        dat = _convert_delimited_text(cleaned_text,'\s+','\n',float,
                                      force_columns = True,empty_columns= None)
        
        #this can happen sometimes if the _convert_delimited_text runs into issues
        #and leaves things as a string, will try to convert effective here
        #the dataframe converter may be able to convert it if this fails
        try:
            index_dat = dat[:,0].astype(int)
        except (ValueError,TypeError):
            index_dat = dat[:,0].astype(float)
            index_dat = index_dat.astype(int)

        #we can run into issues forcing the columns if the solution terminates well before the
        #convergence conditions kick in- this can happen if there are differening convergence
        #checking start points - this will raise a valueerror due to differing lengths of
        #columns and data columns, so we will try and adjust for that
        try:
            self.df = pd.DataFrame(dat[:,1:],
                                index = pd.Series(index_dat,name = columns[0]),
                                columns = columns[1:],dtype = float)
        except ValueError:
            len_diff = len(columns) - dat.shape[1]
            self.df = pd.DataFrame(dat[:,1:],
                                   index = pd.Series(index_dat, name =columns[0]),
                                   columns = columns[1:-len_diff],dtype = float)

        #it could be the case that there are duplicate iteration numbers - because ansys re-prints
        #the previous iteration values if something changes so we have to remove these values
        self.df = self.df[~self.df.index.duplicated()]
        
        return self.df

    def read_data(self):
        
        self.read_params()
        self.readdf()

    def _get_status(self):
        """
        get the status of the solution file
        False - solution is not finished
        True - solution is finished
        
        the strategy here is to find all instances of the phrase:
        solve/iterate (or simply iterate) with an integer number after the phrase
        and ensure that the sum of these integers equals the length of the dataframe read

        BUGS 10.06.2021

        This is not reliably letting me know if the simulation is completed or not - there
        is some flaw in the logic here.
        """

        total = 1
        self.file.seek(0)
        txt = self.file.read()
        
        for p in self._ITERATE_PHRASES:
            rexp = re.finditer(p,txt)
            r,rexp = more_itertools.spy(rexp,n=1)
            if r:
                break
        
        for i,r in enumerate(rexp):
            line = txt[r.end():]
            total += int(line.partition(LINE_BREAK)[0].strip())
        
        if i == 1:
            total +=1

        self.file.seek(0)
        if self.df is None:
            self.readdf()
        
        if total == self.df.shape[0]:
            self.STATUS = True
        else:
            self.STATUS = False

        return self.STATUS
        
class ReportFilesOut(FluentFiles):

    def __init__(self,flist: list,
                      folder_names = [],
                     *args,**kwargs):

        super().__init__(flist,*args,**kwargs)
        self.component_class = ReportFileOut
        self._set_component_class(fluent_folders= folder_names)
    
    def readdf(self):
        self.load(convergedResult= True)
        for key,df in self.data.items():
            self.data[key] = df.squeeze()
        
        self.df = pd.DataFrame.from_dict(self.data,orient= 'index')
        return self.df
    
class SolutionFiles(FluentFiles): 

    def __init__(self,flist:list,
                      folder_names = [],
                      *args,**kwargs): 

        super().__init__(flist,*args,**kwargs)
        self.component_class = SolutionFile
        self._set_component_class(fluent_folders= folder_names)
        self.__input_parameters = dict.fromkeys(self.keys)

    @property
    def input_parameters(self):
        return self.__input_parameters
    
    @input_parameters.setter
    def input_parameters(self,ip):
        self.__input_parameters = ip
    
    def read_params(self):
        for key in self.keys:
            with self.__getitem__(key) as ffile:
                self.input_parameters[key] = ffile.read_params()
        
        return self.input_parameters
 
    def params_as_frame(self):
        _f = True
        for value in self.input_parameters.values(): 
            if value is not None:
                _f = False
                break
                
        if _f:
            self.read_params()
        
        df = pd.DataFrame.from_dict(self.input_parameters,orient = 'index')
        df.index.name = 'File'
        return df
        
#Representation of the "design point"
#folder from ANSYS work bench
#will attempt to find pairs of input/output based upon file extensions/console output files
#and build a pandas dataframe of the results upon loading
class DesignPoint:

    def __init__(self,path: str,                    
                 env = 'fluent-default',                
                 *args,
                 **kwargs
                ):

        super().__init__(*args,**kwargs)
        self.__fluent_settings = settings.from_env(env)

        self.filesys = DesignPointFolder(path)

    @property
    def settings(self):
        return self.__fluent_settings
    
    @property
    def X(self):
        return self.__X

    @X.setter
    def X(self,x):
        self.__X = x

    @property
    def Y(self):
        return self.__Y
    
    @Y.setter
    def Y(self,y):
        self.__Y = y

    
    def _load_cases(self,solution_path = None,output_source = '.out',input_source = '.trn'):

        """
        main parser for determining where to load data from
        """
        
        if output_source == '.out' and input_source == '.trn':
            return self._load_cases_from_report_file_and_solution_file(solution_path = solution_path)

    
    def _load_cases_from_report_file_and_solution_file(self, solution_path = None):

        """
        load output data from a .out file and input data from a .trn file looking where ANSYS 
        usually leaves them

        WONT load data if a both of the report files and the solution files do not exist, or if there is
        more than one of either file
        """    

        fluent_folders = self.filesys.get_fluent_folders()
        report_files = []
        solution_files = []
        for f in fluent_folders:
            rfiles = f.get_report_files()
            sfiles = f.get_solution_files()
            exists_condition = rfiles[0] is not None and sfiles[0] is not None
            distinguishable_condition = len(rfiles) == 1 and len(sfiles) == 1

            if exists_condition and distinguishable_condition:
                report_files.append(rfiles[0])
                solution_files.append(sfiles[0])
        
        rfiles = ReportFilesOut(report_files)
        sfiles = SolutionFiles(solution_files)
        X = sfiles.params_as_frame()
        Y = rfiles.readdf()

        return X,Y

    def load(self,solution_path = None, input_source = '.trn',output_source = '.out'):

        """
        Load the available inputs and outputs into two pandas DataFrames with
        
        X: nxm dataframe with n the number of cases in a design point and m the number of parameter inputs
        Y: nxp dataframe where p is the number of variable ouputs

        A number of available searches are available based on where ANSYS Workbench outputs variable reports
        """
        self.X,self.Y = self._load_cases(solution_path = solution_path)
        return self.X,self.Y

def main():
    pass

if __name__ == '__main__':
    main()