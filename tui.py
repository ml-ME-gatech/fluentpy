#native imports
from abc import ABC,abstractmethod
import os
from typing import Hashable, OrderedDict, Union, List
import os
import subprocess
import numpy as np 
import sys
from pathlib import PosixPath, PurePath,WindowsPath
import shutil
import re
import string
import random 


#package imports
from .disk import SerializableClass
from .util import _surface_construction_arg_validator,get_fluent_path
from .fluentio import SurfaceIntegralFile

__all__ = [
           'Initializer',
           'ScalarRelaxation',
           'EquationRelaxation',
           'NISTRealGas',
           'Discritization',
           'CaseReader',
           'CaseMeshReplaceReader',
           'CaseDataReader',
           'FluentEngine',
           'BatchCaseReader',
           'DataWriter',
           'CaseWriter',
           'Solver_Iterator',
           'Solver',
           'ConvergenceConditions',
           'FluentCase',
           'StandardKOmegaSpecification',
           'StandardKEpsilonSpecification',
           'ViscousModelModification',
           'SolidCellZone',
           'UDF',
           'WallBoundaryCondition',
           'MassFlowInlet',
           'PressureOutlet',
           'VelocityInlet',
           'SurfaceIntegrals',
           'FluentJournal'
           ]

"""
Author: Michael Lanahan
Date Created: 08.05.2021
Last Edit: 01.04.2021

The purpose of this file is provide python class interfaces to TUI commands in 
the command line or batch mode fluent software.
"""

class TUIBase:

    LINE_BREAK = '\n'
    EXIT_CHAR = 'q' + LINE_BREAK
    EXIT_STATEMENT = 'exit'
    ALLOWABLE_PRECISION_SPEC = ['3ddp','2ddp']

    def __init__(self,*args,
                precision_specification = '3ddp',
                **kwargs):
        
        self.precision_specification = precision_specification
        self.__tui_prefix = None

    @property
    def tui_prefix(self):
        if self.__tui_prefix is None:
            self.__tui_prefix = '/'.join(__name__.split('.')[1:])

        return self.__tui_prefix

    def generate_random_file_name(self) -> str:

        my_file_name = self.FILE_PREFIX + '_'
        for _ in range(self.random_character_length):
            my_file_name += random.choice(string.ascii_letters)
        
        return my_file_name + self.ext
    
class TUIVersion(TUIBase):

    """
    Adds the ability to set the TUI version
    
    Parameters
    ----------
    version: str
            version of the tui, a string or something that can be
            type-cast to a string
    
    Examples
    -------

    .. code-block:: python

        tui_version = TUIVersion('19.3.12')
        print(tui_version)

        > file/set-tui-version/19.3.12
    
    """
    _prefix = 'file/set-tui-version/{}'

    def __init__(self,version: str):

        self.__version = version
    
    @property
    def version(self) -> str:
        return str(self.__version)
    
    def __str__(self):
        return self._prefix.fromat(self.version) 

class Initializer(TUIBase):

    """
    representation of the initializer object in Fluent
    
    Parameters
    ----------
    init_type: str 
            one of either "hyb-initialization" or "initialize-flow". creates
            the initialization for the solver
    
    Examples
    --------
    .. code-block:: python

            initializer = Initializer()
            print(initializer)
            > "solve/initialize/hyb-initialization"
    """
    
    _prefix = 'solve/initialize/'
    ALLOWABLE_INITIALIZER_TYPES = ['hyb-initialization','initialize-flow']
    def __init__(self,init_type = 'hyb-initialization'):

        super().__init__()

        if init_type not in self.ALLOWABLE_INITIALIZER_TYPES:
            raise ValueError('initializer must be one of: {}'.format(self.ALLOWABLE_INITIALIZER_TYPES))
        
        self.__init_type = init_type

    @property
    def init_type(self):
        return self.__init_type
    
    def __str__(self):
        return self._prefix + self.init_type

class Relaxation(ABC,TUIBase):

    def __init__(self,variable: str,
                      value: float) -> None:
        
        if isinstance(variable,str) and (isinstance(value,int) or isinstance(value,float)):
            self._check_allowable_variables(variable,value)
            variable = [variable]
            value = [value]

        elif isinstance(variable,list) and isinstance(value,list):
            if len(variable) != len(value):
                raise AttributeError('lists of variables and values must be the same length')
            else:
                for var,val in zip(variable,value):
                    self._check_allowable_variables(var,val)

        else:
            raise ValueError('cannot make relaxation from variable: {} and value: {}'.format(variable,value))
                
        self.__var_value_dict = dict(zip(variable,value))

    @abstractmethod
    def _check_allowable_variables(self,variable: str,
                                    value: float):
        pass

    @classmethod
    def from_dict(cls,
                  input_dict: dict):

        vars = []
        vals = []
        for var,val in input_dict.items():
            vars.append(var)
            vals.append(val)
        
        return cls(vars,vals)

    @property
    def var_value_dict(self):
        return self.__var_value_dict
    
    @var_value_dict.setter
    def var_value_dict(self,vvd):
        self.__var_value_dict = vvd

    def format_relaxation(self):
        txt = self._prefix + self.LINE_BREAK
        for variable,value in self.var_value_dict.items():
            txt += str(variable) + self.LINE_BREAK
            txt += str(value) + self.LINE_BREAK
        
        txt += self.EXIT_CHAR + self.EXIT_CHAR + self.EXIT_CHAR
        return txt
    
    def __str__(self):
        return self.format_relaxation()

class ScalarRelaxation(Relaxation):
    """
    Representation of relaxing scalars in Fluent 

    Parameters
    ----------
    variable : str | list
            either a string or a list of strings designating the variables to be relaxed
    
    value : float | list
            the value of the relaxation, or a list of values between 0 and 1

    Examples
    --------

    .. code-block:: python

        sr = ScalarRelaxation('temperature',0.5)    #relax temperature to 0.5
        print(sr)
        > solve/set/under-relaxation
        > temperature
        > 0.5
        > q
        > q
        > q

    .. code-block:: python 
    
        sr = ScalarRelaxation(['temperature','epsilon'],[0.6,0.3])  #relax temperature and epsilon
        print(sr)
        > solve/set/under-relaxation
        > temperature
        > 0.6
        > epsilon
        > 0.3
        > q
        > q
        > q
    
    """
    
    ALLOWABLE_VARIABLE_RELAXATION = ['body-force','epsilon','temperature','density', 'k', 'turb-viscosity']
    _prefix = 'solve/set/under-relaxation'

    def __init__(self,variable: str,
                      value: float):

        super().__init__(variable,value)

    def _check_allowable_variables(self,variable: str,
                                    value: float) -> None:
                    
        if variable in self.ALLOWABLE_VARIABLE_RELAXATION:        
            if value > 1 or value < 0:
                raise ValueError('Value must be between 0 and 1, not {}'.format(value))
        
        else:
            raise ValueError('{} not an allowable variable for relaxation'.format(variable))

class EquationRelaxation(Relaxation):

    """
    class for allowing the adjustment of relaxation factors
    to aid in the convergence of difficult solutions
    This treats explicitly the equation relaxations and adjustment of the
    courant number

    Parameters
    ----------
    variable : str | list
            either a string or a list of strings designating the variables to be relaxed. 
            Must be one of (1) courant number (2) momentum (3) pressure
    value : str | list
            momentum and pressure must be in [0,1] while courant number must be greater than 0
    
    Examples
    --------

    .. code-block:: python 

        er = EquationRelaxation(['courant number','momentum'],[500,0.6])
        print(er)

        > solve/set/p-v-controls
        > 500
        > 0.6
        > 0.75
        > q
        > q
        > q
    """

    ALLOWABLE_RELAXATION = {'courant number':200,
                            'momentum':0.75,
                            'pressure':0.75}

    _prefix = 'solve/set/p-v-controls'

    def __init__(self,variable: str,
                      value: float):

        super().__init__(variable,value)

        #unlike the scalar relaxation, the prompt requires all three
        #relaxation inputs regardless - we will provide the defaults if none
        #are provided
        for key,value in self.ALLOWABLE_RELAXATION.items():
            if key not in self.var_value_dict:
                self.var_value_dict[key] = value

        #this needs to be in the correct order
        self.var_value_dict = OrderedDict((k,self.var_value_dict[k]) for 
                                            k in self.ALLOWABLE_RELAXATION.keys())
        
    def _check_allowable_variables(self,variable: str,
                                   value: float) -> None:
        
        if variable in self.ALLOWABLE_RELAXATION:
            if value == 'default':
                value = self.ALLOWABLE_RELAXATION[variable]
            
            if variable == 'momentum' or variable == 'pressure':
                if value > 1 or value < 0:
                    raise ValueError('Value must be between 0 and 1, not {}'.format(value))
        else:
            raise ValueError('{} not an allowable variable for relaxation'.format(variable))
    
    def format_relaxation(self):
        txt = self._prefix + self.LINE_BREAK
        for _,value in self.var_value_dict.items():
            txt += str(value) + self.LINE_BREAK
        
        txt += self.EXIT_CHAR + self.EXIT_CHAR + self.EXIT_CHAR 
        return txt
        
class NISTRealGas(TUIBase):

    """
    class for setting up a real gas model for fluent. This is required if 
    we want to shift from interpolated/constant properties in fluent to 
    NIST real gas models after a few iterations - you may want to do this 
    because NIST real gas models can make convergence very difficult/
    can error fluent out if the solutions are very outside of the reccomended
    range of the correlation used. 

    ** this will check to make sure that the fluid supplied is allowable within the
    fluent database so that this doesn't cause errors at runtime

    Parameters
    ----------
    gas : str 
            the name of the gas in the NIST real gas library

    Examples
    --------

    .. code-block:: python 

        nrg = NISTRealGas('co2')
        print(nrg)
        > /define/user-defined/real-gas-models/nist-real-gas-model
        > yes
        > co2.fld
        > no
    """

    _prefix = '/define/user-defined/real-gas-models/nist-real-gas-model'
    
    def __init__(self,gas: str):
        lib = self._read_lib()
        if '.fld' not in gas:
            gas += '.fld'
        
        if gas not in lib:
            raise FileExistsError('Gas property: {} not available in the NIST Real Gas Library'.format(gas))
        
        self.__gas = gas

    @property
    def gas(self):
        return self.__gas

    def _format_real_gas(self):

        txt = self._prefix + self.LINE_BREAK
        txt += 'yes' + self.LINE_BREAK
        txt += self.gas + self.LINE_BREAK
        txt += 'no' + self.LINE_BREAK
        return txt

    def __str__(self):
        return self._format_real_gas()

    def _read_lib(self):
        """
        reads in the list of fluids taken from fluent - or rather the real 
        gas models taken from fluent. This is to check
        the supplied fluid again. 

        This is very computationally inefficient practice to do this parsing everytime
        but I am lazy and because this function shoud not be called a bunch of times
        it should be fine.
        """

        path = os.path.split(__file__)[0]
        lib_name = os.path.join(path,'dat\\nist_real_gas_lib')
        with open(lib_name,'r') as file:
            string = file.read()
        
        lines = string.split(self.LINE_BREAK)
        flds = []
        for line in lines:
            fld = [f.strip() for f in line.split(' ')]
            flds += fld
        
        return flds

class Discritization(TUIBase):

    """
    class for changing discritization schemes. This can be useful if you are
    having issues with convergence of the solution i.e. starting out at first order
    and working to second order/higher orders. 

    Parameters
    ----------
    schemes : 'all' | str | list
            one of "all" a string, or a list of strings. if "all" is selected,
            all discritization schemes are set to the order supplied. If a string or a
            list of strings is supplied, must be one of "density", "epsilon", 'k",'mom',
            'pressure', 'temperature'.

    orders : str | list
            string or list of strings designated the orders of the schemes. Can accomodate 
            all differencing scheme names from Fluent i.e. "Second Order Upwind"
    
    Examples
    --------
    
    .. code-block:: python 

        disc = Discritization(schemes = ['density','pressure'],
            orders = ['Second Order Upwind','First Order Upwind']) 
        print(disc) 
        > /solve/set/discretization-scheme
        > density
        > 1
        > pressure
        > 11
        > q
        > q
        > q
    
    """

    _prefix = '/solve/set/discretization-scheme'
    pmap = {'Second Order Upwind':'Second Order',
            'First Order Upwind':'Linear'}
    ALLOWABLE_DISCRITIZATION_SCHEMES = ['density','epsilon','k','mom','pressure','temperature']
    ALLOWABLE_DISCRITIZATION_ORDERS = {'First Order Upwind':0,
                                       'Second Order Upwind':1,
                                       'Power Law': 2,
                                       'Central Differencing':3,
                                       'QUICK':4,
                                       'Third Order MUSCL':5,
                                       'Standard':10,
                                       'Linear':11,
                                       'Second Order':12,
                                       'Body Force Weighted':13,
                                       'PRESTO!': 14,
                                       'Continuity Based':15,
                                       'SIMPLE':20,
                                       'SIMPLEC':21,
                                       'PISO':22}

    def __init__(self,schemes = 'all',orders = None):

        if schemes == 'all':
            self.__schemes = self.ALLOWABLE_DISCRITIZATION_SCHEMES
        else:
            if not isinstance(schemes,list):
                schemes = [schemes]

            for scheme in schemes:
                if scheme not in self.ALLOWABLE_DISCRITIZATION_SCHEMES:
                    raise ValueError('No discritization scheme for field variable: {}'.format(scheme))

            self.__schemes = schemes
        
        if orders is None:
            self.__orders = ['Second Order Upwind' for _ in range(len(self.schemes))]
        else:
            if not isinstance(orders,list):
                orders = [orders for _ in range(len(self.schemes))]
            if len(orders) != len(self.schemes):
                raise AttributeError('Orders and schemes must be of the same length')
            
            for order in orders:
                if order not in self.ALLOWABLE_DISCRITIZATION_ORDERS: 
                    raise ValueError('order of {} not allowed'.format(order))
            
            self.__orders = orders

    @property
    def schemes(self):
        return self.__schemes
    
    @property
    def orders(self):
        return self.__orders
    
    def _format_default_scheme(self,scheme,order):
        """
        schemes for most variables here
        """
        txt = ''
        txt += scheme + self.LINE_BREAK
        txt += str(self.ALLOWABLE_DISCRITIZATION_ORDERS[order]) + self.LINE_BREAK
        return txt
    
    def _format_pressure_scheme(self,scheme,order):
        """
        the scheme for presure is different for some reason
        """
        txt = ''
        try:
            order = self.pmap[order]
        except KeyError:
            pass

        txt += scheme + self.LINE_BREAK
        txt += str(self.ALLOWABLE_DISCRITIZATION_ORDERS[order]) + self.LINE_BREAK
        return txt
    
    def _format_discritization(self):
        """
        format the discrization scheme for TUI
        """
        txt = self._prefix + self.LINE_BREAK
        for s,o in zip(self.schemes,self.orders):
            if s == 'pressure':
                txt += self._format_pressure_scheme(s,o)
            else:
                txt += self._format_default_scheme(s,o)
        
        txt += self.EXIT_CHAR + self.EXIT_CHAR + self.EXIT_CHAR
        return txt
    
    def __str__(self):
        """
        string representation
        """
        return self._format_discritization()
    
class FileIO(ABC,TUIBase):

    """
    Base class for file-io in fluent - inherited by various reader's and writers
    """
    _prefix = ''
    _suffix = ''

    def __init__(self,file,*args,**kwargs):

        self.__file = file
    
    @property
    def file(self):
        return self.__file
    
    def __str__(self):
        return self._prefix + ' ' + self.file + self._suffix

class CaseReader(FileIO):

    """
    representation of the read-case command
    
    Parameters
    ----------
    file: str
            name of the file as a string

    Examples
    --------
    
    .. code-block:: python 

        cr = CaseReader('sample.cas')
        print(cr)
        > file/read-case sample.cas
    """
    
    _prefix = 'file/read-case'

class BatchCaseReader(CaseReader):

    """
    Case reader for batched inputs. Assumes a file structure like: 

    main folder
    * | -> batch folder 1
    * | -> batch folder 2
    * .
    * .
    * | -> batch folder n

    sample.cas``

    will first change to an outer directory, read in file, and then change
    back to the original directory

    Parameters
    ----------
    file: str
            the name of the .cas file as a string
    
    Examples
    ---------
    set folder to change back into on initiation
    
    .. code-block:: python
        
        bcr = BatchCaseReader('sample.cas',current_folder = 'main')
        print(bcr)
        > sync-chdir ..
        > file/read-case sample.cas
        > sync-chdir main
    
    set property directly 

    .. code-block:: python

        bcr = BatchCaseReader('sample.cas')
        bcr.pwd = 'main'
        print(bcr)

        > sync-chdir ..
        > file/read-case sample.cas
        > sync-chdir main
    """
    
    def __init__(self,file,
                      current_folder = None):

        super().__init__(file)
        
        self._prefix = 'sync-chdir ..' + self.LINE_BREAK + 'file/read-case'
        
        if current_folder is not None:
            self.__pwd = current_folder
        else:
            self.__pwd = None
        
    @property
    def _suffix(self):
        return self.LINE_BREAK + 'sync-chdir {}'.format(self.pwd)
        
    @property
    def pwd(self):
        return self.__pwd

    @pwd.setter
    def pwd(self,pwd):
        self.__pwd = pwd


class SettingsWriter(FileIO):

    """
    representation of the write-settings command
    
    Parameters
    ----------
    file: str
            name of the file as a string

    Examples
    --------
    
    .. code-block:: python 

        sw = SettingsWriter('test.settings')
        print(sw)
        > file/write-settings test.settings
    """
    
    _prefix = 'file/write-settings'

    def __init__(self,file: str):

        super().__init__(file)

class SettingsReader(FileIO):

    """
    representation of the write-settings command
    
    Parameters
    ----------
    file: str
            name of the file as a string

    Examples
    --------
    
    .. code-block:: python 

        sr = SettingsReader('test.settings')
        print(sr)
        > file/read-settings test.settings
    """
    
    _prefix = 'file/read-settings'

    def __init__(self,file: str):

        super().__init__(file)


class TempCaseIO(FileIO):

    """
    for temporary reading and writing of case files
    in fluent. Useful if a case needs to be re-read for changes
    and modifications to take effect
    
    Parameters
    ----------
    tui_commands: List
            a list of tui commands that can be specified in between the read/write
            of the temporary case file
    file: str | None
            the file to write the temporary file to, if None, a random file name will be
            generated like: "temp_asdofoijasfd.....ext"
            where ext is the extension specified, and the number of characters after "temp_"
            is determined by the "random_character_length" 
    ext: str
            file extension to specify
    random_character_length: int
            the number of random characters to specify

    Examples
    --------
    
    .. code-block:: python 

        tempfile = TempCaseIO()
        print(tempfile)
        > file/write-case temp_JyeVlcoYcLzGlERv.cas
        > file/read-case temp_JyeVlcoYcLzGlERv.cas 
        > !rm temp_gesXDLqhLXDnafTx.cas
    """

    FILE_PREFIX = 'temp'
    def __init__(self,tui_commands = [],
                      tui_pre_commands = [],
                      tui_post_commands = [],
                      file = None,
                      ext = '.cas',
                      random_character_length = 16,
                      delete = True):

        self.ext = ext
        self.random_character_length = random_character_length
        self.tui_commands = tui_commands
        self.tui_pre_commands = tui_pre_commands
        self.tui_post_commands = tui_post_commands
        self.delete = delete
        if file is None:
            file = self.generate_random_file_name()
        
        super().__init__(file)
    
    def stringify_tui_commands(self, cmds: List[str]) -> str:
        text = ''
        for command in cmds:
            try:
                text += str(command) + self.LINE_BREAK
            except (AttributeError,TypeError):
                text += command()
        
        if text != '':
            if text[-1] == self.LINE_BREAK:
                return text
            else:
                return text + self.LINE_BREAK
        else:
            return text 
    
    def __str__(self):

        writer = CaseWriter(self.file)
        reader = CaseReader(self.file)

        if self.delete:
            end_text = '!rm ' + self.file + self.LINE_BREAK
        else:
            end_text = ''
        
        return self.stringify_tui_commands(self.tui_pre_commands) +\
               str(writer) + self.LINE_BREAK +\
               self.stringify_tui_commands(self.tui_commands) +\
               str(reader) + \
               self.stringify_tui_commands(self.tui_post_commands) + \
               self.LINE_BREAK + end_text


class CaseMeshReplaceReader(FileIO):

    """
    read-case and then replace with another mesh
    
    Parameters
    ----------
    case_file : str
            the string file name of the case file you want to read
    
    mesh_file : str
            the mesh file string name of the case file you want to read

    Examples
    --------

    .. code-block:: python 
        
        cmr = CaseMeshReplaceReader('sample.cas','new.msh')
        print(cmr)
        > file/read-case sample.cas
        > mesh/replace new.msh
    """

    _prefix = 'mesh/replace'

    def __init__(self,case_file: str,
                      mesh_file: str,
                      intermediate_modifications = [],
                      reader = CaseReader) -> None:

        self.intermediate_modifications = intermediate_modifications
        self._case_reader = reader(case_file)
        self.__pwd = None
        
        super().__init__(mesh_file)

    @property
    def pwd(self) -> str:
        return self.__pwd
    
    @pwd.setter
    def pwd(self,pwd):
        self.__pwd = pwd
        self._case_reader.pwd = pwd

    def __str__(self):
        _prefix = str(self._case_reader) + self.LINE_BREAK
        for im in self.intermediate_modifications:
            _prefix += str(im)
        
        self._prefix = _prefix + self._prefix
        return super().__str__()


class CaseDataReader(CaseReader):

    """
    representation of the read-case-data command in python

    Parameters
    ----------
    file: str
            name of the file as a string
    
    Examples
    --------

    .. code-block:: python

        cdr = CaseDataReader('sample.cas')
        print(cdr)
        > file/read-case-data sample.cas

    """
    _prefix = 'file/read-case-data'

class CaseAppendReader(TUIBase):

    _prefix = 'mesh/modify-zones/append-mesh-data'
    def __init__(self,case_file: str):

        self.case_file = case_file

    def __str__(self):

        txt = self._prefix + self.LINE_BREAK
        txt += self.case_file + self.LINE_BREAK
        return txt


class FluentEngine(TUIBase):

    """
    main class for the post processing engine using fluent. If fluent needs
    to be invoked and supplied with commands via the python interface, this is the best
    option.

    Parameters
    ----------
    file : str
            string of the .cas file in fluent
    specification : str
            keyword argument for the specification of fluent - default "3ddp"
    num_processors : int
            keyword argument specifying the number of processors to use\
            when invoking fluent - default 1
    reader : object
            keyword argument specifying the type of reader to use to read in the
            case file. Readers must have a __str__ method. - default CaseDataReader
    fluent_path : str
            keyword argument specifying the path to the fluent executable
    version : str
            the version of fluent being used. may be used to switch between paths

    Examples
    --------
    example demonstrates how to extract a surface integral from a case file via fluent.
    This example would invoke fluent provided that the fluent executable is on the system path.
    
    .. code-block:: python
        
        engine = FluentEngine('sample.cas',num_processors = 8)
        si = SurfaceIntegrals('sample.cas',11,'temperature','area-weighted-avg',engine = engine)
        sif = si()
    """

    POSIX_FLUENT_INIT_STATEMENT = '{}/fluent {} -t{} < {} > {}'
    WINDOWS_FLUENT_INIT_STATEMENT = '{}/fluent {} -t{} -g -i {} -o {}'
    FLUENT_INPUT_NAME = 'input.fluent'
    FLUENT_OUTPUT_NAME = 'output.fluent'

    def __init__(self,file: str,
                      specification = '3ddp',
                      num_processors = 1,
                      reader = CaseDataReader,
                      version = '19.1',
                      fluent_path = None):
        
        self.path,file_name = os.path.split(file)
        self.spec = specification
        self.__num_processors = num_processors
        self.__input = reader(file_name)
        self._additional_txt = ''
        self.input_file = os.path.join(self.path,self.FLUENT_INPUT_NAME)
        self.output_file = os.path.join(self.path,self.FLUENT_OUTPUT_NAME)
        self.__fluent_path = fluent_path
        self.version = version
    

    def insert_text(self,other):
        self._additional_txt += other
    
    @property
    def num_processors(self):
        return str(self.__num_processors)

    @property
    def fluent_path(self):

        if self.__fluent_path is None:
            return get_fluent_path(self.version)
        else:
            return self.__fluent_path

    def _fluent_initializer(self,
                            system = None):
        """
        the initialization is platform dependent, so accomodate this. Also,
        it could be the case that we want to define the system manually and then use
        this file on another type of system, so allow manual input through sytem 
        keyword argument
        """

        if system is None:
            os_name = sys.platform
            if os_name == 'win32' or os_name == 'win64':
                system = 'windows'
            elif os_name == 'linux' or os_name == 'posix':
                system = 'posix'
            
        if system == 'windows':
            return self.WINDOWS_FLUENT_INIT_STATEMENT.format(self.fluent_path,
                                                            self.spec,
                                                            self.num_processors,
                                                            self.FLUENT_INPUT_NAME,
                                                            self.FLUENT_OUTPUT_NAME) + self.EXIT_CHAR
        elif system == 'posix':
            return self.POSIX_FLUENT_INIT_STATEMENT.format(self.fluent_path,
                                                            self.spec,
                                                            self.num_processors,
                                                            self.FLUENT_INPUT_NAME,
                                                            self.FLUENT_OUTPUT_NAME) + self.EXIT_CHAR
        else:
            raise ValueError('system must be one of 1. windows or 2. posix')
        
    @property
    def input(self):
        return str(self.__input)
    
    def _format_call(self,save):
        """
        format the text for the call, and also write the input file for 
        fluent
        """
        call_text = self._fluent_initializer()
        self._format_input_file(save)
        return call_text
    
    def _format_input_file(self,save) -> None:
        """
        format the input file to fluent to read and create the surface integral
        """
        txt = self.input + self.LINE_BREAK
        txt += self._additional_txt + self.LINE_BREAK
        txt += self.EXIT_STATEMENT + self.LINE_BREAK
        if save is not None:
            if save:
                raise NotImplementedError('not formatted for saving')
            else:
                txt += 'ok' + self.LINE_BREAK
        
        with open(self.input_file,'w') as file:
            file.write(txt)
    
    def _clean(self):
        """ 
        clean directory from input and output files
        """
        if os.path.exists(self.input_file):
            os.remove(self.input_file)
        
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
        
    def __call__(self, save = None):
        """
        This call does the following:
        (1) cleans the directory of the fluent case file from input and output files
        (2) formats the call
        (3) opens fluent and submits commands to fluent
        (4) cleans up the directory again
        """

        self._clean()
        txt = self._format_call(save)
        cwd = os.getcwd()
        os.chdir(self.path)
        process = subprocess.call(txt)
        os.chdir(cwd)
        self._clean()
        return process


    
class DataWriter(FileIO):

    """
    representation of the write-data command
    
    Parameters
    ----------
    file : str
            string of the file name to write (.dat)

    Examples
    --------

    .. code-block:: python

        dr = DataWriter('mydata.dat')
        print(dr)
        > file/write-data mydata.dat
    """
    
    _prefix = 'file/write-data'

    def __init__(self,file):

        super().__init__(file)

class CaseWriter(FileIO):

    """
    representation of the write-case command
    Parameters
    ----------
    file : str
            string of the file name to write (.cas)

    Examples
    --------

    .. code-block:: python

        cr = CaseWriter('sample.cas')
        print(cr)
        > file/write-case sample.cas
    """
    
    _prefix = 'file/write-case'

    def __init__(self,file):

        super().__init__(file)

class Solver_Iterator(TUIBase):

    """
    base representation of a solver iterator
    
    Parameters
    ----------
    niter : int 
            number of iterations to iterate for - default 200
    
    Examples
    ----------

    .. code-block:: python
    
        si = Solver_Iterator(niter = 500)
        print(si)
        > solve/iterate 500
    """

    _prefix = 'solve/iterate'
    def __init__(self,niter = 200):
        self.__niter = niter
    
    @property
    def niter(self):
        return self.__niter
    
    def __str__(self):
        return self._prefix + ' ' + str(self.niter)

class Solver(TUIBase):

    """
    the solver class, must be initialzed with an initializer (for the solver)
    and a Solver_Iterator

    Parameters
    ----------
    initializer : object
            an object with a __str__ method intended to initalize a fluent solution

    solver_iterator : object
            an object with a __str__ method intended to iterate a fluent solution
    
    Examples
    --------
    
    .. code-block:: python
        
        solver = Solver()
    
    .. code-block:: python
        
        solver = Solver(initializer= Initializer(),
                solver_iterator= Solver_Iterator(niter = 1000))
        
    """
    
    def __init__(self,
                 initializer = Initializer(),
                 solver_iterator = Solver_Iterator()):

        self.__initializer = initializer
        self.__solver_iterator = solver_iterator

    @property
    def initializer(self):
        return self.__initializer
    
    @property
    def solver_iterator(self):
        return self.__solver_iterator

    @property
    def usage(self):
        return 'parallel timer usage'

    def __str__(self):
        txt = str(self.initializer) + self.LINE_BREAK
        txt += str(self.solver_iterator) + self.LINE_BREAK
        txt += str(self.usage) + self.LINE_BREAK
        return txt 


class ReportFile(TUIBase):
    """
    Class for adding report files to a Fluent simulation.
    - Both creation and deletion of a file is not permitted in a single class
    - if a file is deleted, any supplied variables are ignored

    Parameters
    ----------
    fname: str
            the string of the report file name
    variables: List[str]
            optional keyword arguments containing a list of variables to include
            in the report file
    create: bool
            optional keyword argument to create the report file
    delete: bool
            optional keyword argument to delete the report file
    
    Examples
    --------

    .. code-block:: python
        
        rf = ReportFile('report-file-1',variables = ['p-in','t-out'],
                        create = False)
        
        print(str(rf))

    """

    _prefix = 'solve/report-files/'
    _delete_prefix = 'delete'
    _create_prefix = 'add'
    _edit_prefix = 'edit'


    def __init__(self,fname: str,
                      variables = [],
                      create = False,
                      delete = False):

        if create and delete:
            raise ValueError('cannot both create and delete report file')
        

        self.fname,self.ext = os.path.splitext(fname)
        self.variables = variables
        self.create = create
        self.delete = delete
    
    def add_variables(self,variables: List[str]) -> None:
        
        self.variables += variables
    
    def format_delete(self) -> str:

        txt = self._prefix + self._delete_prefix + self.LINE_BREAK
        txt += self.fname + self.LINE_BREAK
        
        return txt

    def format_creation(self) -> str:
        
        txt = self._prefix + self._create_prefix + self.LINE_BREAK
        txt += self.fname + self.LINE_BREAK

        return txt
    
    def format_add_report_definition(self) -> str:

        txt = self._prefix + self._edit_prefix + self.LINE_BREAK
        txt += self.fname + self.LINE_BREAK
        txt += 'report-defs' + self.LINE_BREAK
        
        for v in self.variables:
            txt += v + self.LINE_BREAK
        
        return txt
    
    def format_report(self) -> str:

        txt = ''
        if self.delete:
            txt += self.format_delete()
            return txt

        elif self.create:
            txt += self.format_creation()
            if self.variables:
                txt += self.format_add_report_definition()

        return txt

    def __str__(self) -> str:

        return self.format_report()

    def __call__(self) -> str:

        return self.format_report() 


class ReportDefinitions(TUIBase):

    _prefix = 'solve/report-definitions'
    _create_prefix = ''
    def __init__(self,name: str,
                      delete = False):

        self.name = name
        self.delete = delete

    def format_creation(self,name) -> str:

        pass

class LoadCustomFieldFunction(TUIBase):

    _prefix = 'define/custom-field-functions/load'

    def __init__(self,file_name: str):

        self.file_name = file_name
    
    def __str__(self) -> str:

        return self._prefix + '/' + self.file_name

class SetReferenceValue(TUIBase):

    _prefix = 'report/reference-values/{}'

    def __init__(self,name: str,
                      value: float):

        self.name = name
        self.value = value
    
    def __str__(self) -> str:

        return self._prefix.format(self.name) + ' ' + str(self.value)
    
class ConvergenceConditions(TUIBase):
    """
    modify convergence conditions

    Parameters
    ----------
    variables : list
            a list of variables to moniter for convergence
    condition : 'all' | 'any'
            either all or any indicating to terminate solution procedure once all or any conditions are met
    initial_values_to_ignore: int (default 0)
            how many iterations to ignore before checking convergence
    previous_values_to_consider: int (default 1)
            how many previous iterations to check to ensure convergence,handy for oscillating solutions
    stop_criterion : float (default 1e-3)
            value to judge convergence by
    print_value: bool (default True)
            print the value of the monitored variable or not
    
    Examples
    --------
    
    .. code-block:: python
        
        cc = ConvergenceConditions(['report-def1'],condition = 'all')
        print(cc)
        
        > /solve/convergence-conditions
        > condition
        > 1
        > conv-reports
        > add
        > report-def1-convergence
        > initial-values-to-ignore
        > 0
        > previous-values-to-consider
        > 1
        > print
        > yes
        > stop-criterion
        > 0.001
        > report-defs
        > report-def1
        > q
        > q
        > q
    """

    _prefix = '/solve/convergence-conditions'

    def __init__(self,variables: list,
                      condition = 'all',
                      initial_values_to_ignore = 0,
                      previous_values_to_consider = 1,
                      stop_criterion = 1e-3,
                      print_value = True,
                      ):

        self.__variables = variables
        self.__condition = condition.lower()
        self.__initial_values_to_ignore = initial_values_to_ignore
        self.__previous_values_to_consider = previous_values_to_consider
        self.__print = print_value
        self.__stop_criterion = stop_criterion

    @property
    def variables(self):
        return self.__variables
    
    @property
    def condition(self):
        if self.__condition == 'all':
            return '1'
        elif self.__condition == 'any':
            return '2'
        else:
            raise ValueError('condition must be "all" or "any"')

    @property
    def print_value(self):
        if self.__print:
            return 'yes' 
        else:
            return 'no'
        
    @property
    def initial_values_to_ignore(self):
        return self.__initial_values_to_ignore
    
    @property
    def previous_values_to_consider(self):
        return self.__previous_values_to_consider
    
    @property
    def stop_criterion(self):
        return self.__stop_criterion
    
    def format_condition(self):

        txt = 'condition' + self.LINE_BREAK
        txt += self.condition + self.LINE_BREAK
        return txt
    
    def add_condition(self,name):

        txt = 'add' + self.LINE_BREAK
        txt += name + '-convergence' +  self.LINE_BREAK
        txt += 'initial-values-to-ignore' + self.LINE_BREAK
        txt += str(self.initial_values_to_ignore) + self.LINE_BREAK
        txt += 'previous-values-to-consider' + self.LINE_BREAK
        txt += str(self.previous_values_to_consider) + self.LINE_BREAK
        txt += 'print' + self.LINE_BREAK
        txt += self.print_value + self.LINE_BREAK
        txt += 'stop-criterion' + self.LINE_BREAK
        txt += str(self.stop_criterion) + self.LINE_BREAK
        txt += 'report-defs' + self.LINE_BREAK
        txt += name + self.LINE_BREAK
        txt += self.EXIT_CHAR

        return txt
    
    def format_convergence_conditions(self):

        txt = self._prefix + self.LINE_BREAK
        txt += self.format_condition()
        txt += 'conv-reports' + self.LINE_BREAK
        for var in self.variables:
            txt += self.add_condition(var)
        
        txt += self.EXIT_CHAR + self.EXIT_CHAR
        return txt

    def __str__(self):
        return self.format_convergence_conditions()

class FluentCase(TUIBase):
    
    """ 
    class for representing a fluent case
    """
    
    def __init__(self,case_name: str):

        self.__case_file = case_name

    @property
    def case_file(self):
        return self.__case_file

class RPSetVar(TUIBase):
    """
    Unit class for modifying Variables through the "rpsetvar" command. 
    """

    SET_VAR = r"rpsetvar'"
    SET_FLOAT_VAR = '(' + SET_VAR + ' {} {})'

    def __init__(self,name: str,
                     value: object):

        super().__init__()
        self.name = name
        self.value = value

    def __call__(self) -> str:

        if self.value is None:
            return self.value
        else:
            return self.SET_FLOAT_VAR.format(self.name,str(self.value))

class RPSetVarModification(TUIBase, ABC):

    def __init__(self,input_dict: dict):

        self._dict = dict.fromkeys(input_dict)
        for key, value in input_dict.items():
            self.__setitem__(key,value)
        
    def __getitem__(self,key: Hashable) -> object:

        return self._dict[key]()
    
    def __setitem__(self,key: Hashable,
                         newvalue: object) -> None:
        
        self._dict[key] = RPSetVar(key,newvalue)
    
    def __call__(self) -> str:

        txt = ''
        for key in self._dict:
            try:
                txt += self.__getitem__(key) + self.LINE_BREAK
            except TypeError:
                pass
        
        return txt
    
    def __str__(self) -> str:

        return self.__call__()
    
class TwoEquationModelConstants(RPSetVarModification):

    """
    Class for modifying the Model constants in the two equation
    models via the rpsetvar interface. This is limited 
    """

    def __init__(self,defaults = {},
                     **kwargs):

        inputdict = dict.fromkeys(kwargs.keys())
        for key in defaults:
            if key not in inputdict:
                inputdict[key] = defaults[key]
            else:
                inputdict[key] = kwargs[key]
        
        _inputdict = self.name_mapping(inputdict,self.parameter_lookup)
        super().__init__(_inputdict)

    def name_mapping(self,input_dict: dict,
                          association : dict) -> dict:

        output_dict = dict.fromkeys(association.keys())
        for key in output_dict:
            output_dict[key] = input_dict[association[key]]
        
        return output_dict

class KEpsilonModelConstants(TwoEquationModelConstants):

    def __init__(self,**kwargs):

        DEFAULTS = {'wall_prandlt': None,
                    'sigma_k': None,
                    'c_epsilon_1': None,
                    'c_epsilon_2': None,
                    'c_mu': None,
                    'sigma_eps': None,
                    'energy_prandlt': None}

        self.parameter_lookup = {'wallprt':'wall_prandlt',
                                 'keprt': 'energy_prandlt',
                                 'kesige': 'sigma_eps',
                                 'kesigk': 'sigma_k',
                                 'kec2': 'c_epsilon_2',
                                 'kec1':'c_epsilon_1',
                                 'kecmu':'c_mu'}
                                
        super().__init__(defaults = DEFAULTS,**kwargs)

class KEpsilonRNGModelConstants(TwoEquationModelConstants):

    def __init__(self,**kwargs):

        DEFAULTS = {'wall_prandlt': None,
                    'c_epsilon_1': None,
                    'c_epsilon_2': None,
                    'c_mu': None}

        self.parameter_lookup = {'wallprt':'wall_prandlt',
                                 'rng-kec2': 'c_epsilon_2',
                                 'rng-kec1':'c_epsilon_1',
                                 'rng-kecmu':'c_mu'}
                                
        super().__init__(defaults = DEFAULTS,**kwargs)

class KOmegaModelConstants(TwoEquationModelConstants):

    def __init__(self,**kwargs):

        DEFAULTS = {'sigma_w': None,
                    'sigma_k': None,
                    'beta_i': None,
                    'beta_star_inf': None,
                    'r_w':None,
                    'r_k': None,
                    'r_beta': None,
                    'alpha_0':None,
                    'alpha_inf': None,
                    'alpha_star_inf': None}
        
        self.parameter_lookup = {'kw-sig-w': 'sigma_w',
                                 'kw-sig-k':'sigma_k',
                                 'kw-beta-i': 'beta_i',
                                 'kw-beta-star-inf':'beta_star_inf',
                                 'kw-r-w': 'r_w',
                                 'kw-r-k ':'r_k',
                                 'kw-r-beta':'r_beta',
                                 'kw-alpha-0': 'alpha_0',
                                 'kw-alpha-inf':'alpha_inf',
                                 'kw-alpha-star-inf':'alpha_star_inf'}
        
        super().__init__(defaults = DEFAULTS,**kwargs)

class GEKOModelConstants(TwoEquationModelConstants):

    def __init__(self,**kwargs):

        DEFAULTS = {'c_jet_aux': None,
                    'c_jet':None,
                    'c_real': None,
                    'c_mix':None,
                    'c_nw_sub':None,
                    'c_nw':None,
                    'c_sep':None,
                    'bf_tur': None,
                    'c_curv': None,
                    'c_corner': None}


        self.parameter_lookup = {'geko-cjet-aux':'c_jet_aux',
                                  'geko-cjet-v193':'c_jet',
                                  'geko-creal':'c_real',
                                  'geko-cmix':'c_mix',
                                  'geko-cnw-sub': 'c_nw_sub',
                                  'geko-cnw':'c_nw',
                                  'geko-csep':'c_sep',
                                  'geko-bf-tur':'bf_tur',
                                  'corner-flow-correction-ccorner':'c_corner',
                                  'curvature-correction-ccurv':'c_curv'}
        
        super().__init__(defaults= DEFAULTS,**kwargs)

class KOmega_BSLModelConstants(TwoEquationModelConstants):

    def __init__(self,**kwargs):

        DEFAULTS = {'beta_i2': None,
                    'beta_i1':None,
                    'sigma_w2': None,
                    'sigma_w1': None,
                    'sigma_k1': None,
                    'sigma_k2': None,
                    'beta_star_inf': None,
                    'alpha_inf': None,
                    'alpha_star_inf': None,
                    'sigma_wall': None,
                    'sigma_ke': None}

        self.parameter_lookup = {'bsl-beta-i2':'beta_i2',
                                 'bsl-beta-i1':'beta_i1',
                                 'bsl-sig-w2':'sigma_w2',
                                 'bsl-sig-w1':'sigma_w1',
                                 'bsl-sig-k1':'sigma_k1',
                                 'bsl-sig-k2':'sigma_k2',
                                 'kw-beta-star-inf':'beta_star_inf',
                                 'kw-alpha-inf':'alpha_inf',
                                 'kw-alpha-star-inf':'alpha_star_inf',
                                 'wallprt':'sigma_wall',
                                 'keprt':'sigma_ke'}
        
        super().__init__(defaults= DEFAULTS,**kwargs)
    
class KOmega_SSTModelConstants(TwoEquationModelConstants): 

    def __init__(self,**kwargs):

        DEFAULTS = {'c_corner': None,
                    'c_curv': None,
                    'beta_i2': None,
                    'beta_i1': None,
                    'a1': None,
                    'sigma_w2':None,
                    'sigma_w1': None,
                    'sigma_k1': None,
                    'sigma_k2': None,
                    'beta_star_inf':None,
                    'alpha_inf':None,
                    'alpha_star_inf':None,
                    'sigma_wall': None,
                    'sigma_ke': None}

        self.parameter_lookup = {'corner-flow-correction-ccorner':'c_corner',
                                 'curvature-correction-ccurv':'c_curv',
                                 'sst-beta-i2':'beta_i2',
                                 'sst-beta-i1':'beta_i1',
                                 'sst-a1':'a1',
                                 'sst-sig-w2':'sigma_w2',
                                 'sst-sig-w1':'sigma_w1',
                                 'sst-sig-k1':'sigma_k1',
                                 'sst-sig-k2':'sigma_k2',
                                 'kw-beta-star-inf':'beta_star_inf',
                                 'kw-alpha-inf':'alpha_inf',
                                 'kw-alpha-star-inf':'alpha_star_inf',
                                 'wallprt':'sigma_wall',
                                 'keprt':'sigma_ke'}
        
        super().__init__(defaults= DEFAULTS,**kwargs)

class KOmegaLowReCorrection(TwoEquationModelConstants):

    def __init__(self,**kwargs):

        DEFAULTS = {'r_w': None,
                    'r_k': None,
                    'r_beta': None}

        self.parameter_lookup = {'kw-r-w': 'r_w',
                                 'kw-r-k':'r_k',
                                 'kw-r-beta':'r_beta'}
        
        super().__init__(defaults = DEFAULTS,**kwargs)
    

class ModelModificationCollector:

    def __init__(self,modifications: List,
                      rule: callable):

        self.modifications = modifications
        self.rule = rule

    def apply_rules(self, modification):

        txt = self.rule(modification)
        return txt

    def __str__(self) -> str:
        
        txt = ''
        for modification in self.modifications:
            txt += self.apply_rules(modification)

        return txt

class ModelModification(ABC,TUIBase):

    _prefix = 'define/models/{}'
    """
    abstract base class for modifying models
    """
    def __init__(self,model_class: str):

        self.model_class = model_class
    
    def __str__(self):

        txt = self._prefix.format(self.model_class) + self.LINE_BREAK
        txt += self.format_model_modification()
        return txt

    @abstractmethod
    def format_model_modification():
        pass

class ViscousModelModification(ModelModification):
    """
    class implemented in order to facilitate changing of turbulence models
    in Fluent.

    The allowable models (listed) below are limited here because I am unsure of the
    behavior of the fluent case if two-equation models are not selected at this time
    this list may be appended to in the future

    Allowable models:

    1. 'ke-realizable'
    2. 'ke-rng'
    3. 'ke-standard'
    4. 'kw-bsl'
    5. 'kw-sst'
    6. 'kw-geko' or 'geko'
    7. 'kw-standard'
    8. 'k-kl-w'
    
    Parameters
    ---------
    name : str
            the viscous model to modify
    
    Examples
    ---------

    .. code-block:: python

        vmm = ViscousModelModification('ke-realizable')
        print(vmm)
        > define/models/viscous
        > ke-realizable
        > yes
        > q

    """

    ALLOWABLE_VISCOUS_MODELS = ['ke-realizable',
                                'ke-rng',
                                'ke-standard',
                                'kw-bsl',
                                'kw-sst',
                                'kw-geko',
                                'geko',
                                'kw-standard',
                                'k-kl-w',
                                'reynolds-stress-model']


    def __init__(self,name: str):
        
        if name not in self.ALLOWABLE_VISCOUS_MODELS:
            txt = [allow + '\n' for allow in self.ALLOWABLE_VISCOUS_MODELS]
            raise ValueError('name: {} not allowed, must be one of: {}'.format(txt))
        
        super().__init__('viscous')
        self.name = name

    def format_model_modification(self):

        txt = self.name + self.LINE_BREAK
        txt += 'yes' + self.LINE_BREAK
        txt += self.EXIT_CHAR + self.LINE_BREAK
        return txt

class MaterialProperty(TUIBase):

    ALLOWABLE_APPROXIMATION = ['constant',
                                'piecewise-linear',
                                'piecewise-polynomial']

    def __init__(self,name: str,
                      value: Union[str,None],
                      approximation: str):

        self.name = name
        self.value = value
        self.approximation = approximation

    def format_value(self):

        if self.approximation == 'constant':
            text = str(self.value) + self.LINE_BREAK
        
        elif self.approximation == 'piecewise-linear' or self.approximation == 'piecewise-polynomial':
            value = np.array(self.value).squeeze()
            if value.ndim != 2:
                raise ValueError('must be interpretable as a 2D array')
            if value.shape[0] < 2:
                raise ValueError('must have greater than two points for peicwise specification')
            if value.shape[1]!= 2:
                raise ValueError('must be a two-D array with temperature the first column and property the second')
            
            text = str(value.shape[0]) + self.LINE_BREAK + ',' +self.LINE_BREAK
            for i in range(value.shape[0]):
                text += str(value[i,0]) + self.LINE_BREAK
                text += str(value[i,1]) + self.LINE_BREAK
                text += + ',' +self.LINE_BREAK
            
        else:
            txt = [aa + self.LINE_BREAK for aa in self.ALLOWABLE_APPROXIMATION]
            raise ValueError('apprxomation must be one of: {} \n not {}'.format(txt,self.approximation))
        
        return self.approximation + self.LINE_BREAK + text

    def __call__(self):

        if self.value is None:
            return 'no' + self.LINE_BREAK 
        else:
            return 'yes' + self.LINE_BREAK + self.format_value()

class MaterialModification(ABC,TUIBase):

    _prefix = 'define/materials/change-create'

    def __init__(self,name: str,
                      **kwargs):

        super().__init__()
        self.name = name

    def enter_statement(self):

        return self._prefix + '/' + self.name +\
               self.LINE_BREAK + ',' + self.LINE_BREAK

    @abstractmethod
    def format_materials(self):
        pass 

    def __call__(self):

        return self.enter_statement() + self.format_materials()
    
class FluidMaterialModification(MaterialModification):

    def __init__(self,name: str,
                      approximation = 'constant',
                      **kwargs):

        super().__init__(name)

        default_props = ['density','cp','thermal_conductivity',
                        'viscosity','molecular_weight',
                        'thermal_expansion_coefficient',
                        'speed_of_sound']
        
        self.prop_values = OrderedDict()
        for key in kwargs:
            if key not in default_props:
                raise ValueError('cannot specify property: {}'.format(key))

        for key in default_props:
            if key in kwargs:
                value = kwargs[key]
                if isinstance(value,MaterialProperty):
                    self.prop_values[key] = value
                else:
                    self.prop_values[key] = MaterialProperty(key,value,approximation)
            else:
                self.prop_values[key] = MaterialProperty(key,None,approximation)

    def format_materials(self):
        txt = ''
        for _,mp in self.prop_values.items():
            txt += mp()
        
        return txt

class FluentCellZone(ABC,TUIBase):
    """
    Class for modifications to a Fluent Cell Zone, either solid or
    fluid. Offers the ability to (1) change the material, (2) add a constant source
    (3) modify the zone type. 

    Parameters
    ----------
    name: str
            name of the fluent cell zone
    boundary_type: str
            the type of the zone to be modified i.e. solid,fluid,wall,mass inlet ect...

    
    Examples
    --------

    .. code-block:: python

        fcz = FluentCellZone('my_zone','fluid')
        fcz.modify_zone_type('solid')
        fcz.change_material('aluminum')
    
    """

    _prefix = '/define/boundary-conditions/{}'
    def __init__(self,name: str,
                      boundary_type: str):
        
        self.name = name
        self.boundary_type = boundary_type
        
        #material change
        self._mat_change = False
        self._new_material = None

        #add source
        self._add_const_src = False
        self._source_value = None

        #change zone type
        self._modify_zone = False
        self._zone_type = None


    def change_material(self, new_material: str) -> None:
        """
        stores whether or not to change the material
        
        Parameters
        ----------
        new_material : str
                string of new material to change to
        
        """

        self._mat_change = True
        self._new_material = new_material
    
    def add_constant_source(self,source_value: Union[float,list]) -> None:
        """
        add a constant source to a cell zone

        Parameters
        ----------
        source_value : float | list
                add a constant source (or multiple sources if list) to the cell zone
        
        """
        self._add_const_src = True
        self._source_value = source_value
    
    def modify_zone_type(self,new_type: str) -> None:
        """
        Parameters
        ----------
        new_type : str
                one of "fluid" or "solid" that allows changing the type of the cell zone
        """

        if new_type != 'fluid' and new_type != 'solid':
            raise ValueError('only zone types of fluid or solid supported')
        
        self._modify_zone = True
        self._zone_type = new_type

    def _format_change_material(self) -> str:
        """
        format changing the material
        """
        if self._mat_change:
            txt = self._prefix.format(self.boundary_type) + self.LINE_BREAK
            txt += self.name + self.LINE_BREAK
            txt += 'yes' + self.LINE_BREAK
            txt += self._new_material + self.LINE_BREAK
        else:
            txt = 'no' + self.LINE_BREAK

        return txt

    def _format_add_constant_source(self) -> str:
        """
        formatt the addition of a source
        """
        if isinstance(self._source_value,list):
            raise NotImplementedError('gonna have to support list source terms here')
            len_src = len(self._source_value)
        else:
            len_src = 1

        if len_src > 10:
            raise ValueError('Fluent doesnt allow specification of more than 10 sources')
        
        if self._add_const_src:
            txt = 'yes' + self.LINE_BREAK
            txt += str(len_src) + self.LINE_BREAK
            txt += 'yes' + self.LINE_BREAK
            txt += str(self._source_value) + self.LINE_BREAK

        else:
            txt = 'no' + self.LINE_BREAK
        
        return txt

    def _format_modify_zone(self) -> str:
        """
        format the modification of a zone type
        """
        txt = self._prefix.format('modify-zones/zone-type') + self.LINE_BREAK
        txt += self.name + self.LINE_BREAK
        txt += self._zone_type + self.LINE_BREAK
        return txt


    def __call__(self) -> str:

        return self.format_boundary_condition()
    
    def __str__(self) -> str:

        return self.format_boundary_condition()
    
    def format_boundary_condition(self) -> str:

        if self._modify_zone:
            txt = self._format_modify_zone()
        else:
            txt = ''

        txt += self._format_change_material()
        txt += self._format_add_constant_source()
        
        txt += 'no' + self.LINE_BREAK
        txt += 'no' + self.LINE_BREAK
        txt += 'no' + self.LINE_BREAK
        txt += '0' + self.LINE_BREAK
        txt += 'no'  + self.LINE_BREAK
        txt += '0' + self.LINE_BREAK
        txt += 'no'  + self.LINE_BREAK
        txt += '0' + self.LINE_BREAK
        txt += 'no'  + self.LINE_BREAK
        txt += '0' + self.LINE_BREAK
        txt += 'no'  + self.LINE_BREAK
        txt += '0' + self.LINE_BREAK
        txt += 'no'  + self.LINE_BREAK
        txt += '1'  + self.LINE_BREAK
        txt += 'no'  + self.LINE_BREAK
        txt += 'no'  + self.LINE_BREAK
        txt += 'no'  + self.LINE_BREAK

        return txt

class SolidCellZone(FluentCellZone):

    """
    Class for modifying the properties of a Solid Cell Zone in fluent. 

    Parameters
    ----------
    name : str
            the string of the solid cell zone to modify in fluent
    
    Examples
    ---------
    
    .. code-block:: python
        
        scz = SolidCellZone('wall1')
        scz.add_constant_source(1e6)
        scz.change_material('aluminum')

    """
    def __init__(self,name: str) -> None:

        super().__init__(name,'solid')

class MeshMerge(TUIBase):
    """
    Class for merging zones in fluent
    
    Parameters
    ----------
    zone_list: List[str]
            a list of string names for the zones to merge

    Examples
    ---------
    
    .. code-block:: python
    
        mm = MergeMesh(['zone1','zone2','zone3'])

    """

    _prefix = 'mesh/modify-zones/merge-zones'
    def __init__(self,zone_list: List[str]):

        self.zone_list = zone_list

    def __str__(self):

        txt = self._prefix + self.LINE_BREAK
        for zone in self.zone_list:
            txt += zone + self.LINE_BREAK
        
        txt += ',' + self.LINE_BREAK
    
        return txt

class MeshFaceFuse(TUIBase):
    """
    Class for fusing faces in a mesh in fluent

    Parameters
    ----------
    face_list: List[str]
            a list of string names of the faces to fuse
    tolerance: float [optional]
            an optional keyword argument to supply a tolerance for the face fusing
    
    Examples
    --------

    .. code-block:: python

        mff = MeshFaceFuse(['myface','myface1'],tolerance = 0.000003)

    """
    _prefix = 'mesh/modify-zones/{}'
    def __init__(self,face_list: List[str],
                      fused_name: str,
                      tolerance = 0.05):

        self.face_list = face_list
        self.fused_name = fused_name
        self.tolerance = tolerance

    @property
    def tolerance_prefix(self):
        return self._prefix.format('matching-tolerance')
    
    @property
    def fuse_prefix(self):
        return self._prefix.format('fuse-face-zones')
    
    def format_tolerance(self):

        txt = self.tolerance_prefix + self.LINE_BREAK
        txt += str(self.tolerance) + self.LINE_BREAK
        return txt

    def format_face_list(self):

        txt = self.fuse_prefix + self.LINE_BREAK
        for face in self.face_list:
            txt += face + self.LINE_BREAK
        
        txt += ',' + self.LINE_BREAK
        txt += self.fused_name + self.LINE_BREAK

        return txt
    
    def __str__(self):

        return self.format_tolerance() + self.format_face_list()

        
class MeshTransform(TUIBase,ABC):

    _base_prefix = 'mesh/{}'
    transform_type = None

    def __init__(self):
        pass

    @property
    def prefix(self):
        return self._base_prefix.format(self.transform_type)
    
    @abstractmethod
    def transform(self) -> str:
        pass 

    def __str__(self):
        return self.transform()

class MeshTranslation(MeshTransform):

    """
    Class for translating the mesh

    Parameters
    ----------
    offset: np.ndarray
            the offset by which to transform the mesh by

    Examples
    --------

    .. code-block:: python

        mt = MeshTranslation([1,0,0])
    
    """

    def __init__(self,offset: np.ndarray) -> np.ndarray:

        self.transform_type = 'translate'
        offset = np.array(offset).squeeze()
        if offset.ndim != 1:
            raise ValueError('offset must be specified as a 1-D vector')
        
        if offset.shape[0] != 2 and offset.shape[0] !=3:
            raise ValueError('offset must be either a 2 or 3D vector')
        
        self.offset = list(offset)
    
    def transform(self) -> str:
        txt = self.prefix + self.LINE_BREAK
        for ov in self.offset:
            txt += str(ov) + self.LINE_BREAK

        return txt

class WarningResponse(TUIBase):

    def __init__(self,response = None):

        self.response = response
        
    
    def __str__(self):

        if self.response is None:
            return ''
        else:
            return self.response + self.LINE_BREAK

class MeshScale(MeshTransform):
    """
    Class for scaling the mesh

    Parameters
    ---------
    scale_factor: np.ndarray
            the x,y,z vector intended for scaling
    
    Examples
    --------

    .. code-block:: python

        ms = MeshScale([1,-1,1])
    """

    def __init__(self,scale_factor: np.ndarray,
                      warning_response = None) -> np.ndarray:

        self.transform_type = 'scale'
        scale_factor = np.array(scale_factor).squeeze()
        if scale_factor .ndim != 1:
            raise ValueError('scale factor must be specified as a 1-D vector')
        
        if scale_factor.shape[0] != 2 and scale_factor .shape[0] !=3:
            raise ValueError('scale factor must be either a 2 or 3D vector')

        self.scale_factor = list(scale_factor)
        self.warning_response = WarningResponse(response = warning_response)
    
    def transform(self) -> str:
        
        txt = self.prefix + self.LINE_BREAK
        for sf in self.scale_factor:
            txt += str(sf) + self.LINE_BREAK
        
        txt += str(self.warning_response)

        return txt

class MeshRotation(MeshTransform):
    """
    Class for rotating the mesh

    Parameters
    ----------
    rotation_angle : float
            the angle (in degrees) by which to rotate the meshes
    origin : np.ndarray
            the origin to perform the rotation around
    axis : np.ndarray
            the axis to perform the rotation around
    
    Examples
    --------

    .. code-block:: python

        mr = MeshRotation(5,[0,0,0])

    """
    def __init__(self,rotation_angle: float,
                      origin: np.ndarray,
                      axis: np.ndarray):

        """
        include some basic parsing to ensure that the origin 
        and axis are specified correctly as either 2 or 3 D 
        arrays so that there is no confusion and reduce the possibility
        for errors. Also ensure that the two arguments are the same length
        """

        self.transform_type = 'rotate'

        array_args = [origin,axis]
        array_names = ['origin','axis']
        array_parsed = []
        for aa,an in zip(array_args,array_names):
            array = np.array(aa).squeeze()
            if array.ndim != 1:
                raise ValueError('{} must be a 1-D array'.format(an))
            
            if array.shape[0] != 2 and array.shape[0] != 3:
                raise ValueError('{} must be specifided as a 2 or 3 dimensional vector'.format(an))
        
            array_parsed.append(list(aa))

        self.origin,self.axis = array_parsed

        if len(self.origin) != len(self.axis):
            raise ValueError('origin and axis arugments must have identical length')
        
        self.rotation_angle = rotation_angle
    
    def transform(self) -> str:
        """
        format the arguments into string interpretable by fluent
        """
        
        txt = self.prefix + self.LINE_BREAK
        txt += str(self.rotation_angle) + self.LINE_BREAK
        for ov in self.origin:
            txt += str(ov) + self.LINE_BREAK
        
        for av in self.axis:
            txt += str(av) + self.LINE_BREAK
        
        
        return txt
        

class DeleteAllInterface(TUIBase):

    """
    Class for deleting all mesh iterfaces
    
    Parameters
    ----------
    None

    Examples
    ---------

    .. code-block:: python
        
        dai = DeleteAllInterface()
        str(dai)

    """

    _prefix = 'define/mesh-interfaces/delete-all'

    def __init__(self):
        pass

    def __str__(self):
        return self._prefix + self.LINE_BREAK + 'yes' + self.LINE_BREAK
    
class MeshInterface(TUIBase):
    """
    Class for constructing a mesh interface between two or more boundary conditions
    or zones in a mesh

    Parameters
    ---------- 
    zone_list : List[str]
            a list of strings designating the zones to be combined via the mesh interface

    Examples
    --------
    .. code-block:: python

        mi = MeshInterface(['my-zone','my-zone:1'])
        str(mi)

    """
    _prefix = 'define/mesh-interfaces/create'

    def __init__(self,zone_list: Union[List[str],str],
                      interface_prefix = 'intf',
                      exclude = False):

        self.zone_list = zone_list
        self.interface_prefix = interface_prefix
        self.exclude = exclude
    
    def _format_defined_interface(self):

        txt = self._prefix + self.LINE_BREAK
        txt += self.interface_prefix + self.LINE_BREAK
        if self.exclude:
            txt += 'no' + self.LINE_BREAK
        
        for zone in self.zone_list:
            txt += zone + self.LINE_BREAK
        
        txt += ',' + self.LINE_BREAK
        txt += 'no' + self.LINE_BREAK
        return txt
    
    def _format_auto_interface(self):

        txt = self._prefix + self.LINE_BREAK
        txt += self.interface_prefix + self.LINE_BREAK
        txt += 'yes' + self.LINE_BREAK
        txt += 'no' + self.LINE_BREAK

        return txt

    
    def __str__(self):

        if isinstance(self.zone_list,list):
            return self._format_interface()
        
        elif isinstance(self.zone_list,str) and self.zone_list.lower() == 'auto':
            return self._format_auto_interface()
        
        else:
            raise ValueError('cannot parse zone list to mesh interface command')
        

class UDF(TUIBase):

    """
    class for representing a UDF for loading into boundary conditions in fluent. Meant primary
    to be used in conjunction with boundary conditions i.e. MassFlowInlet,PressureOutlet ect...

    
    Parameters
    -----------
    file_name : str
            the name of the udf file
    udf_name : str
            the name of the udf in fluent
    data_name : str
            the name of the data name in fluent
    condition_name : str
            the name of the condition (i.e. convection_coefficient, 
            heat_flux, ect.. the UDF is intended to be applied to)
    compile : bool
             default False - option to compile the UDF at runtime

    Examples
    ---------
    .. code-block:: python

        udf = UDF('test.c','myudf','mydata','heat_flux')
        print(udf)
        > heat_flux
        > yes
        > yes
        > myudf
        > "mydata"
    
    """

    _compile_prefix = 'define/user-defined/compiled-functions/compile'
    _load_prefix = 'define/user-defined/compiled-function/load'
    _unload_prefix = 'define/user-defined/compiled-function/unload'

    def __init__(self,file_name = None,
                      data_name = None,
                      condition_name = None,
                      profile_name = 'udf',
                      udf_lib = 'random',
                      case_dir = None,
                      compile = False,
                      system_type = 'linux') -> None:
        
        self.system_type = system_type
        self.file_name = file_name

        if udf_lib.lower() == 'random':
            self.FILE_PREFIX = 'udflib'
            self.random_character_length = 5
            self.ext = ''
            self.udf_lib = self.generate_random_file_name()
        else:
            self.udf_lib = udf_lib
        
        self.profile_name = profile_name
        self.condition_name = condition_name
        self.compile = compile
        self._compile_call = self.compile

        self.establish_os()
        self.check_compilation(file_name)
        if case_dir is None:
            self.case_dir = os.getcwd()
        else:
            self.case_dir = case_dir
        
        if file_name is None and data_name is None:
            raise ValueError('cannot specify udf from no file_name or data_name')
            
        if file_name is not None:
            _data_name = self.infer_data_name_from_file(file_name)

        if data_name is not None:
            split_tuple = data_name.split('::')
            if len(split_tuple) == 1:
                self.__data_name = data_name
            else:
                self.__data_name = split_tuple[0]
                self.udf_lib = split_tuple[1]
        else:
            self.__data_name = _data_name

    @staticmethod
    def infer_data_name_from_file(file_name : str):
        """
        if the file is available, infer the data_name input into fluent
        from this file
        """
        
        with open(file_name,'r') as file:
            raw_text = file.read()
        
        define_macros = re.finditer('DEFINE_',raw_text)

        for dm in define_macros:
            raw = raw_text[dm.end():]
            arguments = [arg.strip() for arg in 
                        raw[raw.find('(')+1:raw.find(')')].split(',')]
            break
    
        return arguments[0]
            
    def check_compilation(self, file_name : str):
        """
        of compilation is required, check to see if a file exists to
        execute the compilation with
        """

        if self.compile and not os.path.exists(file_name):
            raise FileNotFoundError('file: {} could not be found. Cannot\
                     compile at runtime'.format(file_name))
        
        self._compile_call = True
         
    @property
    def case_dir(self):
        return self.__case_dir
    
    @case_dir.setter
    def case_dir(self,path: Union[str,PurePath]):
        self.__case_dir = self.Path(path)
    
    @property
    def data_name(self):
        return r'"' + self.__data_name + '::' +  self.udf_lib + r'"'

    def establish_os(self) -> None:
        """
        establish the os for which to use the platform
        dependent path for
        """
        os_name = sys.platform
        if os_name == 'win32' or os_name == 'win64':
            self.Path = WindowsPath
        elif os_name == 'linux' or os_name == 'posix':
            self.Path = PosixPath
        else:
            raise OSError('not configured to work on non-linux or windows systems')

    def _format_enable_udf(self):
        """
        string sequence to enable using udf
        """
        text = 'yes' + self.LINE_BREAK
        text += 'yes' + self.LINE_BREAK
        text += self.profile_name + self.LINE_BREAK
        text += self.data_name + self.LINE_BREAK

        return text

    def _fluent_compile_sequence(self, file_name : str) -> str:
        """
        return a string with the compliation sequence in fluent
        """
        text = self._unload_prefix + self.LINE_BREAK + ',' +  self.LINE_BREAK
        text += self._compile_prefix + self.LINE_BREAK
        text += self.udf_lib + self.LINE_BREAK
        text += 'yes' + self.LINE_BREAK
        text += file_name + self.LINE_BREAK
        text += ',' + self.LINE_BREAK + ',' + self.LINE_BREAK
        return text
    
    def _fluent_load_sequence(self, file_name : str) -> str:
        """
        return a string with the fluent loading sequence
        """
        text = self._load_prefix + self.LINE_BREAK
        text += self.udf_lib + self.LINE_BREAK
        return text

    def _format_linux_compile(self, file_name: str,
                                    full_file_path : str):
        
        """
        compile and load a udf on a linux system
        """
        if not os.path.exists(self.case_dir):
            raise FileExistsError('case folder : {} does not exist'.format(self.case_dir)) 
        
        src_file = self.case_dir.joinpath(file_name)
        
        if not os.path.exists(src_file):
            shutil.copy2(full_file_path,src_file)

        return self._fluent_compile_sequence(file_name) +\
               self._fluent_load_sequence(file_name)        
        
    def format_compile_udf(self):
        """
        format string sequence to compile udf if required
        this is called in the boundary condition prior
        to any formatting of the boundary condition 
        specification
        """
        #move file to directory with case file
        txt = ''
        
        _,file_name = os.path.split(self.file_name)
    
        if self.system_type == 'linux':
            txt += self._format_linux_compile(file_name,self.file_name)
        else:
            raise NotImplementedError('havent implemented runtime compilation for non-posix systems')

        return txt

    def __str__(self):
        """
        string sequence to enable udf
        """
        return self._format_enable_udf()

def udf_setter(property_setter : callable) -> callable:
    """
    wrapper to enable setting udf properties directly. Will infer
    the condition_name of the udf from the property being set
    """
    
    def wrapped_setter(self,udf : Union[UDF,float]):
        if isinstance(udf, UDF):
            if udf.condition_name is None:
                udf.condition_name = property_setter.__name__
            
            self.add_udf(udf)
            property_setter(self,-np.inf)
        else: 
            property_setter(self,udf)

    return wrapped_setter 
        
def udf_property(condition_name: str) -> callable:
    """
    decorator meant to enable all conditions 
    that can have udf profile to have one 
    
    Parameters
    ----------
    condition_name : str
            the condition_name that could be enabled

    Examples
    --------
    .. code-block:: python

        @udf_property('t0')
        def temperature(self):
            return self.__temperature 
    
    this will do the following in the "set" menu (define/boundary-conditions/set)
    1. if there is no udf
    > t0
    > no
    > value of temperature
    2. if there is a udf

    """
    
    def udf_enabled_condition(condition: callable) -> callable:

        """
        wrapper for a udf enabled condition.if the udf is None, the condition is 
        returned. If the udf is not None then the text for the udf is returned as 
        well as the condition. This is clearly meant to function within a class that 
        has a property udf, which is a dictinoary that can be identified using the 
        condition_name string.

        Parameters
        ----------
        condition : callable
                a callable with the specifications for the condition
        """
        @property
        def enabled_condition(self) -> str:

            _condition_names = [condition_name,
                                condition.__name__,
                                condition.__name__.replace('_','-')]
            
            for cname in _condition_names:

                try:
                    #found a udf with matching condition_name
                    self.decorated_list.append(condition.__name__)
                    return condition_name + self.LINE_BREAK + str(self.udf[cname])
                except KeyError:
                    pass
            
            output = condition(self)
            if output is None:
                return output
            else:
                self.decorated_list.append(condition.__name__)
                
                return condition_name + self.LINE_BREAK +\
                       'no' +self.LINE_BREAK +\
                       str(output) + self.LINE_BREAK
            
        return enabled_condition
    
    return udf_enabled_condition

def boolean_property(cls_property: callable) -> callable:
    """
    Convinience function for turning boolean properties into 
    yes/no answers for the TUI interface
    """
    @property
    def wrapped_property(self):

        tui_name = cls_property.__name__.replace('_','-')
        tui_syntax = tui_name + self.LINE_BREAK + '{}' + self.LINE_BREAK
        if cls_property(self):
            return tui_syntax.format('yes')
        else:
            return tui_syntax.format('no')

    return wrapped_property

class FluentBoundaryCondition(ABC,TUIBase):
    """
    Base class for all fluent boundary conditions. This class contains many of the basic 
    routines required for parsing in other boudnary conditions, and does some basic
    parsing and checking of inputs as well

    Parameters
    ------------
    boundary_type: the type of the boundary, will raise ValueError if not in ALLOWABLE_BOUNDARY_TYPES
    models: a list of models that are being used in Fluent, will raise ValueError if not in ALLOWABLE_VISCOUS_MODELS
            or not in ALLOWABLE_MODELS
    solver: the solver that is being used in Fluent. Will raise ValueError if not in ALLOWABLE_SOLVERS
    reference_frame: whether or not the reference frame is absolute

    Methods
    -------------
    add_udf() - add a udf to the boundary condition
    remove_udf() - remove a udf from the boundary condition

    """
    _prefix = '/define/boundary-conditions/set/'
    ALLOWABLE_SOLVERS = ['pressure-based','density-based']
    ALLOWABLE_BOUNDARY_TYPES = ['mass-flow-inlet',
                                'pressure-outlet',
                                'wall',
                                'velocity-inlet',
                                'turbulence_specification']

    ALLOWABLE_VISCOUS_MODELS = ['ke-standard','kw-standard','ke-realizable','ke-rng','geko','kw-geko','laminar']
    ALLOWABLE_MODELS = ['energy','viscous'] 
    ALLOWABLE_MODELS += ['viscous/' + vm for vm in ALLOWABLE_VISCOUS_MODELS]
    ALLOWABLE_REFERENCE_FRAME = ['absolute',
                                 'relative to adjacent cell zone']
    
    def __init__(self,name: str,
                      boundary_type: str,
                      models: list,
                      defaults = {},
                      **kwargs):
        
        #check to ensure the models are allowed
        for model in models:
            if model not in self.ALLOWABLE_VISCOUS_MODELS and model not in self.ALLOWABLE_MODELS:
                raise ValueError('model: {} is not allowed'.format(model))
        
        #check to ensure the boundary type is allowed
        if boundary_type not in self.ALLOWABLE_BOUNDARY_TYPES:
            raise ValueError('Cannot parse boundary of type: {}'.format(boundary_type))
        
        self._assign_default_attributes(defaults,**kwargs)
        self.property_methods = self.determine_properties()
        self.decorated_list = []
        self.btype = boundary_type
        self.name = name
        self.models = models
        self.__udf = {}
        
    @property
    def udf(self):
        return self.__udf
    
    @udf.setter
    def udf(self,udf):
        self.__udf = udf
    
    def enter_statement(self):
        return self._prefix + self.btype + self.LINE_BREAK + '(' + self.name + ')' + self.LINE_BREAK        

    def exit_statement(self):
        return self.EXIT_CHAR
    
    def add_udf(self,new_udf: UDF) -> None:
        """
        add a new udf to the udf dictionary
        """
        if new_udf.condition_name is None:
            raise ValueError('The condition name cannot be none if adding udf to boundary condition')
        
        if new_udf.condition_name not in self.udf:
            self.udf[new_udf.condition_name] = new_udf
        else:
            raise ValueError('Cannot have multiple udfs with the same condition name for the same boundary')

    def remove_udf(self,udf_condition_name: str) -> UDF:
        """
        remove a UDF by condition name and return that UDF
        """
        try:
            self.udf.pop(udf_condition_name)
        except KeyError as ke:
            raise KeyError('Cannot find UDF with condition name:{} in udf dictionary'.format(udf_condition_name))

    def format_pre_udf(self) -> str:
        """
        all of the udf_properties must be iterated through. If they have a UDF
        associated with them, set the value to -np.inf, and if requested for compilation
        add the necessary text to compile the udf 
        """

        _compile_text = ''
        for property_name in self.property_methods:
            fmt1 = property_name.replace('_','-')
            fmt2 = property_name.replace('-','_')
            
            for fmt_property in [fmt1,fmt2]:
                #assign values of -1 to all properties with udf
                if fmt_property in self.udf:
                    self.__setattr__(property_name,-np.inf)
                    if self.udf[fmt_property].compile and self.udf[fmt_property]._compile_call:
                        _compile_text += self.udf[fmt_property].format_compile_udf()
                        self.udf[fmt_property]._compile_call = False

                    break

        return _compile_text

    def specification_conditions(self,prefix = '') -> str:
        """
        deals with all boundary conditions which may be set like: 
        > [name]
        > [udf? (y/n)]
        > [value]
        this is fairly generic, and thus can be set in the base class
        """

        txt = ''
        self.decorated_list = []
        
        for property_name in self.property_methods:
            if (property_name == 'temperature' and 'energy' in self.models)\
                or property_name != 'temperature':
                try:
                    new_text = prefix + self.__getattribute__(property_name)
                    if property_name in self.decorated_list:
                        txt += new_text
                except (TypeError,AttributeError):
                    pass
            
        return txt

    @abstractmethod
    def format_conditions(self) -> str:
        """
        meant to deal with all formatting of conditions
        that are not udf enabled, especially those that
        determine which values must be specified. This is unique
        to each boundary condition.
        """
        pass

    @abstractmethod
    def format_boundary_condition(self) -> str:

        pass

    def __call__(self):
        return self.format_boundary_condition()
    
    @classmethod
    def determine_properties(cls) -> List[str]:
        """
        Helper function for determining all properties 
        in a (sub)class of FluentBoundaryCondition that are properties

        .. code-block:: python
            
            @udf_property("prop_name")
            def prop_name(self):
                .
                .

        .. code-block:: python

            @property
            def direction_vector(self):
                .
                .
        
        Parameters
        ----------
        None

        Returns
        --------
        property_list : List[str]
                a list of strings that can be acsessed with the
                __getattribute__() method that are properties
        """

        class_line = [cls_ for cls_ in cls.mro() if 'abc.ABC' not
                      in str(cls_) and 'object' not in str(cls_)]
        
        property_list = []
        for cls_ in class_line:
            for attr_name,attr_value in cls_.__dict__.items():
                if isinstance(attr_value,property):
                    property_list.append(attr_name)
        
        property_list.remove('udf')
        return property_list
    
    def _assign_default_attributes(self,defaults,**kwargs) -> None:
        """
        helper function for assigning default keyword arguments to
        the corresponding attributes of the boundary condition class
        """

        for key in defaults:
            if key not in kwargs:
                self.__setattr__(str(key),defaults[key])
            else:
                self.__setattr__(str(key),kwargs[key])

class FluentSolidBoundaryCondition(FluentBoundaryCondition):
    
    def __init__(self,name: str,
                      boundary_type: str,
                      models: list,
                      defaults = {},
                      **kwargs):
        
        super().__init__(name,boundary_type,models,
                        defaults = defaults,**kwargs)    

    def format_boundary_condition(self) -> str:
        """
        Main Design pattern conglommeration here. Boundary conditions
        all consist of 
        (1) configuart
        """
        txt = self.format_pre_udf()
        txt += self.enter_statement()
        txt += self.format_conditions()
        txt += self.specification_conditions()
        txt += self.exit_statement()

        return txt
    
    def format_conditions(self):

        return super().format_conditions()
    
class WallBoundaryCondition(FluentSolidBoundaryCondition):

    """
    Wall boundary condition representation. Properties with a star may be set after instantation. 
    UDFS may be applied to a particular property of the wall following the example below.

    Does not support:
    
    1. via-mapped-interface
    2. via-system-coupling

    Parameters
    ----------
    name : str
            the name of the wall boundary condition as a string
    models : list
            the models used 
    q_dot : float | *
            heat generation
    heat_flux : float | *
            heat flux
    convective_heat_transfer_coefficient : float | *
            convective heat transfer coefficient
    wall_temperature : float | *
            temperature of the wall
    tinf : float | *
            temperature used for the convective heat transfer coefficient
    caf : float | *
            convective augmentation factor
    trad : float | *
            the temperature used for calculating radiative heat transfer
    ex_emiss : float | *
            emissivity of the surface
    thermal_network : bool | *
            use thermal network or not
    planar_conduction : float | *
            use planar conduction or not

    Examples
    --------
    .. code-block:: python

        wall = WallBoundaryCondition('heated-surf',['viscous','energy'])
        wall.heat_flux = 10e3
        wall.trad = 1e4
        wall.ex_emiss = 0.5
        wall.convective_heat_transfer_coefficient = 10
        wall.tinf = 500

        print(wall())
    """
    
    DEFAULTS = {'wall_thickness':None,
                'q_dot': None,
                'heat_flux':None,
                'convective_heat_transfer_coefficient':None,
                'wall_temperature': None,
                'tinf': None,
                'caf': None,
                'trad': None,
                'ex_emiss':None,
                'thermal_network':None,
                'planar_conduction':False}

    def __init__(self,name: str,
                      models: list,
                      defaults = {},
                      **kwargs):

        for key,value in self.DEFAULTS.items():
            defaults[key] = value
        
        super().__init__(name,'wall',models,defaults = defaults,**kwargs)


    @udf_property('q-dot')
    def q_dot(self):
        return self.__q_dot
    
    @q_dot.setter
    @udf_setter
    def q_dot(self,qd: float):
        self.__q_dot = qd
    
    @udf_property('heat-flux')
    def heat_flux(self):
        return self.__heat_flux
    
    @heat_flux.setter
    @udf_setter
    def heat_flux(self,hf: float):
        self.__heat_flux = hf
    
    @udf_property('convective-heat-transfer-coefficient')
    def convective_heat_transfer_coefficient(self):
        return self.__convective_heat_transfer_coefficient
    
    @convective_heat_transfer_coefficient.setter
    @udf_setter
    def convective_heat_transfer_coefficient(self,chtc: float):
        self.__convective_heat_transfer_coefficient = chtc

    @udf_property('tinf')
    def tinf(self):
        return self.__tinf
    
    @tinf.setter
    @udf_setter
    def tinf(self,t: float):
        self.__tinf = t
    
    @udf_property('temperature')
    def wall_temperature(self):
        return self.__wall_temperature
    
    @wall_temperature.setter
    @udf_setter
    def wall_temperature(self,wt: float):
        self.__wall_temperature =wt
    
    @udf_property('caf')
    def caf(self):
        return self.__caf
    
    @caf.setter
    @udf_setter
    def caf(self,caf:float):
        self.__caf = caf

    @udf_property('trad')
    def trad(self):
        return self.__trad
    
    @trad.setter
    @udf_setter
    def trad(self,tr: float):
        self.__trad = tr
    
    @udf_property('ex-emiss')
    def ex_emiss(self):
        return self.__ex_emiss
    
    @ex_emiss.setter
    @udf_setter
    def ex_emiss(self,ee: float):
        self.__ex_emiss = ee
    
    @boolean_property
    def planar_conduction(self):
        return self.__planar_conduction
    
    @planar_conduction.setter
    def planar_conduction(self,pc: bool):
        self.__planar_conduction = pc
    
    def format_thermal_bc(self):

        mapping = {'heat-flux':[self.heat_flux],
                   'convection': [self.convective_heat_transfer_coefficient,self.tinf,self.caf],
                   'radiation': [self.ex_emiss,self.trad],
                   'network': [self.thermal_network]}
        
        _thermal_bc = None
        for thermal_bc, clist in mapping.items():
            
            try:
                #can't convert string to floats, so will fail
                #if boundary conditions are present
                np.array(clist,dtype = 'float')
            except ValueError:
                if _thermal_bc is not None:
                    _thermal_bc = 'mixed'
                    break
                else:
                    _thermal_bc = thermal_bc
        
        if _thermal_bc is None:
            return ''
        else:
            return 'thermal-bc' + self.LINE_BREAK + 'yes' +\
                    self.LINE_BREAK + _thermal_bc + self.LINE_BREAK

    def format_wall_thickness(self):
        if self.wall_thickness is not None:
            return 'wall-thickness' + self.LINE_BREAK + str(self.wall_thickness) + self.LINE_BREAK
        else:
            return ''
        
    def format_conditions(self):

        text = self.format_thermal_bc()
        text += self.format_wall_thickness()
        text += self.planar_conduction 
        return text
        
class FluentFluidBoundaryCondition(FluentBoundaryCondition):
    """
    Base class for Fluid Boundary Conditions in Fluent. This class is inherited
    by all Fluid Boundary Conditions

    Parameters
    ----------
    temperature : float | *
            only used if energy is in models. sets the temperature at the 
            boundary, defaults to 300
    frame_of_reference: str | *
            choice of absolute or relative, defaults to absolute
    direction_vector : list | *
        optional specfication of the direction vector, must be specified as a
        1D array with 1-3 components x,y,z. Defaults to None, in which case
        the mass flow is normal to the boundary.
    """ 

    FLUID_DEFAULTS = {'temperature': None,
                      'direction_vector': None,
                      'frame_of_reference':'absolute'}

    def __init__(self,name:str,
                      boundary_type: str,
                      models: list,
                      turbulence_model: str,
                      defaults = {},
                      **kwargs):
        
        for key,value in self.FLUID_DEFAULTS.items():
            defaults[key] = value
        
        super().__init__(name,boundary_type,models,defaults = defaults,**kwargs)

        self.__turbulence_model = _assign_turbulence_model(turbulence_model,**kwargs)
    
    @property
    def turbulence_model(self):
        return self.__turbulence_model

    @udf_property('t0')
    def temperature(self):
        return self.__t0

    @temperature.setter
    def temperature(self,t):
        self.__t0 = t
    
    @property
    def direction_vector(self) -> np.ndarray:
        return self.__direction_vector
    
    @direction_vector.setter
    def direction_vector(self,dv : Union[np.ndarray,list,tuple]):
        
        if dv is not None:
            self.__direction_vector = np.array(dv).squeeze()
            if self.__direction_vector.ndim != 1:
                raise ValueError('direction vector must be specified by 1D array')
            if self.__direction_vector.shape[0] < 1 or self.__direction_vector.shape[0] >3:
                raise ValueError('direction vector must be between length 1 and 3')
        else:
            self.__direction_vector = dv

    @property
    def frame_of_reference(self) -> str:
        return self.__frame_of_reference

    @frame_of_reference.setter
    def frame_of_reference(self,frm : str) -> None:
        _frm = frm.lower()
        if _frm not in self.ALLOWABLE_REFERENCE_FRAME:
            txt = [text  + '\n' for text in self.ALLOWABLE_REFERENCE_FRAME]
            raise ValueError('frame of reference must\
             be one of \n {}. \n not : {}'.format(txt,_frm))
        
        
        self.__frame_of_reference = _frm
               
    def format_direction_spec(self,
                              direction_str = ['ni','nj','nk'],
                              direction_spec = 'direction-spec') -> str:
        """
        all direction vectors follow the same format
        if the direction vector is None, specify as normal the boundary.
        otherwise, specify the direction vector
        """
        if direction_spec is None:
            txt = ''
        else:
            txt = direction_spec + self.LINE_BREAK
        
        if self.direction_vector is None:
            return txt + 'no' + self.LINE_BREAK + 'yes' + self.LINE_BREAK
        else:
            if direction_spec is not None:
                txt += 'yes' + self.LINE_BREAK
            direction_vector = list(self.direction_vector)
            for dv,ds in zip(direction_vector,direction_str):
                txt += ds + self.LINE_BREAK + 'no' + self.LINE_BREAK +\
                       str(dv) + self.LINE_BREAK
            
            return txt

    def format_frame_of_reference(self) -> str:
        """
        all frame of references have a generic format
        """
        txt = 'frame-of-reference' + self.LINE_BREAK
        if self.frame_of_reference == 'absolute':
            return txt + 'yes' + self.LINE_BREAK
        else:
            return txt + 'no' + self.LINE_BREAK + 'yes' + self.LINE_BREAK

    def format_turbulent_quantities(self) -> str:
        """
        just calls the turbulence_model format_spec() method
        """
        return self.turbulence_model.specification_conditions()

    def format_boundary_condition(self) -> str:
        """
        Main Design pattern conglommeration here. Boundary conditions
        all consist of 
        (1) configuart
        """
        txt = self.format_pre_udf()
        txt += self.enter_statement()
        txt += self.format_conditions()
        txt += self.specification_conditions()
        txt += self.format_turbulent_quantities()
        txt += self.exit_statement()

        return txt

class NoTurbulenceModel:

    def __init__(self,*args,**kwargs):
        pass

    def format_boundary_condition(self):
        return ''
    
    def format_conditions(self):
        return ''
    
    def specification_conditions(self):
        return ''

class TwoEquationTurbulentBoundarySpecification(FluentFluidBoundaryCondition):

    TET_DEFAULTS = {'turbulent_kinetic_energy':None,
                    'turb_intensity':None,
                    'turb_length_scale':None,
                    'turb_viscosity_ratio':None,
                    'turb_hydraulic_diam':None}

    def __init__(self,model: str,defaults = {}, **kwargs):

        for key,value in self.TET_DEFAULTS.items():
            defaults[key] = value
        
        super().__init__(model[0],
                         'turbulence_specification',
                          model,'viscous',defaults = defaults,
                          temperature = None,**kwargs)

    @udf_property('turbulent-kinetic-energy')
    def turbulent_kinetic_energy(self) -> float:
        return self.__turbulent_kinetic_energy
    
    @turbulent_kinetic_energy.setter
    @udf_setter
    def turbulent_kinetic_energy(self,tke) -> None:
        self.__turbulent_kinetic_energy = tke
    
    @abstractmethod
    def format_conditions(self) -> str:
        
        if self.turb_intensity is not None and self.turb_length_scale is not None:
            return 'no' + self.LINE_BREAK + 'yes' + self.LINE_BREAK
        elif self.turb_intensity is not None and self.turb_viscosity_ratio is not None:
            return 'no' + self.LINE_BREAK + 'no' + self.LINE_BREAK +\
                   'yes' + self.LINE_BREAK
        elif self.turb_intensity is not None and self.turb_hydraulic_diam is not None:
            return 'no' + self.LINE_BREAK + 'no' + self.LINE_BREAK +\
                    'no' + self.LINE_BREAK + 'yes' + self.LINE_BREAK 
        else:
            raise ValueError('Cannot format turbulent conditions based upon specified values')

    def specification_conditions(self, prefix = '') -> str:
        text = prefix + 'turb-intensity' + self.LINE_BREAK + \
                   str(self.turb_intensity) + self.LINE_BREAK
        
        if self.turb_intensity is not None and self.turb_length_scale is not None:
            return  text +\
                    prefix + 'turb-length-scale' + self.LINE_BREAK +\
                    str(self.turb_length_scale) + self.LINE_BREAK

        elif self.turb_intensity is not None and self.turb_viscosity_ratio is not None:
            return text +\
                    prefix +  'turb-viscosity-ratio' + self.LINE_BREAK +\
                    str(self.turb_viscosity_ratio) + self.LINE_BREAK
                
        elif self.turb_intensity is not None and self.turb_hydraulic_diam is not None:
            return text +\
                    prefix + 'turb-hydraulic-diam' + self.LINE_BREAK +\
                    str(self.turb_hydraulic_diam) + self.LINE_BREAK
        else:
            return super().specification_conditions(prefix = prefix)
    
    def format_boundary_condition(self):

        return self.format_conditions()+\
               self.specification_conditions()

class StandardKEpsilonSpecification(TwoEquationTurbulentBoundarySpecification):

    SKE_DEFAULTS = {'turbulent_dissipation_rate':None}

    def __init__(self,**kwargs):

        super().__init__(['ke-standard'],defaults = self.SKE_DEFAULTS,**kwargs)
        for key,value in self.SKE_DEFAULTS.items():
            self.TET_DEFAULTS[key] = value
        
    @udf_property('turbulent-dissipation-rate')
    def turbulent_dissipation_rate(self):
        return self.__turbulent_dissipation_rate

    @turbulent_dissipation_rate.setter
    @udf_setter
    def turbulent_dissipation_rate(self,tdr):
        self.__turbulent_dissipation_rate = tdr
    
    def format_conditions(self):
        txt = 'ke-spec' + self.LINE_BREAK
        if self.turbulent_dissipation_rate is not None and self.turbulent_kinetic_energy is not None:
            return txt + 'yes' + self.LINE_BREAK
        else:
            return txt + super().format_conditions()
    
class StandardKOmegaSpecification(TwoEquationTurbulentBoundarySpecification):

    SKO_DEFAULTS = {'specific_dissipation_rate': None}

    def __init__(self,*args,**kwargs):

        super().__init__(['kw-standard'],defaults = self.SKO_DEFAULTS,**kwargs)
        for key,value in self.SKO_DEFAULTS.items():
            self.TET_DEFAULTS[key] = value
    
    @udf_property('specific-dissipation-rate')
    def specific_dissipation_rate(self) -> str:
        return self.__specific_dissipation_rate
    
    @specific_dissipation_rate.setter
    @udf_setter
    def specific_dissipation_rate(self,sdr: float):
        self.__specific_dissipation_rate = sdr

    def format_conditions(self):
        txt = 'ke-spec' + self.LINE_BREAK
        if self.specific_dissipation_rate is not None and self.turbulent_kinetic_energy is not None:
            return txt + 'yes' + self.LINE_BREAK
        else:
            return txt + super().format_conditions()

def _assign_turbulence_model(model:str,**kwargs) -> TwoEquationTurbulentBoundarySpecification:

    allowable_kwargs = ['turbulent_kinetic_energy',
                         'turb_intensity',
                         'turb_length_scale',
                         'turb_viscosity_ratio',
                         'turb_hydraulic_diam',
                         'turbulent_dissipation_rate',
                         'specific_dissipation_rate']

    _kwargs = {key: value for key,value in kwargs.items() if key in allowable_kwargs}

    class_assignment = {'ke-standard':StandardKEpsilonSpecification,
                        'ke-realizable':StandardKEpsilonSpecification,
                        'ke-rng': StandardKEpsilonSpecification,
                        'kw-standard':StandardKOmegaSpecification,
                        'kw-sst':StandardKOmegaSpecification,
                        'kw-bsl': StandardKOmegaSpecification,
                        'kw-geko':StandardKOmegaSpecification,
                        'geko':StandardKOmegaSpecification,
                        'viscous':NoTurbulenceModel,
                        'laminar': NoTurbulenceModel}

    try:
        return class_assignment[model](**_kwargs)

    except KeyError:
        raise ValueError('cannot identify the requested model: {}'.format(model))

class MassFlowInlet(FluentFluidBoundaryCondition):

    """
    Mass flow rate boundary condition class. Allows for specification of either the mass flux
    or the mass flow rate. Specification of the turbulence model is required. Starred 
    arguments are keyword arguments that act as inputs for the fluent journal. mass_flow 
    and mass_flux default to None, and only one of these variables is permitted to not be None
    to avoid specification of both.

    Parameters
    ----------
    name : str
            the name of the mass flow inlet boundary condition
    models : list
            a list of the models used, does not require specification of temperature
    turbulence_model: str
            the turbulence model used, see allowable turbulence models
    mass_flow : float | *
            the mass flow rate defaults to None
    mass_flux : float | *
            the mass flux defaults to None
    initial_gauge_pressure : float | *
            the initial pressure defaults to 0

    Examples
    --------
    .. code-block:: python

        mfi = MassFlowInlet('mass-flow-inlet',['viscous','energy'],'ke-standard')
        mfi.mass_flux = 1.0
        mfi.turbulence_model.turb_intensity = 1.0
        mfi.turbulence_model.turb_length_scale = 5.0
        print(mfi())
    """

    DEFAULTS = {'mass_flow': None,
                'mass_flux': None,
                'initial_gauge_pressure':0}
                
    def __init__(self,name: str,
                      models: list,
                      turbulence_model: str,
                      **kwargs):

        fkwargs = {kw: val for kw,val in kwargs.items() if kw not in self.DEFAULTS}
        super().__init__(name,'mass-flow-inlet',models,turbulence_model,**fkwargs)
        self._assign_default_attributes(self.DEFAULTS,**kwargs)


    @udf_property('mass-flow')
    def mass_flow(self):
        return self.__mass_flow
    
    @udf_property('mass-flux')
    def mass_flux(self):
        return self.__mass_flux

    @udf_property('supersonic/initial-gauge-pressure')
    def initial_gauge_pressure(self):
        return self.__initial_gauge_pressure
    
    @mass_flow.setter
    @udf_setter
    def mass_flow(self,mfr):
        self.__mass_flow = mfr
    
    @mass_flux.setter
    @udf_setter
    def mass_flux(self,mf):
        self.__mass_flux = mf

    @initial_gauge_pressure.setter
    @udf_setter
    def initial_gauge_pressure(self,ip):
        self.__initial_gauge_pressure = ip
    
    def format_flow_spec(self) -> str:

        text = 'flow-spec' + self.LINE_BREAK

        if self.mass_flux is not None and self.mass_flow is not None:
            raise ValueError('both mass flow rate and mass flux cannot be specified')
        
        elif self.mass_flux is None and self.mass_flow is None:
            raise ValueError('both mass flow rate and mass flux cannot be None')
        
        elif self.mass_flux is None and self.mass_flow is not None:
            
            return text + 'yes' + self.LINE_BREAK
        
        else:
            return text + 'no' + self.LINE_BREAK + 'yes' + self.LINE_BREAK

    def format_conditions(self) -> str:
        """
        Logic Notes
        ----------
        """

        txt = self.format_direction_spec()
        txt += self.format_frame_of_reference()
        txt += self.format_flow_spec()
        txt += self.turbulence_model.format_conditions()

        return txt
    
class PressureOutlet(FluentFluidBoundaryCondition):
    """
    A pressure outlet boundary condition class. Similar to other boundary conditions,
    requires specification of a name, models simulated and the turbulence model.
    The pressure and temperature are the only values that impact input into the TUI and the
    pressure defaults to None. This will create an error if left unspecified, so this must be modified
    during instantation or directly on the instance.

    Does not permit specification of targeted-mf-boundary at the moment

    Parameters
    ---------
    name : str
            the name of the mass flow inlet boundary condition
    models : list
            a list of the models used, does not require specification of temperature
    turbulence_model: str
            the turbulence model used, see allowable turbulence models
    pressure : float | *
            the pressure at the outlet
    p_profile_multiplier: float | *
            multiplier for the pressure profile
    avg_press_spec : float | *
            whether to activate the average pressure specification or not
    radial : float | *
            activate radial pressure distribution

    Examples
    ---------
    .. code-block:: python 

        po = PressureOutlet('pressure-outlet',['viscous','energy'],'ke-standard',pressure = 1e5)
        po.turbulence_model.turbulent_kinetic_energy = 1.0
        po.turbulence_model.turbulent_dissipation_rate = 5.0
        print(po())
    """

    DEFAULTS = {'pressure': None,
                'p_profile_multiplier': 1.0,
                'avg_press_spec': False,
                'radial':False}

    def __init__(self,name:str,
                      models: list,
                      turbulence_model: str,
                      **kwargs):

        super().__init__(name,'pressure-outlet',models,
                         turbulence_model,defaults = self.DEFAULTS,**kwargs)
        
    @udf_property('gauge-pressure')
    def pressure(self):
        return self.__pressure
    
    @pressure.setter
    @udf_setter
    def pressure(self,p):
        self.__pressure = p

    @boolean_property
    def avg_press_spec(self) -> str:
        return self.__avg_press_spec
    
    @avg_press_spec.setter
    @udf_setter
    def avg_press_spec(self,aps: bool):
        self.__avg_press_spec = aps
    
    @boolean_property
    def radial(self) -> str:
        return self.__radial
    
    @radial.setter
    @udf_setter
    def radial(self,r: bool):
        self.__radial = r
    
    def format_turbulent_quantities(self) -> str:
        """
        have to modify to allow the additional of "backflow-" to the front
        of the turbulent quantities
        """
        if self.turbulence_model.turbulent_kinetic_energy is not None:
            return self.turbulence_model.specification_conditions(prefix = 'backflow-')
        else:
            return self.turbulence_model.specification_conditions()
    
    def format_p_profile_multiplier(self) -> str:
        
        return 'p-profile-multiplier' + self.LINE_BREAK +\
                str(self.p_profile_multiplier) + self.LINE_BREAK
    
    def format_conditions(self) -> str:

        txt = self.format_direction_spec()
        txt += self.format_frame_of_reference()
        txt += self.turbulence_model.format_conditions()
        txt += self.radial + self.avg_press_spec
        txt += self.format_p_profile_multiplier()

        return txt

class VelocityInlet(FluentFluidBoundaryCondition):
    """
    Representation of the Velocity Inlet Boundary condition in fluent. Does not support
    specification by components, only magnitude and direction

    Parameters
    ----------
    name : str
            the name of the mass flow inlet boundary condition
    models : list
            a list of the models used, does not require specification of temperature
    turbulence_model: str
            the turbulence model used, see allowable turbulence models
    vmag : float | *
            the magnitude of the velocity
    p_sup : float | *
            the initial pressure of the inlet
    velocity_spec : str | *
            for now only supports "magnitude, normal to boundary"

    Examples
    --------
    
    .. code-block:: python

        vi = VelocityInlet('test_vi',['viscous'],'ke-standard')
        print(vi())

    """


    DEFAULTS = {'vmag': 0,
                'p_sup': 0,
                'velocity_spec':'magnitude, normal to boundary'}

    VELOCITY_SPEC = ['magnitude and direction',
                     'magnitude, normal to boundary']


    def __init__(self,name: str,
                      models: list,
                      turbulence_model: str,
                      **kwargs):

        
        super().__init__(name,'velocity-inlet',models,turbulence_model,
                         defaults = self.DEFAULTS,**kwargs)
    
    @udf_property('vmag')
    def vmag(self):
        return self.__vmag
    
    @vmag.setter
    @udf_setter
    def vmag(self,vm: float):
        self.__vmag = vm
    
    @udf_property('p-sup')
    def p_sup(self):
        return self.__p_sup

    @p_sup.setter
    @udf_setter
    def p_sup(self,p: float):
        self.__p_sup = p
    
    def format_velocity_spec(self):

        if self.velocity_spec not in self.VELOCITY_SPEC:
            text_list =[txt + '\n' for txt in self.VELOCITY_SPEC]
            raise ValueError('velocity must be specified by one \
                              of: {} \n not {}'.format(text_list,self.velocity_spec))
        
        if self.direction_vector is not None:
            self.velocity_spec = 'magnitude and direction'

        text = 'velocity-spec' + self.LINE_BREAK
        if self.velocity_spec == 'magnitude, normal to boundary':
            return text + 'no' +self.LINE_BREAK + 'no' +self.LINE_BREAK +\
                   'yes' +self.LINE_BREAK
        else:
            text += 'yes' + self.LINE_BREAK
            text += self.format_direction_spec(direction_str= ['direction-0',
                                                               'direction-1',
                                                               'direction-2'],
                                                direction_spec = None)
            return text

    def format_conditions(self) -> str:

        txt = self.format_velocity_spec()
        txt += self.format_frame_of_reference()
        txt += self.turbulence_model.format_conditions()

        return txt

class SurfaceIntegrals(TUIBase):
    """ 
    base class for all surface integrals that can be generated using 
    fluent. Hooks into an engine and executes upon inserting commands

    Parameters
    ---------
    file : str
            string of the file to apply the surface integrals to
    id : list
            a list of integers of the boundary condition identification
    variable : list
            a list of strings of the field variable to compute the surface integral for
    surface_type : list
            the type of surface integral - i.e. area-weighted-avg
    engine: object
            default FluentEngine - the engine to open fluent with

    Examples
    --------
    
    .. code-block:: python

        si = SurfaceIntegrals('sample.cas',11,'temperature','area-weighted-avg')
        sif = si()

    .. code-block:: python

        si = SurfaceIntegrals('sample.cas',[[10,11],[12]],
                              ['temperature','temperature'],
                              ['area-weighted-avg','vertex-max'],
                              engine = None)
        sif = si()
        print(sif)

        > /report/surface-integrals/vertex-max
        > 12
        > , 
        > temperature
        > yes
        > sample-vertex-max-12-temperature
        > /report/surface-integrals/area-weighted-avg
        > 10
        > 11
        > , 
        > temperature
        > yes
        > sample-area-weighted-avg-10-11-temperature
    """

    _prefix = '/report/surface-integrals/{}'
    SURFACE_INTEGRAL_FILE_DELIM = '-'
    SURFACE_INTEGRAL_EXT = '.srp'
    
    def __init__(self,file:str,
                      id: str,
                      variable: str,
                      surface_type: str,
                      engine = FluentEngine,
                      id_pad = 1,
                      **engine_kwargs
                  ):
        
        #attempt to instantiate the engine - if the engine isn't callable
        #then assume that this is being used at the end of computation
        try:
            self.engine = engine(file,**engine_kwargs)
        except TypeError:
            self.engine = None
        
        self.file = file
        self.id,self.variable,self.surface_type  = \
             self._validate_constructor_args(id,variable,surface_type)
        
        file_names = [self._generate_file_name(self.file,st,id,var) for st,id,var 
                      in zip(self.surface_type,self.id,self.variable)]

        self.delete = {fname: True for fname in file_names}
        self.id_pad = id_pad

    @staticmethod
    def _validate_constructor_args(id: list,
                                   variable: list,
                                   surface_type: list) -> tuple:

        return _surface_construction_arg_validator(id,variable,surface_type)
    
    def prefix(self,surface_type: str):
        return self._prefix.format(surface_type)
    
    def file_name(self,id: str,
                       surface_type: str,
                       variable: str):
        """
        get the filename to write the surface integral to
        """
        fname = self._generate_file_name(self.file,
                                         surface_type,
                                         id,
                                         variable)
        
        if self.delete[fname]:
            self.delete[fname] = False
            if os.path.exists(fname):
                os.remove(fname)
            
        return fname
    
    def _format_text(self):
        """
        format the text for the call to the surface integral here
        """

        txt = ''
        
        shortest_id = min([len(id) for id in self.id])
        for ids,variable,surface_type in zip(self.id,self.variable,self.surface_type):
            txt += self.prefix(surface_type) + self.LINE_BREAK
            for id in ids:
                txt += id + self.LINE_BREAK
            
            
            if len(ids) < shortest_id + self.id_pad:
                diff = len(ids) - shortest_id
                for _ in range(self.id_pad - diff):
                    txt += ' , ' + self.LINE_BREAK 
            else:
                txt += ' , ' + self.LINE_BREAK
            
            txt += variable + self.LINE_BREAK
            txt += 'yes' + self.LINE_BREAK
            _,_file = os.path.split(self.file_name(ids,surface_type,variable))
            txt += _file + self.LINE_BREAK
        
        return txt

    def __call__(self,
                 return_engine = False):

        #enables the post module to simply be passed as txt
        #if the engine is not callable
        if self.engine is not None:

            self.engine.insert_text(self._format_text())
            engine_ouput = self.engine()
            sif = []
            for ids,variable,surface_type in zip(self.id,self.variable,self.surface_type):
                sif.append(SurfaceIntegralFile(self.file_name(ids,surface_type,variable)))

            if return_engine:
                return sif,engine_ouput
            else:
                return sif
        else:
            return self._format_text()

    def _generate_file_name(self,
                            file: str,
                            surface_type: str,
                            ids: list,
                            variable: str) -> str:
        
        _ids = ''.join([id + self.SURFACE_INTEGRAL_FILE_DELIM for id in ids])[0:-1]

        path,_file = os.path.split(file)
        _file = os.path.splitext(_file)[0]

        write_file = ''.join([item + self.SURFACE_INTEGRAL_FILE_DELIM for item in [_file,surface_type,_ids,variable]])[0:-1]
         
        return os.path.join(path,write_file)
    
class FluentJournal(SerializableClass,TUIBase):
    
    """
    class for producing a fluent batch job file using provided information. This essentially
    knits all essential information required to run a fluent case into a single journal file.
    The intent is to make this as easy to use as possible, so the only required argument
    is the case_file as a string argument, and everything else should be handled
    automatically, with optional specification provided as keyword arguments

    Parameters
    ----------
    case_file : str
            the string of the case file
    output_name : str
            the name of the output .cas and .dat files - default "result"
    transcript_file : str
            the name of the transcript file - default "solution.trn"
    reader : object
            the reader in fluent, defaults to "CaseReader". must have a __str__() method
    data_writer : object
            the data writer in fluent, defaults to "DataWriter". must have a __str__() method
    case_writer : object
            the case writer in fluent, defaults to "CaseWriter". must have a __str__() method
    solver : object
            the solver object in fluent, defaults to "Solver". must have __str__() method
    post : list
            a list of post objects, each of which must be callable and return a string
    model_modifications : list
            a list of model modifications, each of which must have a __str__() method
    boundary_conditions : list
            a list of boundary conditions, each of which must be callable and return a string
    """
    
    def __new__(cls,*args,**kwargs):

        return super(FluentJournal,cls).__new__(cls)

    def __init__(self,case_file: str,
                      output_name = 'result',
                      transcript_file = 'solution.trn',
                      reader = CaseReader,
                      data_writer = DataWriter,
                      case_writer = CaseWriter,
                      solver = Solver(),
                      post = [],
                      convergence_condition = None,
                      model_modifications = [],
                      boundary_conditions = [],
                      pre_solution = [],
                      **kwargs):

        self.__case = FluentCase(case_file)
        
        try:
            self.__reader = reader(case_file)
        except TypeError:
            self.__reader = reader
        
        #potentially immense storage savings here if we do not write every single case
        if case_writer is None or isinstance(case_writer,type(None)):
            self.write_case = False
            self.__case_writer = None
        else:
            self.write_case = True
            self.__case_writer = case_writer(output_name + '.cas')
        
        if data_writer is None or isinstance(case_writer,type(None)):
            self.write_data = False
            self.__data_writer = None
        else:
            self.write_data = True
            self.__data_writer = data_writer(output_name + '.dat')
        
        self.__solver = solver
        self.__transcript_file = transcript_file
        self.__file_name = case_file
        self.__boundary_conditions = boundary_conditions
        self.__convergence_condition = convergence_condition
        self.__post = post
        self.model_modifications = model_modifications
        self.pre_solution = pre_solution

    @property
    def case(self):
        return self.__case

    @property
    def file_name(self):
        return self.__file_name
    
    @file_name.setter
    def file_name(self,fn):
        self.__file_name = fn
    
    @property
    def reader(self):
        return self.__reader
    
    @property
    def case_writer(self):
        return self.__case_writer
    
    @property
    def convergence_condition(self):
        return self.__convergence_condition

    @property
    def data_writer(self):
        return self.__data_writer
    
    @property 
    def solver(self):
        return self.__solver
    
    @property
    def transcript_file(self):
        return self.__transcript_file
    
    @property
    def boundary_conditions(self):
        return self.__boundary_conditions
    
    @property
    def post(self):
        return self.__post
    
    @post.setter
    def post(self,p):
        self.__post = p

    @boundary_conditions.setter
    def boundary_conditions(self,bc):
        self.__boundary_conditions = bc
    

    def _model_modification_spec(self):
        """
        must have a str method
        """
        txt = self.LINE_BREAK + ';Model Modifications' + self.LINE_BREAK + self.LINE_BREAK
        for model_mod in self.model_modifications:
            txt += str(model_mod)
        
        return txt

    def _pre_solution_spec(self):
        """ 
        must have a str method
        """
        text = self.LINE_BREAK + ';Pre Solution' + self.LINE_BREAK + self.LINE_BREAK
        for ps in self.pre_solution:
            text += str(ps)
        
        return text
    
    def _boundary_conditions_spec(self):
        """
        boundary conditions must be callable 
        """
        txt = self.LINE_BREAK + ';Boundary Conditions' + self.LINE_BREAK + self.LINE_BREAK
        for bc in self.boundary_conditions:
            txt += bc()
        
        return txt

    def _format_convergence_condition(self):
        """ 
        convergence conditions must have a __str__ method defined
        """
        if self.convergence_condition is None:
            return ''
        else:
            txt = self.LINE_BREAK + ';Convergence Conditions' + self.LINE_BREAK + self.LINE_BREAK
            return txt + str(self.converence_condition)
    
    def _post_spec(self):
        """
        everything from post must have a call method which returns a string.
        post methods may have an engine property, which should be set to None
        so that another instance of fluent is not started.
        """
        txt = self.LINE_BREAK + ';Post Processing' + self.LINE_BREAK + self.LINE_BREAK
        for p in self.post:
            try:
                p.engine = None
            except AttributeError:
                pass
            
            txt += p()
        
        return txt

    def _format_fluent_file(self) -> str:
        """
        format the fluent input file
        """
        
        txt = 'file/start-transcript ' + self.transcript_file + self.LINE_BREAK     
        
        txt +=  str(self.reader) + self.LINE_BREAK
        txt += self._format_convergence_condition()
        txt += self._model_modification_spec()
        txt += self._boundary_conditions_spec()
        txt += self._pre_solution_spec()
        if self.solver is not None:
            txt += str(self.solver)
        txt += self._post_spec()
        if self.write_case:
            txt += str(self.case_writer) + self.LINE_BREAK
        
        if self.write_data:
            txt += str(self.data_writer) + self.LINE_BREAK
        
        txt += 'exit' + self.LINE_BREAK

        return txt

    def __call__(self):
        return self._format_fluent_file()

    def write(self,f) -> None:

        try:
            with open(f,'w',newline = self.LINE_BREAK) as file:
                file.write(self._format_fluent_file())

        except TypeError as te:
            try:
                f.write(self._format_fluent_file())
            except AttributeError as ae:
                raise ValueError('Failed to write file for following reasons: \nTypeError:{} \nAttributeError: {}\nInput that caused error: {}'.format(str(te),str(ae),f))
        
    def _from_file_parser(dmdict):
        """
        allows for the parsing of the class from a file
        """
        dmdict.pop('class')
        dmdict.pop('case')
        dmdict.pop('write_case')
        case_file = dmdict.pop('file_name')
        dmdict['reader'] = dmdict.pop('reader').__class__
        dmdict['case_writer'] = dmdict.pop('case_writer').__class__
        dmdict['data_writer'] = dmdict.pop('data_writer').__class__

        return [case_file],dmdict
    