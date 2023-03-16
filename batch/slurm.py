#native imports
from abc import ABC,abstractstaticmethod
from datetime import timedelta
from copy import deepcopy
import math
import os
from ..pace import PaceScript
from ..disk import SerializableClass

#package imports

"""
Author: Michael Lanahan
Date Created: 11.10.2022
Last Edit: 11.10.2022

scripts for working with fluent using the PACE computational cluster at GT
"""

class Slurm:

    """
    base class for the slurm header. Provides a base initialization method that formats the various
    initializer arguments into the required form for the slurm script. The formatting is done 
    in the property methods and is formatted into a script by the method "format_pbs_header()"
    this formatted text is then called like-so: 

    slurm = Slurm(*args,**kwargs)
    text = slurm()

    Example Slurm script
    https://docs.pace.gatech.edu/phoenix_cluster/slurm_guide_phnx/
    
    #!/bin/bash
    #SBATCH -JSlurmPythonExample                    # Job name
    #SBATCH --account=gts-gburdell3                 # charge account
    #SBATCH -N1 --ntasks-per-node=4                 # Number of nodes and cores per node required
    #SBATCH --mem-per-cpu=1G                        # Memory per core
    #SBATCH -t15                                    # Duration of the job (Ex: 15 mins)
    #SBATCH -qinferno                               # QOS Name
    #SBATCH -oReport-%j.out                         # Combined output and error messages file
    #SBATCH --mail-type=BEGIN,END,FAIL              # Mail preferences
    #SBATCH --mail-user=gburdell3@gatech.edu        # E-mail address for notifications

    cd $SLURM_SUBMIT_DIR                            -> change to working directroy - where script is submited from
    module load ansys/<version.number>              -> load ansys, with version number in <int>.<int> i.e. 19.12
    fluent -t8 -g <inputfile> outputfile            -> run fluent command with input file and output file
    """
    
    LINE_BREAK = '\n'
    line_leader = '#SBATCH '
    def __init__(self, name: str,
                       account: str,
                       queue: str,
                       output_file: str,
                       walltime: float,
                       memory:float,
                       nodes: int,
                       processors: int,
                       email = None,
                       email_permissions = None,
                       memory_request = 'p',
                       *args,
                       **kwargs):

        self.__name = name
        self.__account = account
        self.__queue = queue
        self.__output_file = output_file
        self.__walltime = walltime
        self.__memory = memory
        self.__nodes = nodes
        self.__processors = processors
        self.__email = email
        self.__email_permissions = email_permissions
        self.memory_request = memory_request.lower()
        if self.memory_request != 'p' and self.memory_request != 't':
            raise ValueError('memory must be requested on a per node "p" or total "t" basis')

    @property
    def name(self):
        return '-J' + self.__name 
    
    @property
    def account(self):
        return '--account=' + self.__account
    
    @property
    def queue(self):
        return '-q ' + self.__queue
    
    @property
    def output_file(self):
        return '-o{}-%j.out'.format(self.__output_file)
    
    @staticmethod
    def wall_time_formatter(td: timedelta) -> str:
        """
        you get issues upon direct string conversion of time delta
        because pace doesn't allow a "date" field for walltime - the largest
        unit of time is hour and it wants the wall time in:

        HH:MM:SS

        format
        """

        def _str_formatter(integer: int) -> str:

            if integer < 10:
                return '0' + str(integer)
            else:
                return str(integer)
    
        HOURS_PER_DAY = 24.0
        MINUTES_PER_HOUR = 60.0
        SECONDS_PER_MINUTE = 60.0

        hours = td.days*HOURS_PER_DAY
        hours += math.floor(td.seconds/(MINUTES_PER_HOUR*SECONDS_PER_MINUTE))
        hours =int(hours)
        _minutes = td.seconds % (MINUTES_PER_HOUR*SECONDS_PER_MINUTE)
        minutes = int(math.floor(_minutes/SECONDS_PER_MINUTE))
        seconds = int(_minutes % SECONDS_PER_MINUTE)

        td_str = ''
        for unit in [hours,minutes,seconds]:
            td_str += _str_formatter(unit) + ':'

        return td_str[0:-1]

    @property
    def walltime(self):
        td = timedelta(seconds = self.__walltime)
        return '-t' + self.wall_time_formatter(td)
    
    @property
    def memory(self):

        if self.memory_request == 'p':
            return  '--mem-per-cpu={}G'.format(self.__memory)
        else:
            raise NotImplementedError("haven't implemented total memory request for Slurm Scirpts")
    
    
    @property
    def processesors_nodes(self):
        return '-N' + str(self.__nodes) + ' --ntasks-per-node=' + str(self.__processors)
    
    @property
    def email(self):
        if self.__email is None:
            return self.__email
        else:
            return '--mail-user='+  self.__email
    

    @name.setter
    def name(self,n):
        self.__name = n
    
    def format_pbs_header(self):

        txt = '#!/bin/bash' + self.LINE_BREAK
        for item in [self.name,self.account,self.queue,self.output_file,self.walltime,
                     self.memory,self.processesors_nodes,self.email]:
        
            if item is not None:
                txt += self.line_leader + ' ' + item + self.LINE_BREAK
        
        return txt

    def copy(self):
        return deepcopy(self)

    def __call__(self):
        return self.format_pbs_header()

class DefaultSlurm(Slurm):

    """
    a default pbs script. The account and queue are now hardcoded into the initializer
    while variables such as walltime,memory, nodes and processors are still required
    """
    
    def __init__(self,name: str,
                       walltime: float,
                       memory:float,
                       nodes: int,
                       processors: int,
                       output_file = 'fluent.out',
                       email = None,
                       email_permissions = None,
                       memory_request = 'p',
                       account = 'gts-my14'):


        super().__init__(name,account,'inferno',output_file,walltime,
                        memory,nodes,processors,email = email,
                        email_permissions= email_permissions,memory_request = memory_request)


class PythonSlurm(SerializableClass):

    SLURM_PDIR = '$SLURM_SUBMIT_DIR'

    def __init__(self,
                 script: PaceScript,
                 version = '2019.10',
                 name = 'python_deployment',
                 WALLTIME = 10,
                 MEMORY = 1,
                 N_NODES = 1,
                 N_PROCESSORS = 1,
                 slurm = DefaultSlurm,
                 account = 'gts-my14',
                 memory_request = 'p'):

        self.slurm = slurm(name,WALLTIME,MEMORY,N_NODES,N_PROCESSORS,
                            'python_pace.out',memory_request = memory_request,
                            account = account)
        
        self.script = script
        try:
            if not os.path.exists(self.script.target_dir):
                os.mkdir(self.script.target_dir)
        except TypeError:
            pass
        
        self.version = version

    @staticmethod
    def format_change_dir(chdir)-> str:
        """
        this is important to change to the PBS dir which is an environment variable 
        native to the bash shell on PACE
        """
        return 'cd ' + chdir
    
    def format_load_anaconda(self) -> str:

        return 'module load anaconda3/{}'.format(self.version)

    def format_run_script(self) -> str:

        return 'python ' + self.script.script_name
    
    def format_call(self):

        txt = self.slurm() + self.LINE_BREAK
        txt += self.format_change_dir(self.SLURM_PDIR) +self.LINE_BREAK
        txt += self.format_load_anaconda() + self.LINE_BREAK
        txt += self.script.setup() 
        txt += self.format_run_script() + self.LINE_BREAK

        return txt
    
    def __call__(self):
        """
        callable interface here
        """
        return self.format_call()
    
    def write(self,f):
        """
        write the script to a file or IOStream (whatever its called in python)
        """
        if self.script.target_dir is None:
            self.script.target_dir,_ = os.path.split(f)

        try:
            with open(f,'w',newline = self.LINE_BREAK) as file:
                file.write(self.format_call())

        except TypeError:
            f.write(self.format_call())

    def _from_file_parser(dmdict):
        """
        parser from the file that allows instantation from file
        """
        dmdict['_cached_pbs'] = dmdict.pop('pbs')
        dmdict.pop('class')
        input_file = dmdict.pop('input_file')
        dmdict['mpi_option'] = dmdict.pop('mpi_opt')
        return [input_file],dmdict

def main():

    slurm = DefaultSlurm('test',1500,8,1,8)
    print(slurm())

if __name__ == '__main__':
    main()