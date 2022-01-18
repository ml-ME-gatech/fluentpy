#third party imports
from io import StringIO
from multiprocessing.sharedctypes import Value
from typing import Iterable,Union
import more_itertools
import numpy as np
import pandas as pd
import re
from abc import ABC,abstractmethod
from itertools import islice
import itertools
from more_itertools import peekable
from pandas.errors import ParserError
from pathlib import WindowsPath,PosixPath
import sys

#package imports
from ._file_scan import _get_text_between_phrase_lines

__all__ = [
           'ReportFileOut',
           'SolutionFile',
           'ReportFilesOut',
           'SolutionFiles',
           'PostDataFile',
           'SphereSliceFile',
           'SurfacePointFile',
           'XYDataFile',
           'SurfaceIntegralFile'
           ]

"""
Creation:
Author(s): Michael Lanahan 
Date: 05.10.2021

Last Edit: 
Editor(s): Michael Lanahan
Date: 12.30.2021

Description
-----------
These are the work horse classes for reading, interpreting, and
interfacing with fluent output files. Classes are much much easier in this context
as they lend themselves to easily and concicsely representing file information
"""

class FluentFile(ABC):
    """
    Parameters
    -----------
    args and kwargs

    Description
    -----------

    base class for fluent files
    could be useful to add stuff on here later
    """

    LINE_BREAK = '\n'

    def __new__(cls,*args,**kwargs):

        """
        had some issues with class method instantion, python was getting
        confused about which fname to use
        """
        instance = super(FluentFile,cls).__new__(cls)
        instance.fname = args[0]

        return instance

    def __init__(self,fname: str,               #full path to folder name
                      read_length = False,      #read the length of the file, if file is huge we may not want to do this for performance issues.
                      case_name = None,         #option to provide the case name
                      *args,**kwargs):

        self.__fname = fname
        self.file = None
        self.length = None
        self.__df = None
        
        self.__case_name = case_name
        
        #if the file is very long may not want to do this if the information is not neccessaary
        if read_length:
            self._get_length()
        
        #Set up the pathlib here based on the system we are on - since this code 
        #will likely be used on both windows and posix systems need to make compatible with
        #both
        os_name = sys.platform
        if os_name == 'win32' or os_name == 'win64':
            self._Path = WindowsPath
        elif os_name == 'linux' or os_name == 'posix':
           self._Path = PosixPath
        else:
            raise ValueError('Cannot determine Path structure from platform: {}'.format(os_name))
                    
    #"official" string representation of an object
    def __repr__(self):
        return "File: {} \nCase: {}".format(self.fname,self.caseName)

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
        but sometimes it is neccessary to know the length of the file. Sets
        the buffer back to zero after get_length is called
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
        """
        the length of the file
        """
        return self.length
        
    @property
    def length(self):
        """
        the property of the file length. calls _get_length() if length is None
        so make sure that this is something you actually want to do
        """
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
    def fname(self):
        """
        file name of the fluent file, as a string
        """
        return self.__fname

    @fname.setter
    def fname(self,f):
        self.__fname = f
    
    @property
    def df(self):
        """
        most fluent output files admit some data that can be represented in a 
        tabular format convinient to store in a pandas data frame. The df property
        is meant to hold this data
        """
        return self.__df

    @df.setter
    def df(self,df):
        self.__df = df

    @abstractmethod
    def readdf(self):
        """
        each inherited file will require a method designed to read in the data
        frame
        """
        pass

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

    def _set_component_class(self):
        if self.component_class is None:
            raise NotImplementedError('Must set Class in subclasses of fluentFiles')
        
        for key in self.keys:
            self.__setitem__(key,self.component_class(str(key))) 
        
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
    def load(self,convergedResult = True):
        
        for key in self.keys:
            with self.__getitem__(key) as ffile:
                if convergedResult:
                    self.data[key] = ffile.readdf().iloc[-1]
                else:
                    self.data[key] = ffile.readdf().iloc[-1]
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
                    dat.append(ffile.readdf()[varname])
            except KeyError as ke:
                if ignore_missing:
                    dat.append(None)
                else:
                    raise KeyError(ke)
        
        data = pd.concat(dat,axis = 1)
        return data
    
class SurfaceFile(FluentFile):

    """
    Surface files are unique because they are implemented as both input and output files
    input - the input required to generated a surface file through the tui interface in fluent
    output - the output of the surface file generated through tui commands, containing decipherable data unique
             to the type of surface being created

    format - the output format is ascii

    Parameters
    ----------
    fname : str
            the name of the file as a string
    """
    SURFACE_CMD = 'surface'
    CREATE_SL_CMD = None
    EXIT_CMD = 'q'
    EXPORT_CMD = 'file/export/ascii'
    READ_JOURNAL_CMD = 'file/read-journal'
    OUTPUT_FILE_EXT = '.so'

    def __init__(self,fname) -> None:

        super().__init__(fname)

    def readdf(self,**kwargs) -> pd.DataFrame:
        """

        Parameters
        ----------
        **kwargs : dict
                keyword arguments for input into pandas pd.read_csv()
                function
        
        Returns
        -------
        df : pd.DataFrame 
                this will output as a table of values like:
                cellnumber,xcoordinate,y-coordinate,z-coordinate,var1,var2,....
                in the cellnumber column, the counting is local to the surface
                and will restart at 1 each time a new surface is defined
        """

        DEFAULTS = {'sep':',','header':0,'index_col':0}

        for kwd,value in DEFAULTS.items():
            if kwd not in kwargs:
                kwargs[kwd] = value

        try:
            self.df = pd.read_csv(self.fname,**kwargs)
            self.df.columns = [c.strip() for c in self.df.columns]
        except ParserError as pe:
            self.df = pd.read_csv(self.fname,error_bad_lines= False,**kwargs)
            self.df.columns = [c.strip() for c in self.df.columns]
        
        return self.df

    def get_surface_list(self) -> list:
        """
        create a list of dataframes where each entry in the list
        is a dataframe containing the values of the variables
        at the surface

        Returns
        -------
        surface_list : list
                a list of pandas DataFrames containing the values of the
                field variables at the surface
        """

        if self.df is None:
            self.readdf()
        
        idxs = np.where(self.df.index == 1)[0]
        surface_list = []
        try:
            for i in range(idxs.shape[0]-1):
                surface_list.append(self.df.iloc[idxs[i]:idxs[i+1]])
        
            surface_list.append(self.df.iloc[idxs[-1]:])
        
            return surface_list
        except IndexError as ie:
            raise TypeError('Index error likely caused because the dataframe \
                was not read correctly: \n {} \n {} '.format(self.df,str(ie)))

    def _parse_from_table_input(array: Union[pd.DataFrame,np.ndarray],
                                R: Union[np.ndarray,float]) -> pd.DataFrame:

        """
        ensure that the input data has the following form:
        array is n x 3 where n is the number of points
        if array is a data frame the columns MUST be x,y,z
        if provideed, R must be a 1-D array with the same length as array
        """

        if array.ndim != 2:
            raise ValueError('Array must be two-dimensional')
        
        if array.shape[1] != 3 and array.shape[1] != 2 and array.shape[1]/2.0 != 2.0 and array.shape[1]/2.0 != 3.0:
            raise ValueError('table input only supported for 2D or 3D input i.e. x,y,z, listed beggining and end points i.e. (x0,x1),(y0,y1),(z0,z1)')
        
        if isinstance(array,np.ndarray):            
            
            if array.shape[1] > 3:
                try:
                    df = pd.DataFrame(array,columns  = ['x0','x1','y0','y1','z0','z1'])
                except ValueError:
                    df = pd.DataFrame(array,columns = ['x0','x1','y0','y1'])
            else:
                try:
                    df = pd.DataFrame(array,columns = ['x','y','z'])
                except ValueError:
                    df = pd.DataFrame(array,columns = ['x','y'])
        
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
        text = self.READ_JOURNAL_CMD + self.LINE_BREAK
        text += self.fname + self.LINE_BREAK
        text += ',' + self.LINE_BREAK
        return text

    def __str__(self):
        return self.format_text()
    
    def __call__(self):
        return self.format_text()
    
    @staticmethod
    def _row_to_text(line_break: str,
                     row: np.ndarray) -> str:

        txt = ''
        for i in range(row.shape[0]):
            txt += str(row[i]) + line_break
        
        return txt

    @classmethod
    def _create_fluent_input_from_table(cls, df: Union[pd.DataFrame, np.ndarray],
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
                                           create_surfaces = True,
                                           cell_centered = True) -> None:

        """
        Parameters
        ----------
        df : pd.DataFrame | np.ndarray
                n x 3 pandas DataFrame or numpy ndarray
        
        R : pd.DataFrame | np.ndarray
                n x 1 or 1-D pandas DataFrame or numpy npdarray containing the radius
                of the spheres of the SphereSlice Surfaces

        file_name : str
                the name of the file to write to as a string
        
        export_variables : list
                a list of the field variables to export from fluent\
                    i.e. "temperature","density". 
        

        from the input dataframe "df" creates the appropriate fluent input
        journal file with name "file_name" that once run in fluent
        will produce data containing the variables in "export_variables"
        for each of the point surfaces
        """
        text,names = cls._create_fluent_input_from_table(df,R,prefix = prefix,seperator = seperator,file_name = file_name)
        _txt =  cls.LINE_BREAK + cls._format_export_command(names,export_variables,file_name + cls.OUTPUT_FILE_EXT,cell_centered = cell_centered)
        if create_surfaces:
            text += _txt
        else:
            text = _txt
        
        with open(file_name,'w') as file:
            file.write(text)
        
        return cls(file_name)
    
    @classmethod
    def _format_export_command(cls,
                              names: list,
                              field_variables: list,
                              file_name: str,
                              cell_centered = True) -> None:

        txt = cls.EXPORT_CMD + cls.LINE_BREAK
        txt += file_name + cls.LINE_BREAK
        #format surfaces for output
        for name in names:
            txt += name + cls.LINE_BREAK
        
        txt += ',' + cls.LINE_BREAK                  #end of names
        txt += 'yes' + cls.LINE_BREAK                #give commma delimiter
        
        #format variables for output
        if isinstance(field_variables,str):
            field_variables = [field_variables]
        elif isinstance(field_variables,list):
            pass
        else:
            raise ValueError('field variables must be designated by strings or list of strings')

        for fv in field_variables:
            if not isinstance(fv,str):
                raise ValueError('field variables must be designated by strings')
            
            txt += fv + cls.LINE_BREAK
        
        txt += 'q' + cls.LINE_BREAK
        if cell_centered:
            txt += 'yes' + cls.LINE_BREAK               #yes to cell-centered
        else:
            txt += 'no' + cls.LINE_BREAK

        return txt

class LineSurfaceFile(SurfaceFile):

    """ 
    LineSurfaceFile

    A specific surface file format type. Creates and reads line surface files

    Parameters
    ----------
    fname : str
            the file namea as a string
    """

    CREATE_SL_CMD = 'line-surface'

    def __init__(self,fname) -> None:

        super().__init__(fname)


    @classmethod
    def _create_fluent_input_from_table(cls, df: Union[pd.DataFrame, np.ndarray],
                                            R,
                                            prefix = 'line',
                                            seperator = '-',
                                            file_name = None) -> None:
        """
        Called by write_fluent_input_from_table.
        convert a pandas DataFrame to a series of TUI commands to create the
        lines listed
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
                                           prefix = 'line',
                                           seperator = '-',
                                           create_surfaces = True,
                                           cell_centered = True) -> None:


        return super().write_fluent_input_from_table(df,None,file_name,export_variables,
        prefix = prefix,seperator=  seperator,create_surfaces = create_surfaces, cell_centered = cell_centered)

class SphereSliceFile(SurfaceFile):
    """
    SphereSliceFile

    A specific surface file format type. Creates and reads sphere slices

    Parameters
    ----------
    fname : str
            the file name as a string
    
    Examples
    --------
    1. making tui input
    
    .. code-block:: python
        
        from fluentio.classes import SphereSliceFile

        R = np.array([1,2,3])                       #three spheres radiusus of 1,2,3 [m] 
        X = np.array([[1,1,1],[2,2,2],[1,2,3]])     #locations of the three spheres in cartesian coordinates [m] \\
        SphereSliceFile.write_fluent_input_from_table(X,R,"test.ssf",['temperature'])
    
    creates a sphere slice file input with the specified radiuses and locations, located at the "test.ssf" file
    exporting the field variable "temperature"

    2. reading fluent output
    
    .. code-block:: python
        
        from fluentio.classes import SphereSliceFile
        import numpy as np

        with SphereSliceFile('test.ssf.so') as ssf:
            df = ssf.readdf()
            sdf_list = ssf.get_surface_list()
            mean_df = ssf.get_sphere_surface_data(np.mean)
    
        for df in sdf_list:
            print(df)
    """
    
    CREATE_SL_CMD = 'sphere-slice'

    def __init__(self,fname) -> None:

        super().__init__(fname)

    def readdf(self) -> pd.DataFrame:
        return super().readdf()

    def get_sphere_surface_data(self,
                                statistic: callable,
                                dimension = 3) -> pd.DataFrame:
        """
        Parameters
        ----------
        statistic : callable
                i.e. np.mean,np.max, ect... MUST have the signature 
                >> statistic(array,axis = 0)
        dimension : int
                keyword argument showing the dimension of the data
        
        Returns
        -------
        df : pd.DataFrame
                a dataframe indexed by the index of the sphere with the statistic
                applied to all of the data within that sphere
        
        convinience function for applying a statistic to the data
        of the spheres and returning the result as a dataframe with each
        row the result of that statistic applied to each variable in the dataframe
        the center of the sphere is taken as the mean
        """
        
        EXCLUDE_COLS = ['x-coordinate','y-coordinate','z-coordinate','cellnumber']
        sl = self.get_surface_list()
        data = np.zeros([len(sl),sl[0].shape[1]])
        field_variables = [column for column in sl[0].columns if 
                           column not in EXCLUDE_COLS]
        
        for i,df in enumerate(sl):
            if dimension == 3:
                data[i,0:dimension] = np.mean(df[['x-coordinate','y-coordinate','z-coordinate']],axis = 0)
            elif dimension == 2:
                try:
                    data[i,0:dimension] = np.mean(df[['x-coordinate','y-coordinate']],axis = 0)
                except KeyError:
                    data[i,0:dimension] = np.mean(df[['x-coordinate','z-coordinate']],axis = 0)
                except KeyError:
                    data[i,0:dimension] = np.mean(df[['y-coordinate','z-coordinate']],axis = 0)

            for k,var in enumerate(field_variables): 
                data[i,dimension + k] = statistic(df[var],axis = 0)
        
        return pd.DataFrame(data,columns = sl[0].columns)

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

    """
    A specific example of a SurfaceFile used for creating and reading point surfaces

    Parameters
    ----------
    fname : str
            the name of the file as a string
    
    Examples
    --------
    1. creating tui input

    .. code-block:: python

        from fluentio.classes import SurfacePointFile

        X = np.array([[1,1,1],[2,2,2],[1,2,3]])     #locations of the three spheres in cartesian coordinates [m]
        SurfacePointFile.write_fluent_input_from_table(X,"test.spf",['temperature'])

    creates a point surface file file input with the specified locations, located at the "test.spf" file
    exporting the field variable "temperature"

    2. reading fluent output

    .. code-block:: python

        from fluentio.classes import SurfacePointFile

        with SurfacePointFile('test.spf.so') as spf:
            #read in all of the data as one dataframe
            df = spf.readdf()

            #read in data as a list of dataframes for each surface
            sdf_list = spf.get_surface_list()
        
        #print dataframe for each surface
        for df in sdf_list:
            print(df)
    
    """

    CREATE_SL_CMD = 'point-surface'

    def __init__(self,fname) -> None:

        super().__init__(fname)

    def readdf(self) -> pd.DataFrame:
        return super().readdf()

    @classmethod
    def _create_fluent_input_from_table(cls, df: Union[pd.DataFrame, np.ndarray],
                                            R,
                                            prefix = 'point',
                                            seperator = '-',
                                            file_name = None) -> None:
        """
        Called by write_fluent_input_from_table.
        convert a pandas DataFrame to a series of TUI commands to create the
        points listed in the DataFrame
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
    
    def get_point_surface_data(self) -> pd.DataFrame:
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
    """
    class for representing the XYDataFile - data files that are exported from
    XY Plots in Fluent. Handles the case
    of multiple surface/volume data export by representing the data as either:
    (1) a single data frame with concated data 
    (2) a dictionary of data frames that can be iteratated over. The keys of the dictionary\
        are determined from the names of the XY Surfaces in the output file

    Parameters
    -----------
    fname : str 
            the name of the file as a string
    
    Examples
    --------
    .. code-block:: python
        
        #asssuming you have a file in XYFile format called "sample.dat"
        my_file = 'sample.dat'
        with XYDataFile(my_file) as xyf:
            df = xyf.readdf()
    
        print(df)

        for surface_name in xyf.keys():
            print(xyf[surface_name])

    """
    DATA_DELIM = '((xy/key/label'
    COLUMN_DELIM = '\t'
    SERIES_SPACING = 2
    DATA_END_LINE = ')'

    def __init__(self, fname: str):

        super().__init__(fname)
        self.__data_names = {}

    @property
    def data_names(self):
        return self.__data_names

    @data_names.setter
    def data_names(self,dn):
        self.__data_names = dn

    def _parse_text_block(self,txt_block: str) -> np.ndarray:
        
        return pd.read_csv(StringIO(txt_block),
                          sep = self.COLUMN_DELIM,
                          dtype= float, header = None).to_numpy()
            
    def _deliminate_data_file(self) -> pd.DataFrame:
        """
        main parsing logic for reading the data file
        here. Iterates through the whole data file, and partitions
        the various components based on pre-defined logic
        """
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

    def readdf(self) -> pd.DataFrame:
        """
        Returns
        -------
        df : pandas.DataFrame
                returns all of the XY data concatenated as a single DataFrame
        """
        return self._deliminate_data_file()
    
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

    """"
    class for representing files exported from CFD Post - Handles the case
    of multiple surface/volume data export by representing the data as either:
    (1) a single data frame with concatenated data 
    (2) a dictionary of data frames that can be iteratated over

    handles multiple variables exported on each surface by using dataframes
    and adding columns to each member of the dictionary

    Parameters
    --------------
    fname : str
             the name of the file as a string

    Examples
    --------
    .. code-block:: python

        my_file = 'sample.dat'
        with PostDataFile(my_file) as pdf:
            df = pdf.readdf()
        
        print(df)

        for surface_name in pdf.keys():
            print(pdf[surface_name])


    """

    DATA_DELIM = '[Name]'
    DATA_START = '[Data]'
    COLUMN_DELIM = ','

    def __init__(self,fname):

        super().__init__(fname)
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

        return columns, pd.read_csv(StringIO(txt_block), 
                                     sep = self.COLUMN_DELIM,
                                     dtype = float,header = None).to_numpy()
        
    def _deliminate_consistent_data_file(self):

        """
        main parsing logic here. Will scan the whole file looking
        for pre-defined breaks in the file, and mark the lines 
        at which those breaks occur. Records all of the deliminitated
        data into a single dataframe, that can be seperated based upon
        the retained delimination markings.
        """
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
    
    def readdf(self) -> pd.DataFrame:
        """
        Returns
        -------
        df : pd.DataFrame 
                all of the data contained in the XY Data File
                concatenate as a DataFrame. To seperate data by surface name
                access class using keys.
        """
        self._deliminate_consistent_data_file()
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

class ReportFileOut(FluentFile):

    """
    Class for representing the report file with .out extension output
    by fluent

    Parameters
    -------------
    fname : str 
            the string of the file name
    
    
    Examples
    -------------
    
    .. code-block:: python

        my_out_file = 'test.out'
        with open ReportFileOut(my_out_file) as rfile:
            df = rfile.readdf()

        print(df)

    """
    _STR_REMOVE = [')','"','\n','(']
    _HEADER_LINE = 2
    _DATA_START = 3

    def __init__(self,fname):

        super().__init__(fname)

    #get headers in a custom fashion because .out files are annoying
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
    def _get_data_frame(self,**kwargs):

        if 'skiprows' not in kwargs:
            skiprows = []
        else:
            skiprows = kwargs.pop('skiprows')
            
        
        #parse skip rows and such key words
        skiprows = self._parse_skip_rows(skiprows)
        #reset file
        self.file.seek(0)
        return pd.read_csv(self.file,header = None,names = self._get_headers(),
                            index_col = 0,sep = ' ',skiprows = skiprows,**kwargs)
    
    def readdf(self,**kwargs) -> pd.DataFrame:
        
        """
        Parameters
        ----------
        **kwargs : dict
                key word arguments for pandas read_csv() function

        Returns
        -------
        df : pandas.DataFrame 
                containing the report file contents with
                headers named appropriately. The index is the iteration number supplied
                in the file
        """

        self.df = self._get_data_frame(**kwargs)
        return self.df

class SolutionFile(FluentFile):
    """
    Class for representing the "solution" files in Fleunt i.e. transcripts
    usuaully output with a .trn extension. Useful for examining convergence of a solution

    Parameters
    ------------
    fname : str
            the file name of the solution file

    Examples
    ---------

    .. code-block:: python

        my_file = 'solution.trn'
        with SolutionFile(my_file) as sfile:
            df = sfile.readdf()
        
        print(df)

    BUGS 11.16.2021 - STATUS Property is not being determined properly
    The STATUS property of the SolutionFile indicates if the solution has 
    completed or not, determined by the logic in _get_status()
    False - solution is not finished
    True - solution is finished
    """

    _PARAM_PHRASE = r'WB->Fluent:Parameter name:'
    _SOL_START_PHRASE = r'  iter  '
    _SOL_END_PHRASE = r'Writing "| gzip -2cf >'
    _ITERATE_PHRASES = ['> solve/iterate',
                       'solve/iterate',
                       '> iterate',
                       'iterate']
    _SKIP_CHARS = ['\n','!']
    _END_CHARS = ['>']
    
    def __init__(self,fname):

        super().__init__(fname)
        self.__STATUS = None
    
    @property
    def STATUS(self):
        if self.__STATUS is None:
            self._get_status()
        
        return self.__STATUS
    
    @STATUS.setter
    def STATUS(self,s):
        self.__STATUS = s
    
    def _parse_solution_text(self,solution_text: str,
                                  eol1: Iterable,
                                  eol2: Iterable):
        
        """
        parse the solution folder file in post into a pandas dataframe with the
        columns being the various values tracked over the course of the solver
        and the rows the iterations.

        ** This function is pretty slow, considering that every line must be iterated
        over in python, and each character of each line must be examined in python. However,
        SolutionFiles tend to be on the order of 1e3-1e4 lines and kb of data, so this is probably
        not a performance bottleneck. In the future, it could be useful to write this parsing procedure 
        in cython but this is not a priority at the moment 12.28.2021. 
        """

        if solution_text == '':
            return solution_text
        else:
            cleanedText = ''
            for e2,e1 in zip(eol2,eol1):
                line = solution_text[e2.start():e1.start()+1].strip() +'\n'
                try:
                    #check to see if we should consider this line
                    if line[0] in self._SKIP_CHARS or 'Solution' in line:
                        continue
                    #check to see if this line indicates an end to the data we are interested in
                    elif line[0] in self._END_CHARS:
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

    def _get_data(self):
        """
        iteratively retrieve data, examining all of the iteration
        blocks found in the file
        """
        cleaned_text = ''
        columns = []
        solution_text = _get_text_between_phrase_lines(self.file,
                                                        [self._SOL_START_PHRASE ,self._SOL_END_PHRASE],
                                                        include_pairs = True)

        eol = itertools.tee(re.finditer('\n',solution_text))
        eol1 = peekable(eol[0])
        eol2 = peekable(eol[1])
        try:
            columns = re.split('\s+',solution_text[0:next(eol1).start()].strip())[0:-1]
        except StopIteration:
            raise AttributeError('no columns found in file - ensure that the file with name: {} is a solution file'.format(self.fname))

        while True:
            try:
                eol1.peek()
                eol2.peek()
                ct = self._parse_solution_text(solution_text,eol1,eol2)
                cleaned_text += ct
            except StopIteration:
                break
        
        return cleaned_text,columns

    def readdf(self) -> pd.DataFrame:
        """
        main reading of data frame occurs here which goes through four main phases: 
        1. the text containing the residual information is located
        2. the solution text is parsed according to the annoying format presented\
            into digestable form - essentially space delimited rows
        3. the text is converted to a numpy array - allowing for empty end rows
        4. the numpy data frame is converted into a pandas dataframe using the columns\
            gleaned from the np array converter
        
        Returns
        -------
        df : pandas.DataFrame
                returns the solution file information as a DataFrame. If information
                is missing from any column, this is filled with nan.
        """
        
        cleaned_text,columns = self._get_data()
        array = pd.read_csv(StringIO(cleaned_text), sep = '\s+',
                          dtype = float, header = None).to_numpy()
        
        #the index will be the first column of the array
        index_dat = array[:,0].astype(int)

        #we can run into issues forcing the columns if the solution terminates well before the
        #convergence conditions kick in - this can happen if there are differening convergence
        #checking start points - this will raise a ValueError due to differing lengths of
        #columns and data columns, so we will try and adjust for that by first assuming the convergence
        #conditions are applied, and then next assuming they do not exist and only returning the
        #data that excludes the convergence conditions
        try:
            self.df = pd.DataFrame(array[:,1:],
                                index = pd.Series(index_dat,name = columns[0]),
                                columns = columns[1:],dtype = float)
        except ValueError:
            len_diff = len(columns) - array.shape[1]
            self.df = pd.DataFrame(array[:,1:],
                                   index = pd.Series(index_dat, name =columns[0]),
                                   columns = columns[1:-len_diff],dtype = float)

        #it could be the case that there are duplicate iteration numbers - because ANSYS re-prints
        #the previous iteration values if something changes so we have to remove these values
        self.df = self.df[~self.df.index.duplicated()]
        
        return self.df

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
            total += int(line.partition(self.LINE_BREAK)[0].strip())
        
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
                     *args,**kwargs):

        super().__init__(flist,*args,**kwargs)
        self.component_class = ReportFileOut
        self._set_component_class()
    
    def readdf(self) -> pd.DataFrame:
        self.load(convergedResult= True)
        for key,df in self.data.items():
            self.data[key] = df.squeeze()
        
        self.df = pd.DataFrame.from_dict(self.data,orient= 'index')
        return self.df
    
class SolutionFiles(FluentFiles): 

    def __init__(self,flist:list,
                      *args,**kwargs): 

        super().__init__(flist,*args,**kwargs)
        self.component_class = SolutionFile
        self._set_component_class()
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

class SurfaceIntegralFile(FluentFile):
    """
    SurfaceIntegralFile

    class representation of the file created by a surface integral. This typically 
    contains a single number as the surface integral is usually approximated as a reimann sum
    representation with some weight depending on the type of integral

    This does not really lend itself to a dataframe representation, and a dictionary is actually
    more useful, so the data is represented in that manner. If multiple surface integrals are contained within
    the file, this is supported by making the value and boundary fields list the same length as the number
    of surface integrals
    """
    def __init__(self,file: str):
        
        self.attributes = {'type':None,
                           'name':None,
                           'unit':None,
                           'value':[],
                           'boundary': [],
                          }
        
        super().__init__(file)
        self.path = self._Path(file)
    
    def _parse_txt(self,lines: list) -> None:
        """
        parse the text from the surface integrals file (native format from fluent)
        into attributes descibed by the "attributes" dictionary property. 

        configured to read multiple surfaces but not multiple variables (is this possible?)
        """
        #this first line here reads the header information on the file
        try:
            self.attributes['type'] =  lines[2].strip()
            self.attributes['name'],self.attributes['unit'] = self._space_delimited_line_split(lines[3])
            for i in range(5,len(lines)):
                try:
                    boundary,value = self._space_delimited_line_split(lines[i])
                    if boundary == 'Net':
                        self.attributes['boundary'].append(boundary)
                        self.attributes['value'].append(float(value))
                        break
                    elif '----' in boundary and '----' in value:
                        pass
                    else:
                        self.attributes['boundary'].append(boundary)
                        self.attributes['value'].append(float(value))
                except ValueError:
                    pass
        except IndexError:
            pass

    @staticmethod
    def _space_delimited_line_split(line: str) -> list:
        #convinience function for parsing specific kinds of text
        _line = line.strip()
        items = [i for i in _line.split('  ') if i != '']
        return items

    def read(self) -> dict:
        """
        read a surface integral file
        """
        with open(str(self.path.resolve()),'r') as file:
            txt = file.readlines()
            self._parse_txt(txt)
        
        return self.attributes

    def readdf(self) -> pd.DataFrame:
        return super().readdf()
