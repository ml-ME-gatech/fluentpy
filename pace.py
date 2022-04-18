from abc import ABC, abstractmethod, abstractproperty
import subprocess
from io import StringIO
from typing import Tuple, Union, Any, List
import re
import os
import shutil
import time
from datetime import datetime,timedelta

"""
Author: Michael Lanahan
Date Created: 04.07.2022
Last Edit: 04.12.2022
"""

PACE_SCIPT_NAME = 'pace_monitor.py'

class PaceCommand(ABC):

    """
    Base class for issuing a command on PACE
    """
    LINEBREAK = '\n'

    def __init__(self,*args,**kwargs):

        pass

    @abstractmethod
    def __str__(self):
        pass

    def __call__(self):
        return subprocess.run(self.__str__(),shell= True,
                capture_output= True,text= True).stdout

class PaceOut(ABC):
    """
    Base class for collecting output from PACE and parsing it
    """
    LINEBREAK = '\n'

    def __init__(self,output:Union[str,StringIO]):

        self.output = output
    
    @abstractmethod
    def parse_output(self) -> str:
        pass

    @abstractproperty
    def json_data(self):
        pass

class PaceCommunication(ABC):
    """
    Base class for the communication between PACE and a python script
    which consists of a command and an output parser
    """
    def __init__(self,*args,
                       pace_command = PaceCommand,
                       pace_out = PaceOut,
                       **kwargs):

        self.pace_command = pace_command(*args,**kwargs)
        self.pace_out_cls = pace_out

    def __call__(self, *args,**kwargs):
        txt = self.pace_command()
        self.pace_out = self.pace_out_cls(txt,*args,**kwargs)
        self.pace_out.parse_output()
        return self.pace_out.json_data

class CheckJobCommand(PaceCommand):
    """
    Issue a "check job" command to PACE
    """
    def __init__(self,jobid: str) -> None:

        super().__init__(jobid)
        self.jobid = jobid
    
    def __str__(self)-> str:
        return 'checkjob ' + str(self.jobid) 

class CheckJobOutput(PaceOut):
    """
    Collect the output from a "check job" command from PACE
    """
    def __init__(self,output:Union[str,StringIO]):

        super().__init__(output)

        self.__data = {}

    @staticmethod
    def parse_line(line: str) -> Tuple:
        
        splittext = line.split(':',1)
        return splittext[0].strip(),''.join(splittext[1].strip())

    def parse_output(self) -> str:
        
        splitted = re.split(self.LINEBREAK,self.output)

        for line in splitted:
            try:
                key,value = self.parse_line(line)
                self.__data[key] = value
            except IndexError:
                pass
            
    @property
    def json_data(self):
        return self.__data

class CheckJob(PaceCommunication):

    """
    Class for issuing the "CHeck Job" command on pace
    and then collecting the subsequent outpout
    """
    def __init__(self,jobid: Union[str,StringIO]):

        super().__init__(jobid,pace_command= CheckJobCommand,
                                pace_out = CheckJobOutput)

class PaceScript:

    LINEBREAK = '\n'
    ENV_SETUP = 'env_setup.sh'

    def __init__(self,script: str,
                      target_dir: str,
                      libs = [],
                      envs = [],
                      python_version = '3.8.8',
                      script_modifications = None):

        self.script = script
        _,self.script_name = os.path.split(self.script)
        self.target_dir = target_dir
        self.libs = libs
        self.envs = envs
        self.python_version = python_version
        self.script_modifications = script_modifications

    def _setup_script(self) -> None:
        #move script to this directory
        if not os.path.exists(self.target_dir):
            raise FileNotFoundError('target directory for PACE python script does not exist: {}'.format(self.target_dir))
        elif not os.path.isdir(self.target_dir):
            raise FileExistsError('{} is not a directory'.format(self.target_dir))
        else:
            with open(self.script,'r') as file:
                txt = file.read()
            
            if self.script_modifications is not None:
                txt = self.script_modifications(txt)
            
            _,file_name = os.path.split(self.script)
            with open(os.path.join(self.target_dir,file_name),'w') as file:
                file.write(txt)
    
    def _setup_lib(self) -> None:
        for lib in self.libs:
            if os.path.exists(lib):
                shutil.copy2(lib,self.target_dir)
            else:
                print('WARNING::could not find library: {}'.format(lib))
    
    def _setup_env(self) -> None:
        
        #export all listed enviornments
        cmds = self.env_export()
        for cmd in cmds:
            subprocess.run(cmd,shell = True)
        
        #write the deployment script to a file
        return self.env_deploy()
        
    def env_export(self) -> str:

        cmds = []
        for env in self.envs:
            file_name = os.path.join(self.target_dir,env + '.yml')
            cmds.append('conda-env export -n ' + env + ' > ' + file_name)
        
        return cmds

    def env_deploy(self) -> str: 

        text = 'echo "Setting up conda virtual environments...."' + self.LINEBREAK
        for env in self.envs:
            text += 'conda-env create -n ' + env + ' -f='+ env + '.yml' +  self.LINEBREAK
        
        text += 'echo "Completed settuping up conda virtual enviornments"' + self.LINEBREAK
        return text

    def setup(self):

        self._setup_script()
        self._setup_lib()
        return self._setup_env()
    
    def write(self,f: str):

        self.target_dir,_ = os.path.split(f) 
        self.setup()
        

class QueuedJobs(ABC):

    def __init__(self,pbs_files: List[str]):

        self.pbs_files = pbs_files
        self.__queue = self.make_queue(pbs_files)
    
    @abstractmethod
    def exit_queue_condition(self):
        pass

    @abstractmethod
    def make_queue(self):
        pass

    def submit_job(self):

        #run the .pbs script in question in question
        cmd = 'qsub ' + next(self.__queue)
        output = subprocess.run(cmd,shell= True,
                                capture_output= True,
                                text= True)
        return output.stdout

class SquentialJobs(QueuedJobs):

    time_format = "%H:%M:%S"

    def __init__(self,first_pbs_file: str,
                      second_pbs_file: str,
                      check_time = 10.0):

        super().__init__([first_pbs_file,second_pbs_file])
        self.check_time = check_time

    def exit_queue_condition(self):

        exit_status = False
        wall_time = self.get_wall_time()
        t0 = time.time()
        status = ''
        while True:
            if status.lower() == 'completed':
                exit_status = True
                break
            else:
                time.sleep(self.check_time)
                status = get_job_status(self.first_job_id)
                if status is None:
                    status = ''

            t1 = time.time()
            dt = t1-t0
            if dt > wall_time:
                break

        return exit_status
                
    def get_wall_time(self):

        with open(self.pbs_files[0],'r') as file:
            for line in file.readlines():
                if 'walltime' in line:
                    line = line.split('=')[1].strip()
                    t = datetime.strptime(line,self.time_format)
                    delta = timedelta(hours = t.hours,minuties = t.minute,
                                      second = t.second)
                    break
        
        return delta.total_seconds()

    def run_jobs(self):

        output = self.submit_job()
        self.first_job_id = output.stdout.split('.')[0]
        exit_status = self.exit_queue_condition()
        if not exit_status:
            print('First job in sequntial job series did not finish before specified walltime') 
        
        self.submit_job()
        


def get_job_status(jobid: str) -> Union[str,None]:
    """
    simplified function checking the status of a job
    submitted on PACE 
    """
    pc = CheckJob(jobid)
    json_data = pc()
    try:
        return json_data['State']
    except KeyError:
        return None
    
def main():

    filename = 'test/pace-files/checkjob_output.txt'
    with open(filename,'r') as file:
        string_data = file.read()
    
    cjo = CheckJobOutput(string_data)

    cjo.parse_output()
    print(cjo.json_data['State']) 

if __name__ == '__main__':
    main()
