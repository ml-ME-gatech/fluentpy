from .slurm import DefaultSlurm
from .pbs import DefaultPBS
from ..disk import SerializableClass
from copy import deepcopy

class FluentScript(SerializableClass):

    """
    A default PBS scrit for a fluent function call. Provides additional formatting 
    for calling ANSYS fluent after the pbs script. Note that the type of pbs 
    can be changed by supplying the keyword argument
    
    pbs = MyPBSClass
    
    in the initialization of the FluentPBS class

    The initial header from the pbs class, along with the additional text required for the fluent
    call are formatted in the function "format_call" and the text is returned by the following syntax

    fluentpbs = FluentPBS(*args,**kwargs)
    txt = fluentpbs()

    where the variable "txt" contains all of the information required for a pbs script with fluent
    """
    
    LINE_BREAK = '\n'
    
    
    def __init__(self,
                 input_file = 'fluent.input',
                 name = None,
                 WALLTIME = None,
                 MEMORY = None,
                 N_NODES = 1,
                 N_PROCESSORS = 1,
                 output_file = 'pace.out',
                 version = '2023R1',
                 email = None,
                 email_permissions = 'abe',
                 mpi_option = 'intel',
                 script_header = None,
                 _cached_header = None,
                 account = 'gts-my14',
                 specification = '3ddp',
                 memory_request = 'p',
                 config = []):
        
        if _cached_header is None:
            if WALLTIME is None:
                raise ValueError('wall time must be specified in order to run script')
                
            if MEMORY is None:
                raise ValueError('The amount of memory must be specified')
            
            if name is None:
                name = input_file
            
            self.script_header = script_header(name,WALLTIME,MEMORY,N_NODES,N_PROCESSORS,
                                                output_file,email = email,email_permissions = email_permissions,
                                                memory_request = memory_request,account = account)
            
        else:
            self.script_header = _cached_header
        
        self.mpi_opt = mpi_option
        self.version = version
        self.N_PROCESSORS = N_PROCESSORS
        self.N_NODES = N_NODES
        self.input_file = input_file
        self.specification = specification
        self._config = config


    def add_config(self,*args):
        """
        add configuration to the script
        """
        self._config.extend(args)
    
    @property
    def config(self):
        return '\n'.join(self._config) + '\n' if self._config else ''
    
    def format_machine_file(self):
        """
        sets the MPI option correctly for pace
        """
        if self.mpi_opt == 'pcmpi' or self.mpi_opt == 'intel' or self.mpi_opt == 'ibmmpi':
            return ' -mpi=' + self.mpi_opt
        elif self.mpi_opt == 'pib':
            return ' -' + self.mpi_opt
        elif self.mpi_opt is None:
            return ''
        
        else:
            raise ValueError('{} is not a valid mpi option'.format(self.mpi_opt))
    
    def format_cnf(self):
        """
        this is required for the process affinity to work on pace
        """
        return ' -cnf=$FLUENTNODES '

    def format_call(self):
        """
        format the whole script here
        """
        txt = self.script_header() + self.LINE_BREAK
        txt += self.config
        txt += self.format_change_dir(self.PDIR) +self.LINE_BREAK
        txt += self.LINE_BREAK + self.LINE_BREAK + self.script_header.added_text + self.LINE_BREAK + self.LINE_BREAK
        txt += self.format_load_ansys(self.version) +self.LINE_BREAK
        mpi = self.format_machine_file()
        cnf = self.format_cnf()
        txt += self.format_fluent_footer(self.N_PROCESSORS,self.N_NODES,
                                         self.input_file,mpi,cnf,
                                         self.specification) \
                + self.LINE_BREAK

        return  txt
    
    @staticmethod
    def format_change_dir(chdir):
        """
        this is important to change to the PBS dir which is an environment variable 
        native to the bash shell on PACE
        """
        return 'cd ' + chdir
    
    @staticmethod
    def format_load_ansys(version):

        """
        format the command to load the version of ansys
        """
        return 'module load ansys/' + version
    
    @staticmethod
    def format_fluent_footer(processors:str,
                             nodes: str,
                             input_file:str,
                             mpi: str,
                             cnf: str,
                             specification : str) -> str:
        """
        format the fluent call in the pbs script
        """
        
        return 'fluent ' + specification + ' -t$SLURM_NTASKS '  + '-scheduler_tight_coupling -pinfiniband'+ mpi + cnf + ' -g < ' + input_file + ' > outputfile'
    
    def __call__(self):
        """
        callable interface here
        """
        return self.format_call()
    
    def copy(self):
        """
        useful for making a bunch of copies in a batch script
        """
        return deepcopy(self)
    
    def write(self,f):
        """
        write the script to a file or IOStream (whatever its called in python)
        """
        try:
            with open(f,'w',newline = self.LINE_BREAK) as file:
                file.write(self.format_call())

        except TypeError:
            f.write(self.format_call())
    
    def _from_file_parser(dmdict):
        """
        parser from the file that allows instantation from file
        """
        dmdict['_cached_header'] = dmdict.pop('script_header')
        dmdict.pop('class')
        input_file = dmdict.pop('input_file')
        dmdict['mpi_option'] = dmdict.pop('mpi_opt')
        return [input_file],dmdict

class FluentPBS(FluentScript):

    def __init__(self,*args,**kwargs):

        super().__init__(*args,script_header= DefaultPBS,**kwargs)
        self.PDIR = '$PBS_O_WORKDIR'
        self.NODE_FILE = '$PBS_NODEFILE'

class FluentSlurm(FluentScript):

    def __init__(self,*args,**kwargs):

        super().__init__(*args,script_header= DefaultSlurm,**kwargs)
        self.PDIR = '$SLURM_SUBMIT_DIR'
        self.NODE_FILE = '$SLURM_JOB_NODELIST'


