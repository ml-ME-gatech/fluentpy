#native imports
from abc import ABC,abstractmethod
import os
from typing import OrderedDict, Union
import os
import subprocess
import numpy as np 
import sys

#package imports
from .disk import SerializableClass
from .util import _surface_construction_arg_validator
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
           'SurfaceIntegrals',
           'FluentRun'
           ]

"""
Author: Michael Lanahan
Date Created: 08.05.2021
Last Edit: 12.29.2021

The purpose of this file is provide python class interfaces to TUI commands in 
the command line or batch mode fluent software.
"""

class TUIBase:

    LINE_BREAK = '\n'
    EXIT_CHAR = 'q' + LINE_BREAK
    EXIT_STATEMENT = 'exit'
    
    def __init__(*args,**kwargs):
        pass

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
                      mesh_file: str) -> None:

        _case_reader = CaseReader(case_file)
        self._prefix = str(_case_reader) + self.LINE_BREAK + self._prefix
        super().__init__(mesh_file)
    
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
    
    Examples
    --------
    example demonstrates how to extract a surface integral from a case file via fluent.
    This example would invoke fluent provided that the fluent executable is on the system path.
    
    .. code-block:: python
        
        engine = FluentEngine('sample.cas',num_processors = 8)
        si = SurfaceIntegrals('sample.cas',11,'temperature','area-weighted-avg',engine = engine)
        sif = si()
    """

    POSIX_FLUENT_INIT_STATEMENT = 'fluent 3ddp -t{} < {} > {}'
    WINDOWS_FLUENT_INIT_STATEMENT = 'fluent {} -t{} -g -i {} -o {}'
    FLUENT_INPUT_NAME = 'input.fluent'
    FLUENT_OUTPUT_NAME = 'output.fluent'

    def __init__(self,file: str,
                      specification = '3ddp',
                      num_processors = 1,
                      reader = CaseDataReader):
        
        self.path,file_name = os.path.split(file)
        self.spec = specification
        self.__num_processors = num_processors
        self.__input = reader(file_name)
        self._additional_txt = ''
        self.input_file = os.path.join(self.path,self.FLUENT_INPUT_NAME)
        self.output_file = os.path.join(self.path,self.FLUENT_OUTPUT_NAME)
    

    def insert_text(self,other):
        self._additional_txt += other
    
    @property
    def num_processors(self):
        return str(self.__num_processors)

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
            return self.WINDOWS_FLUENT_INIT_STATEMENT.format(self.spec,
                                                        self.num_processors,
                                                        self.FLUENT_INPUT_NAME,
                                                        self.FLUENT_OUTPUT_NAME) + self.EXIT_CHAR
        elif system == 'posix':
            return self.POSIX_FLUENT_INIT_STATEMENT.format(self.spec,
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

        self.clean()
        txt = self._format_call(save)
        cwd = os.getcwd()
        os.chdir(self.path)
        process = subprocess.call(txt)
        os.chdir(cwd)
        self.clean()
        return process

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
            self.pwd = current_folder
        
    @property
    def _suffix(self):
        return self.LINE_BREAK + 'sync-chdir {}'.format(self.pwd)
        
    @property
    def pwd(self):
        return self.__pwd

    @pwd.setter
    def pwd(self,pwd):
        self.__pwd = pwd
    
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

class TurbulentBoundarySpecification(ABC,TUIBase):

    def __init__(self):
        pass

    @abstractmethod
    def turbulence_spec(self):
        pass

    def skip_choices(self,num):

        return ''.join(['no' + self.LINE_BREAK for _ in range(num)])

class TwoEquationTurbulentBoundarySpecification(TurbulentBoundarySpecification):

    def __init__(self):
        self.__tke = 1
        self.__length_scale = None
        self.__intensity = None
        self.__viscosity_ratio = None
        self.__hydraulic_diameter = None

    @property
    def intensity(self):
        return self.__intensity
    
    @property
    def tke(self):
        return self.__tke

    @property
    def length_scale(self):
        return self.__length_scale

    @property
    def viscosity_ratio(self):
        return self.__viscosity_ratio

    @property
    def hydraulic_diameter(self):
        return self.__hydraulic_diameter
    
    @intensity.setter
    def intensity(self,intensity):
        self.__intensity = intensity
    
    @tke.setter
    def tke(self,tke):
        self.__tke = tke

    @length_scale.setter
    def length_scale(self,ls):
        self.__length_scale = ls

    @viscosity_ratio.setter
    def viscosity_ratio(self,vr):
        self.__viscosity_ratio = vr
    
    @hydraulic_diameter.setter
    def hydraulic_diameter(self,hd):
        self.__hydraulic_diameter = hd

    def _intensity_and_hydraulic_diameter(self) -> str:

        txt = self.skip_choices(3)
        txt += 'yes' + self.LINE_BREAK
        #no to profile
        txt += str(self.intensity) + self.LINE_BREAK
        #no to profile
        txt += str(self.hydraulic_diameter) + self.LINE_BREAK

        return txt
    
    def turbulence_spec(self,specification):
        if specification == 'intensity and hydraulic diameter':
            return self._intensity_and_hydraulic_diameter()
        elif specification == 'k and omega':
            return self._k_and_omega_specification()
        elif specification == 'k and epsilon':
            return self._k_and_epsilon_specification()
        else:
            raise NotImplementedError('Havent implemented boundary specification mechanisms\
                 beyond intensity and hydraulic diameter, k and omega and k and epsilon')
    
class StandardKOmegaSpecification(TwoEquationTurbulentBoundarySpecification):

    def __init__(self):

        super().__init__()
        self.__omega = 1
    
    @property
    def omega(self):
        return self.__omega
    
    @omega.setter
    def omega(self,o):
        self.__omega = o
    
    def _k_and_omega_specification(self) -> str:
        
        #no to profile
        txt = 'yes' + self.LINE_BREAK + 'no' + self.LINE_BREAK
        txt += str(self.tke) + self.LINE_BREAK
        #no to profile
        txt += 'no' + self.LINE_BREAK
        txt += str(self.omega) + self.LINE_BREAK
        return txt

class StandardKEpsilonSpecification(TwoEquationTurbulentBoundarySpecification):

    def __init__(self):

        super().__init__()
        self.__tdr = 1

    @property
    def tdr(self):
        return self.__tdr

    @tdr.setter
    def tdr(self,tdr):
        self.__tdr = tdr

    def _k_and_epsilon_specification(self) -> str:
        
        #no to profile
        txt = 'yes' + self.LINE_BREAK + 'no' + self.LINE_BREAK
        txt += str(self.tke) + self.LINE_BREAK
        #no to profile
        txt += 'no' + self.LINE_BREAK
        txt += str(self.tdr) + self.LINE_BREAK
        return txt

def _assign_turbulence_model(model:str) -> TurbulentBoundarySpecification:

    class_assignment = {'ke-standard':StandardKEpsilonSpecification,
                        'ke-realizable':StandardKEpsilonSpecification,
                        'ke-rng': StandardKEpsilonSpecification,
                        'kw-standard':StandardKOmegaSpecification}
    
    specification_assigmnment = {'ke-standard':'k and epsilon',
                                 'ke-realizable': 'k and epsilon',
                                 'ke-rng': 'k and epsilon',
                                 'kw-standard': 'k and omega'}

    try:
        return class_assignment[model](), specification_assigmnment[model]
    except KeyError:
        raise ValueError('cannot identify the requested model: {}'.format(model))

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
    6. 'kw-standard'
    7. 'k-kl-w'
    
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
                                'kw-standard',
                                'k-kl-w']


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

class FluentCellZone(ABC,TUIBase):

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

        > yes
        > yes
        > myudf
        > "mydata"
    
    """

    _compile_prefix = 'define/user-defined'
    def __init__(self,file_name: str,
                      udf_name: str,
                      data_name: str,
                      condition_name: str,
                      compile = False) -> None:


        if not os.path.exists(file_name):
            raise FileNotFoundError('file: {} does could not be found'.format(file_name))
        
        self.file_name = file_name
        self.udf_name = udf_name
        self.__data_name = data_name
        self.condition_name = condition_name
        self.compile = compile

    @property
    def data_name(self):
        return r'"' + self.__data_name + r'"'

    def _format_enable_udf(self):
        """
        string sequence to enable using udf
        """
        text = 'yes' + self.LINE_BREAK
        text += 'yes' + self.LINE_BREAK
        text += self.udf_name + self.LINE_BREAK
        text += self.data_name + self.LINE_BREAK

        return text

    def _format_compile_udf(self):
        """
        format string sequence to compile udf if required
        """
        return ''

    def __str__(self):
        """
        string sequence to enablle
        """

        return self._format_enable_udf()

def enable_udf(condition_name: str) -> callable:
    """
    decorator meant to enable all conditions 
    that can have udf profile to have one 
    
    Parameters
    ----------
    condition_name : str
            the condition_name that could be enabled
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

        def enabled_condition(self,*args,**kwargs) -> str:
            
            try:
                return str(self.udf[condition_name])
            except KeyError:
                additional_text = 'no' + self.LINE_BREAK
                return additional_text + condition(self,*args,**kwargs)
            
        return enabled_condition
    
    return udf_enabled_condition

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
    _prefix = '/define/boundary-conditions/'
    _line_start = '/'
    ALLOWABLE_SOLVERS = ['pressure-based','density-based']
    ALLOWABLE_BOUNDARY_TYPES = ['mass-flow-inlet','pressure-outlet','wall']
    ALLOWABLE_VISCOUS_MODELS = ['ke-standard','kw-standard','ke-realizable','ke-rng']
    ALLOWABLE_MODELS = ['energy','viscous'] 
    ALLOWABLE_MODELS += ['viscous/' + vm for vm in ALLOWABLE_VISCOUS_MODELS]
    
    def __init__(self,name: str,
                      boundary_type: str,
                      models: list,
                      solver: str,
                      reference_frame = 'absolute',
                      **kwargs):
        
        if solver not in self.ALLOWABLE_SOLVERS:
            raise ValueError('solver: {} is not allowed'.format(solver))
        
        for model in models:
            if model not in self.ALLOWABLE_VISCOUS_MODELS and model not in self.ALLOWABLE_MODELS:
                raise ValueError('model: {} is not allowed'.format(model))
        
        if boundary_type not in self.ALLOWABLE_BOUNDARY_TYPES:
            raise ValueError('Cannot parse boundary of type: {}'.format(boundary_type))
        
        self._assign_default_attributes(self.DEFAULTS,**kwargs)

        self.__btype = boundary_type
        self.__name = name
        self.__models = models
        self.__solver = solver
        self.__udf = {}
        self.__reference_frame = reference_frame

    @property
    def name(self):
        return self.__name

    @property
    def models(self):
        return self.__models
    
    @property
    def solver(self):
        return self.__solver

    @property
    def btype(self):
        return self.__btype

    @property
    def udf(self):
        return self.__udf
    
    @property
    def reference_frame(self):
        if self.__reference_frame == 'absolute':
            return 'yes'
        else:
            return 'no'
    
    @udf.setter
    def udf(self,udf):
        self.__udf = udf
    
    def enter_statement(self):
        return self._prefix + self.btype + self.LINE_BREAK + self.name + self.LINE_BREAK        

    def add_udf(self,new_udf: UDF) -> None:
        """
        add a new udf to the udf dictionary
        """
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
        
    def _configure_udf_from_mapping(self,mapping: dict) -> str:
        """
        base function for configuring the udfs for a boundary condition
        """
        _compile_text = ''
        for formatter,property_name in mapping.items():
            #assign values of -1 to all properties with udf
            if formatter in self.udf:
                self.__setattr__(property_name,-1)
                if self.udf[formatter].compile:
                    _compile_text += self.udf[formatter].format_compile_udf()

        return _compile_text

    @abstractmethod
    def _format_boundary_condition(self) -> str:

        pass
    
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
                      solver: str,
                      **kwargs):

        super().__init__(name,boundary_type,models,solver,**kwargs)

    def __call__(self):

        return self._format_boundary_condition()
    
    def _format_boundary_condition(self):

        return super()._format_boundary_condition()
    
class WallBoundaryCondition(FluentSolidBoundaryCondition):

    """
    Wall boundary condition representation. Properties with a star may be set after instantation. 
    UDFS may be applied to a particular property of the wall following the example below.

    Parameters
    ----------
    name : str
            the name of the wall boundary condition as a string
    models : list
            the models used 
    solver: str
            the solver used as a string
    shell_conduction : bool
            use shell conduction or not - default False
    wall_thickness : float | *
            thickness of the wall, default 0
    generation : float | *
            generation in the wall, default 0
    heat_flux : float | *
            heat flux at the wall, default None
    convection_coefficient : float | * 
            convection coefficient at the wall, default None
    free_stream_temperature : float | * 
            free stream temperature, default None
    caf : float | *
            convective augmentation factor, default 1

    Examples
    --------
    .. code-block:: python

        wall = WallBoundaryCondition('test',['energy','viscous'],'pressure-based')
        wall.free_stream_temperature = 400.0
        wall.convection_coefficient = 10e3
        print(wall())

        udf = UDF('test.c','udf','HTC::UDF','convection_coefficient')
        wall.add_udf(udf)
        print(wall())
    """
    
    DEFAULTS = {'wall_thickness':0,
                'generation': 0,
                'heat_flux':None,
                'convection_coefficient':None,
                'free_stream_temperature': None,
                'caf': 1}

    def __init__(self,name: str,
                      models: list,
                      solver: str,
                      shell_conduction = False,
                      **kwargs):

        if 'energy' not in models:
            raise NotImplementedError('boundary condition not configured to work without energy equation')
        
        super().__init__(name,'wall',models,solver,**kwargs)

        if shell_conduction:
            self.shell_conduction = 'yes'
        else:
            self.shell_conduction = 'no'

    @property
    def wall_thickness(self):
        return self.__wall_thickness
    
    @property
    def generation(self):
        return self.__generation

    @property
    def convection_coefficient(self):
        return self.__convection_coefficient
    
    @property
    def heat_flux(self):
        return self.__heat_flux
    
    @property
    def free_stream_temperature(self):
        return self.__free_stream_temperature
    
    @property
    def caf(self):
        return self.__caf

    @wall_thickness.setter
    def wall_thickness(self,wt):
        self.__wall_thickness = wt
    
    @generation.setter
    def generation(self,g):
        self.__generation = g
    
    @heat_flux.setter
    def heat_flux(self,hf):
        self.__heat_flux = hf
    
    @convection_coefficient.setter
    def convection_coefficient(self,cc):
        self.__convection_coefficient = cc
    
    @free_stream_temperature.setter
    def free_stream_temperature(self,fst):
        self.__free_stream_temperature = fst
    
    @caf.setter
    def caf(self,caf):
        self.__caf = caf
    
    def __str__(self):

        txt = 'wall thickness: ' + str(self.wall_thickness) + self.LINE_BREAK
        txt += 'heat generation: ' + str(self.generation) + self.LINE_BREAK
        txt += 'heat flux: ' + str(self.heat_flux) + self.LINE_BREAK
        
        return txt
    
    @enable_udf('heat_generation')
    def format_heat_generation(self):
            
        return str(self.generation) + self.LINE_BREAK
    
    @enable_udf('heat_flux')
    def format_heat_flux(self):

        return str(self.heat_flux) + self.LINE_BREAK

    @enable_udf('convection_coefficient')
    def format_convection_coefficient(self):

        return str(self.convection_coefficient) + self.LINE_BREAK

    @enable_udf('free_stream_temperature')
    def format_free_stream_temperature(self):

        return str(self.free_stream_temperature) + self.LINE_BREAK

    @enable_udf('convective_augmentation')
    def format_convective_augmentation(self):

        return str(self.caf) + self.LINE_BREAK
        
    def format_shell_conduction(self):

        txt = self.shell_conduction + self.LINE_BREAK
        return txt
    
    def _configure_udf(self):
        """
        configure mapping of udfs
        """
        mapping = {'heat_generation': 'generation',
                   'heat_flux': 'heat_flux',
                   'convection_coefficient': 'convection_coefficient',
                   'free_stream_temperature': 'free_stream_temperature',
                   'convective_augmentation': 'caf'}
        
        return self._configure_udf_from_mapping(mapping)

    def _format_boundary_condition(self):

        txt = self._configure_udf()

        txt += self.enter_statement()
        txt += str(self.wall_thickness) + self.LINE_BREAK
        txt += self.format_heat_generation()
        #no to change material
        txt += 'no' + self.LINE_BREAK
        #no to change Thermal BC Type
        txt += 'no' + self.LINE_BREAK
        if self.heat_flux is None:
            if self.convection_coefficient is None or self.free_stream_temperature is None:
                raise ValueError('cannot have None value for convection coefficient and free stream temperature if heat flux is None')
            
            txt += self.format_convection_coefficient()
            txt += self.format_free_stream_temperature()

        elif self.convection_coefficient is None:
            txt += self.format_heat_flux()
        
        txt += self.format_shell_conduction()
        txt += self.format_convective_augmentation()

        return txt
        
class FluentFluidBoundaryCondition(FluentBoundaryCondition):
    """
    Note on variable names: 
    tke - total kinetic energy
    tdr - total dissipation rate
    """ 
    FLUID_DEFAULTS = {'temperature': 300,
                     'direction_vector': None}

    def __init__(self,name:str,
                      boundary_type: str,
                      models: list,
                      solver: str,
                      turbulence_model: str,
                      **kwargs):

        for key,value in self.FLUID_DEFAULTS.items():
            self.DEFAULTS[key] = value
        
        super().__init__(name,boundary_type,models,solver,**kwargs)

        self.__turbulence_model,self.__turbulence_specification = \
            _assign_turbulence_model(turbulence_model)
    
    def add_statement(self,text: str,
                           newtext: str) -> str:
        
        return text + self._line_start + newtext + self._line_start
    
    @property
    def turbulence_model(self):
        return self.__turbulence_model
    
    @property
    def direction_vector(self):
        return self.__direction_vector

    @property
    def temperature(self):
        return self.__temperature
      
    @direction_vector.setter
    def direction_vector(self,dv):
        self.__direction_vector = dv

    @temperature.setter
    def temperature(self,t):
        self.__temperature = t
    
    @property
    def turbulence_specification(self):
        return self.__turbulence_specification
    
    @turbulence_specification.setter
    def turbulence_specification(self,ts):
        self.__turbulence_specification = ts
    
    def direction_spec(self) -> str:

        """
        deals with setting the direction vector
        options consist of 
        (1) normal to boundary - selected if direction_vector is None
        (2) sets the direction vector asssuming a list or numpy array
            strict checking of the shape of the direction vector
         """
    
        txt = ''
        if self.direction_vector is None:
            txt = 'no' + self.LINE_BREAK
            #normal to boundary
            txt += 'yes' + self.LINE_BREAK
        else:
            msg = 'direction vector (if specified) must be a list or 1D numpy array'
            if isinstance(self.direction_vector,list):
                self.direction_vector = np.array(self.direction_vector).squeeze()
            elif isinstance(self.direction_vector,np.ndarray):
                self.direction_vector = self.direction_vector.squeeze()
            else:
                raise TypeError(msg)
            
            if self.direction_vector.ndim != 1:
                raise ValueError(msg)
            
            if self.direction_vector.shape[0] > 3:
                raise ValueError('direction vector cannot contain more than 3 components')

            txt = 'yes' + self.LINE_BREAK + 'yes' + self.LINE_BREAK
            for i in range(self.direction_vector.shape[0]):
                txt += 'no' + self.LINE_BREAK + str(self.direction_vector[i]) + self.LINE_BREAK
            
        return txt
    
    @enable_udf('temperature')
    def format_temperature(self) -> str:

        """
        deals with the tempearture specifications
        """
        return str(self.temperature) + self.LINE_BREAK


    def __call__(self):
        return self._format_boundary_condition()

class MassFlowInlet(FluentFluidBoundaryCondition):

    """
    Mass flow rate boundary condition class. Allows for specification of either the mass flux
    or the mass flow rate. Specification of the turbulence model is required. Starred 
    arguments are keyword arguments that act as inputs for the fluent journal. mass_flow_Rate 
    and mass_flux default to None, and only one of these variables is permitted to not be None
    to avoid specification of both.

    Parameters
    ----------
    name : str
            the name of the mass flow inlet boundary condition
    models : list
            a list of the models used, does not require specification of temperature
    solver : str
            the solver, one of 'pressure-based' or 'density-based'
    turbulence_model: str
            the turbulence model used, see allowable turbulence models
    temperature : float | *
            the temperature of the inlet flow, only applicable if model "energy" is used,\
            defaults to 300 K
    mass_flow_rate : float | *
            the mass flow rate defaults to None
    mass_flux : float | *
            the mass flux defaults to None
    init_pressure : float | *
            the initial pressure defaults to 0
    direction_vector : float | *
            optional specfication of the direction vector, must be specified as a
            1D array with three components x,y,z. Defaults to None, in which case
            the mass flow is normal to the boundary.
    turbulence_specification : float | *
            how to specify the turbulent quantities on the boundary. default is either
            "k and epsilon" or "k and omega" depending upon the viscous model. Can alternatively
            be specified using "intensity and hydraulic diameter"

    Examples
    --------
    .. code-block:: python
        
        mfi = MassFlowInlet('test_mfi',['viscous'],'pressure-based','ke-standard')
        mfi.mass_flux = 1.0
        print(mfi())

        > /define/boundary-conditions/mass-flow-inlet
        > test_mfi
        > yes
        > no
        > yes
        > no
        > mass flux: 1.0
        > no
        > pressure: 0
        > no
        > yes
        > yes
        > no
        > 1
        > no
        > 1
    """

    DEFAULTS = {'mass_flow_rate': None,
                'mass_flux': None,
                'init_pressure':0}
                
    def __init__(self,name: str,
                      models: list,
                      solver: str,
                      turbulence_model: str,
                      **kwargs):

        fkwargs = {kw: val for kw,val in kwargs.items() if kw not in self.DEFAULTS}
        super().__init__(name,'mass-flow-inlet',models,
                         solver,turbulence_model,**fkwargs)
        self._assign_default_attributes(self.DEFAULTS,**kwargs)

    @property
    def mass_flow_rate(self):
        return self.__mass_flow_rate
    
    @property
    def mass_flux(self):
        return self.__mass_flux

    @property
    def init_pressure(self):
        return self.__init_pressure
    
    @mass_flow_rate.setter
    def mass_flow_rate(self,mfr):
        self.__mass_flow_rate = mfr
    
    @mass_flux.setter
    def mass_flux(self,mf):
        self.__mass_flux = mf

    @init_pressure.setter
    def init_pressure(self,ip):
        self.__init_pressure = ip

    @enable_udf('mass_flow_rate')
    def format_mass_flow_rate(self):
        return 'mass flow: {}'.format(self.mass_flow_rate) + self.LINE_BREAK

    @enable_udf('mass_flux')
    def format_mass_flux(self):
        return 'mass flux: {}'.format(self.mass_flux) + self.LINE_BREAK
    
    @enable_udf('pressure')
    def format_pressure(self):
        return 'pressure: {}'.format(self.init_pressure) + self.LINE_BREAK
    
    def __str__(self):

        if self.mass_flow_rate is not None:
            txt = self.format_mass_flow_rate()
        elif self.mass_flux is not None:
            txt = self.format_mass_flux()
        else:
            raise ValueError('cannot have both mass flux and mass flow rate as None for MassFlowINlet Boundary condition')
        
        txt += self.format_temperature()
        txt += self.format_pressure()
        
        return txt
        
    def _mass_specification(self) -> str:

        """ 
        deal with the mass flow rate specifications. Formats either the mass flow rate
        or the mass flux depending upon user specification. Allows specification through
        UDF. 
        """ 

        if self.mass_flow_rate is None:
            if self.mass_flux is None:
                raise ValueError('cannot leave both mass flow rate and mass flux unspecified')
            
            txt = 'no' + self.LINE_BREAK + 'yes' + self.LINE_BREAK
            txt += self.format_mass_flux()
        
        else:
            if self.mass_flux is not None:
                raise ValueError('You cannot specify both the mass flux and the mass flow rate')
            
            txt = 'yes' + self.LINE_BREAK + 'no' + self.LINE_BREAK
            txt += self.format_mass_flow_rate()
        
        return txt

    def _configure_udf(self):
        """
        configure mapping of udfs
        """
        mapping = {'temperature': 'temperature',
                   'pressure': 'init_pressure',
                   'mass_flux': 'mass_flux',
                   'mass_flow_rate': 'mass_flow_rate'}
        
        return self._configure_udf_from_mapping(mapping)
    
    def _format_boundary_condition(self) -> str:

        txt = self._configure_udf()
        txt += self.enter_statement()
        txt += self.reference_frame + self.LINE_BREAK     
        txt += self._mass_specification()
        if 'energy' in self.models:
            txt += self.format_temperature()
        txt += self.format_pressure()
        txt += self.direction_spec()
        txt += self.turbulence_model.turbulence_spec(self.turbulence_specification)
        
        return txt

class PressureOutlet(FluentFluidBoundaryCondition):
    """
    A pressure outlet boundary condition class. Similar to other boundary conditions,
    requires specification of a name, models simulated, the solver used and the turbulence model.
    The pressure and temperature are the only values that impact input into the TUI and the
    pressure defaults to None. This will create an error if left unspecified, so this must be modified
    during instantation or directly on the instance.

    Parameters
    ---------
    name : str
            the name of the mass flow inlet boundary condition
    models : list
            a list of the models used, does not require specification of temperature
    solver : str
            the solver, one of 'pressure-based' or 'density-based'
    turbulence_model: str
            the turbulence model used, see allowable turbulence models
    temperature : float | *
            the temperature of the inlet flow, only applicable if model "energy" is used,\
            defaults to 300 K
    pressure : float | *
            the pressure at the outlet
    direction_vector : float | *
            optional specfication of the direction vector, must be specified as a
            1D array with three components x,y,z. Defaults to None, in which case
            the mass flow is normal to the boundary.
    turbulence_specification : float | *
            how to specify the turbulent quantities on the boundary. default is either
            "k and epsilon" or "k and omega" depending upon the viscous model. Can alternatively
            be specified using "intensity and hydraulic diameter"
    Examples
    ---------
    .. code-block:: python 

        po = PressureOutlet('test_pressure_outlet',['viscous','energy'],'pressure-based','kw-standard')
        po.pressure = 10e5
        print(po())
        > /define/boundary-conditions/pressure-outlet
        > test_pressure_outlet
        > yes
        > no
        > 1000000.0
        > no
        > 300
        > no
        > yes
        > yes
        > no
        > 1
        > no
        > 1
        > yes
        > no
        > no
        > no
    """

    DEFAULTS = {'pressure': None}

    def __init__(self,name:str,
                      models: list,
                      solver: str,
                      turbulence_model: str,
                      **kwargs):

        super().__init__(name,'pressure-outlet',models,solver,
                        turbulence_model,**kwargs)
        
    @property
    def pressure(self):
        return self.__pressure
    
    @pressure.setter
    def pressure(self,p):
        self.__pressure = p
    
    @enable_udf('pressure')
    def format_pressure(self):
        """
        specifications for the pressure
        """ 
        return str(self.pressure) + self.LINE_BREAK

    def _configure_udf(self):
        """
        configure mapping of udfs
        """
        mapping = {'temperature': 'temperature',
                   'pressure': 'pressure'}
        
        return self._configure_udf_from_mapping(mapping)
    
    def _format_boundary_condition(self) -> str:

        txt = self.enter_statement()
        txt += 'yes' + self.LINE_BREAK
        txt += self.format_pressure()
        if 'energy' in self.models:
            txt += self.format_temperature()
        txt += self.direction_spec()
        txt += self.turbulence_model.turbulence_spec(self.turbulence_specification)
        #no to a couple of end options that are pretty obscure:
        #Radial Equiliibrium Pressure Distribution
        #Average Pressure Specification
        #Specify Targeted Mass Flow Rate
        txt += 'yes' + self.LINE_BREAK + ''.join(['no' + self.LINE_BREAK for _ in range(3)])

        return txt
    
    def __str__(self):

        txt = 'pressure: {}'.format(self.pressure) + self.LINE_BREAK
        txt += 'temperature: {}'.format(self.temperature) + self.LINE_BREAK
        
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
    
class FluentRun(SerializableClass,TUIBase):
    
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
                      boundary_conditions = []):

        self.__case = FluentCase(case_file)
        
        try:
            self.__reader = reader(case_file)
        except TypeError:
            self.__reader = reader
        
        #potentially immense storage savings here if we do not write every single case
        if case_writer is None:
            self.write_case = False
            self.__case_writer = None
        else:
            self.write_case = True
            self.__case_writer = case_writer(output_name + '.cas')
        
        self.__data_writer = data_writer(output_name + '.dat')
        self.__solver = solver
        self.__transcript_file = transcript_file
        self.__file_name = case_file
        self.__boundary_conditions = boundary_conditions
        self.__convergence_condition = convergence_condition
        self.__post = post
        self.model_modifications = model_modifications

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
        post methods should have an engine property, which should be set to None
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
        txt += str(self.solver)
        txt += self._post_spec()
        if self.write_case:
            txt += str(self.case_writer) + self.LINE_BREAK
        
        txt += str(self.data_writer) + self.LINE_BREAK
        
        txt += 'exit' + self.LINE_BREAK

        return txt

    def __call__(self):
        return self._format_fluent_file()

    def write(self,f) -> None:

        try:
            with open(f,'w',newline = self.LINE_BREAK) as file:
                file.write(self._format_fluent_file())

        except TypeError:
            f.write(self._format_fluent_file())
    
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
    