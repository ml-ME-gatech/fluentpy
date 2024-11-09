"""
Author: Michael Lanahan, Matthew Chan
Date Created: 04.04.2022
Last Edit 04.04.2022

Integration with the other products in the ansys suite
"""

import os
import sys
from pathlib import WindowsPath,PosixPath
import subprocess
from copy import deepcopy

from .submit import FluentSubmission,PaceFluentSubmission,FluentBatchSubmission
from .table_parse import partition_boundary_table
from typing import Tuple,List, Type,Union, Any
from .fluent import FluentScript
from .pbs import DefaultPBS, PythonPBS
from .slurm import DefaultSlurm, PythonSlurm
from pandas import DataFrame
from ..tui import FluentJournal,BatchCaseReader
from ..fluentio import SurfaceFile
from .batch_util import _parse_pykwargs
from ..pace import PaceScript

LINE_BREAK = '\n'

dat_path = os.path.split(os.path.split(__file__)[0])[0]
dat_path = os.path.join(dat_path,'dat')

class MechanicalScript(FluentScript):
    
    def __init__(self, *args, input_file = 'mechanical.wbjn',
                       **kwargs):
        super().__init__(*args,input_file,**kwargs)

    def format_call(self):
        """
        format the whole script here
        """
        txt = self.script_header() + LINE_BREAK
        txt += self.format_change_dir(self.PDIR) +LINE_BREAK
        txt += self.format_load_ansys(self.version) +LINE_BREAK
        txt += self.format_mechanical_footer(self.input_file) \
                + LINE_BREAK

        return  txt

    def format_mechanical_footer(self, input_file: str) -> str:
        """
        format the mechanical call in the pbs script
        """
        return 'runwb2 -B -R "' + input_file + '"'

class MechanicalPBS(MechanicalScript):

    def __init__(self,*args,**kwargs):

        super().__init__(*args,script_header= DefaultPBS,**kwargs)
        self.PDIR = '$PBS_O_WORKDIR'
        self.NODE_FILE = '$PBS_NODEFILE'

class MechanicalSlurm(MechanicalScript):

    def __init__(self,*args,**kwargs):

        super().__init__(*args,script_header= DefaultSlurm,**kwargs)
        self.PDIR = '$SLURM_SUBMIT_DIR'
        self.NODE_FILE = '$SLURM_JOB_NODELIST'
    
class APDL_Script(FluentScript):
    
    def __init__(self, *args, input_file = 'ansys.input',
                       **kwargs):
        
        super().__init__(*args,input_file,**kwargs)

    def format_call(self):
        """
        format the whole script here
        """
        txt = self.script_header() + LINE_BREAK
        txt += self.config + LINE_BREAK
        txt += self.format_change_dir(self.PDIR) +LINE_BREAK
        txt += self.format_load_ansys(self.version) +LINE_BREAK
        txt += self.format_apdl_footer(self.input_file) \
                + LINE_BREAK

        return  txt

    def format_apdl_footer(self, input_file: str) -> str:
        """
        format the mechanical call in the pbs script
        """
        return 'ansys231 -s noread -smp -np $SLURM_NTASKS -b  < ' + input_file + ' > apdl.out 2>&1'

class APDL_PBS(APDL_Script):

    def __init__(self,*args,**kwargs):

        super().__init__(*args,script_header= DefaultPBS,**kwargs)
        self.PDIR = '$PBS_O_WORKDIR'
        self.NODE_FILE = '$PBS_NODEFILE'

class APDL_Slurm(APDL_Script):

    def __init__(self,*args,**kwargs):

        super().__init__(*args,script_header= DefaultSlurm,**kwargs)
        self.PDIR = '$SLURM_SUBMIT_DIR'
        self.NODE_FILE = '$SLURM_JOB_NODELIST'


class APDL_Journal: 

    def __init__(self,file: str):

        self.file = WindowsPath(file)
        self.input_file = self.file.name

    def __str__(self):

        with open(self.file,'r') as file:
            txt = file.read()
        
        return txt
    
    def write(self, filename: str):
        with open(filename, 'w') as file:
            file.write(str(self))

class MechanicalTemplate:

    OUTPUT_FILE_NAME = 'mech_result.csv'

    TEMPLATE_DICT = {'single':'external.wbjn.template',
                     'batch':'external.batch.wbjn.template'}

    def __init__(self, archive_path: str, 
                       surface_files: List[SurfaceFile],
                       project_path = 'mech_result.wbpj', 
                       output_parameter_file = None,
                       template_file = 'single',
                       version='19.1.103',
                       save = True):
        
        if output_parameter_file is None:
            self.output_parameter_file = self.OUTPUT_FILE_NAME
        else:
            self.output_parameter_file = output_parameter_file
        
        if not isinstance(surface_files,list) and not isinstance(surface_files,dict):
            if isinstance(surface_files,SurfaceFile):
                surface_files = [surface_files]
            else:
                raise ValueError('surface_files must be a SurfaceFile or a list of SurfaceFile')
            
        self.save = save
        self.version = version
        self.archieve_path = archive_path
        self.project_path = project_path
        if template_file not in self.TEMPLATE_DICT:
            raise FileNotFoundError('template file must be specified by one of: (1) single (2) batch')

        self.template_file = template_file
        self.surface_files = surface_files

    def read_template(self)-> str:
        template_file = self.TEMPLATE_DICT[self.template_file]
        with open(os.path.join(dat_path,template_file), 'r') as file:
            text = file.read()

        return text    

    def __str__(self):
        text = self.read_template()
        template_editor = TemplateEditor(text)
        
        if isinstance(self.surface_files,list):
            data_file_names = {s.output_file: s.output_file for s in self.surface_files}
        elif isinstance(self.surface_files,dict):
            data_file_names = {file_name:s.output_file for file_name,s in self.surface_files.items()}
        else:
            raise TypeError('surface files must be specifed as a dictionary or a list')

        kwargs = {'version': self.version,
                  'archive_path': self.archieve_path,
                  'project_path':self.project_path,
                  'save':self.save,
                  'export_file':self.output_parameter_file,
                  'data_file_names':data_file_names}

        return template_editor(**kwargs)

    def write(self, filename: str):
        with open(filename, 'w') as file:
            file.write(str(self))
            

class TemplateEditor:

    kwarg_delim = '#<SET_KWARGS>'

    def __init__(self,text: str):
        
        self.text = text

    def edit_numeric(self,
                     name: str,
                     value : Union[float,int]) -> str:
        
        if name is None:
            return str(value)
        else:
            return name + ' = ' + str(value)

    def edit_string(self,
                    name: str,
                    value: str) -> str:
        
        if name is None:
            return "'" + value + "'"
        else:
            return name + ' = ' + "'" + value + "'"
    
    def edit_bool(self,
                  name: str,
                  value: bool) -> str:

        if value:
            value = 'True'
        else:
            value = 'False'
        
        if name is None:
            return value
        else:
            return name + ' = ' + value
        
    def edit_list(self,
                  name: str,
                  value: List) -> str:
        
        text = name + ' = ' + '[' + LINE_BREAK
        for v in value:
            text += self.stringify_value(None,v) + ',' + LINE_BREAK
        
        text = text[0:-2] + ']'
        return text

    def edit_dict(self,
                  name: str,
                  value: List) -> str:
        
        text = name + ' = ' + '{' + LINE_BREAK
        for n,v in value.items():
            _n = self.stringify_value(None,n)
            _v = self.stringify_value(None,v)

            text += _n + ':' + _v + ',' + LINE_BREAK
        
        text = text[0:-2] + '}'
        return text

    def stringify_value(self,name: Any,
                             value: Any) -> str:

        if isinstance(value,str):
            return self.edit_string(name,value)
        elif isinstance(value,bool):
            return self.edit_bool(name,value)
        elif isinstance(value,dict):
            return self.edit_dict(name,value)
        elif isinstance(value,list):
            return self.edit_list(name,value)
        else:
            try:
                return self.edit_numeric(name,value)
            except (TypeError,AttributeError) as error:
                raise TypeError('cannot convert kwarg: {} to string'.format(name) + '\n' + error)
    
    def edit_text(self,**kwargs) -> str:

        text = ''
        for name,value in kwargs.items():
            text += self.stringify_value(name,value) + LINE_BREAK

        return text
    
    def __call__(self,**kwargs) -> str:

        editted_text = self.edit_text(**kwargs)
        if self.kwarg_delim in self.text:
            text = self.text.replace(self.kwarg_delim,editted_text)
            return text
        else:
            raise ValueError('Missing kwarg delim: {} cannot format template'.format(self.kwarg_delim))

class PaceAPDLSubmission(FluentSubmission):

    PACE_ADPL_SCRIPT = 'apdl.{}'

    def __init__(self,apdl_journal:APDL_Journal,
                      apdl_script: APDL_Script):

        super().__init__(None)

        self.apdl_journal = apdl_journal
        self.apdl_script = apdl_script

        if isinstance(apdl_script,APDL_PBS):
            self.PACE_ADPL_SCRIPT = self.PACE_ADPL_SCRIPT.format('pbs')
        elif isinstance(apdl_script,APDL_Slurm):
            self.PACE_ADPL_SCRIPT = self.PACE_ADPL_SCRIPT.format('slurm')
        else:
            raise NotImplementedError('not a valid script for apdl submissions on PACE')
        
        self.write_file_attributes = {'apdl_journal':self.apdl_journal.input_file,
                                      'apdl_script': self.PACE_ADPL_SCRIPT}
    
    def execute_command(self, f: str) -> str:
        pass

    def _from_file_parser(dmdict : dict):
        
        apdl_script = dmdict['apdl_script']['class']
        script = apdl_script.from_dict(dmdict['apdl_script'])
        apdl_journal = dmdict['apdl_journal']['class']
        journal = apdl_journal.from_dict(dmdict['apdl_journal'])

        return ([journal,script],)

    def pre_write(self, folder: str) -> None:
            pass

class PaceMechanicalSubmission(FluentSubmission):

    PACE_MECH_PBS = 'mechanical.pbs'

    def __init__(self,  mechanical_journal: MechanicalTemplate, 
                        mechanical_pbs: MechanicalPBS):

        super().__init__(None)

        self.mechanical_journal = mechanical_journal
        self.mechanical_pbs = mechanical_pbs

        self.write_file_attributes = {'mechanical_journal':mechanical_pbs.input_file,
                                      'mechanical_pbs':self.PACE_MECH_PBS}

    def execute_command(self, f: str) -> str:
        pass
    
    def _from_file_parser(dmdict : dict):
        
        mechanicalpbs = dmdict['mechanical_pbs']['class']
        pbs = mechanicalpbs.from_dict(dmdict['mechanical_pbs'])
        mechanicalrun = dmdict['mechanical_journal']['class']
        run = mechanicalrun.from_dict(dmdict['mechanical_journal'])

        return ([run,pbs],)

    def pre_write(self, folder: str) -> None:
            pass

class PaceFluentMechanicalSimulation(PaceFluentSubmission):

    DEFAULT_PYTHON_SCRIPT = 'delayed_deploy.py'

    def __init__(self,fluent_submission: PaceFluentSubmission,
                      mechanical_submission: PaceMechanicalSubmission,
                      **pykwargs):
        
        pykwargs = _parse_pykwargs(self.DEFAULT_PYTHON_SCRIPT,**pykwargs)

        #port over surface files to be exported
        for surface_file in mechanical_submission.mechanical_journal.surface_files:
            fluent_submission.fluent_journal.post.append(surface_file)

        #get names consistent
        mechanical_submission.mechanical_journal.fluent_data_file =\
                fluent_submission.fluent_journal.data_writer.file

        super().__init__(fluent_submission.fluent_journal,
                         fluent_submission.fluent_pbs,
                         **pykwargs)

        self.PACE_PBS = fluent_submission.write_file_attributes['fluent_pbs']
        self.mechanical_submission = mechanical_submission
        wfa = self.write_file_attributes
        wfa['mechanical_submission'] = self.mechanical_submission
        self.write_file_attributes = wfa

    def pre_write(self, folder: str) -> None:
    
        self.python_script.target_dir = folder
        if self.python_script.script_name == 'delayed_deploy.py':
            def script_modification(txt:str) -> str:
                text = txt.replace('<file1>',self.PACE_PBS)
                text = text.replace('<file2>',self.mechanical_submission.PACE_MECH_PBS)
                return text
        elif self.python_script.script_name == 'single_deploy.py':
            def script_modification(txt:str) -> str:
                text = txt.replace('<file_name>',self.PACE_PBS)
                return text
        else:
            raise ValueError('python script with script name: {} is not supported'.format(self.python_script.script_name))
        
        self.python_script.script_modifications = script_modification

        for surface_file in self.mechanical_submission.mechanical_journal.surface_files:
            surface_file.write(folder)

class SequentialPaceSubmission(FluentSubmission):
    """
    class for executing submissions sequentially
    """

    DEFAULT_PYTHON_SCRIPT = 'sequential_deploy.py'

    path,_ = os.path.split(os.path.split(__file__)[0])
    script_path = os.path.join(path,'dat','scripts')

    def __init__(self, submission_jobs: List[Union[PaceAPDLSubmission,PaceFluentSubmission,PythonPBS,PythonSlurm]],
                        python_script = PaceScript,
                        script_name = None,
                        **pykwargs):

        super().__init__(None)
        pykwargs = _parse_pykwargs(self.DEFAULT_PYTHON_SCRIPT,**pykwargs)
        self.submission_jobs = submission_jobs
        
        script_name = os.path.join(self.script_path,pykwargs.pop('script_name'))
        
        self.python_script = python_script(script_name,None,libs = pykwargs['python_libs'])

        self.write_file_attributes = {'python_script':self.python_script.script_name}
        
    def execute_command(self, f: str) -> str:
        return ['python ',self.python_script.script_name]
    
    def pre_write(self, folder: str) -> None:
    
        self.python_script.target_dir = folder
        if self.python_script.script_name == 'sequential_deploy.py':
            def script_modification(txt:str) -> str:
                text = txt.replace('<file_list>',self.PACE_PBS)
                return text
        else:
            raise ValueError('python script with script name: {} is not supported'.format(self.python_script.script_name))
        
        self.python_script.script_modifications = script_modification

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
        for submission in self.submission_jobs:
            submission.write(folder)
        
    def _from_file_parser(self,dmdict: str):

        raise NotImplementedError('not implmented')
    
class PaceFluentMechanicalBatchSubmission(FluentBatchSubmission):

    SUBMISSION_CLASS = PaceFluentMechanicalSimulation

    def __init__(self,fluent_submission_list: List[PaceFluentMechanicalSimulation],
                      index = None,
                      prefix = '',
                      seperator = '-',
                      case_file = None,
                      archive_file = None,
                      move_batch_files = []):

        super().__init__(fluent_submission_list,
                         index = index,
                         prefix = prefix,
                         seperator = seperator,
                         case_file = case_file,
                         move_batch_files = move_batch_files)
        
        #these are fixed on PACE
        self.PACE_PBS = fluent_submission_list[0].PACE_PBS
        self.BATCH_EXE_FNAME = 'batch.sh'
        self.TERMINAL_TYPE = 'bash'
        self.archive_file = archive_file

    def generate_submission(self,parent: str,
                            purge=False, 
                            verbose=True,
                            overwrite = False) -> None:

        _bf = os.path.join(parent,self.BATCH_EXE_FNAME)
        txt = self.make_batch_submission(parent,
                                        verbose = verbose, 
                                        purge = purge,
                                        overwrite = overwrite)

        with open(_bf,'w',newline = self.LINE_BREAK) as file:
            file.write(txt)

    @classmethod
    def from_frame(cls,
                   case_file: str,
                   archive_file: str,
                   surface_files: List,
                   turbulence_model:str,
                   df:DataFrame,
                   submission_args:List,
                   prefix = '',
                   seperator = '-',
                   script_name = None,
                   python_libs = [],
                   python_envs = [],
                   template_file = 'batch',
                   python_version = '2019.10',
                   save_mechanical = True,
                   *frargs,
                   **frkwargs):

        """
        sloppy job here..... this is quick and dirty and will have to be revisted in the future
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
        _,archive_name = os.path.split(archive_file)
        
        sl,index = cls._submission_list_from_boundary_df(cls.submission_args_from_boundary_df,
                                                         cls.SUBMISSION_CLASS,
                                                         case_name, archive_name,surface_files,
                                                          boundary_df, submission_args,
                                                          submission_kwargs,
                                                          seperator,
                                                          template_file = template_file,
                                                          save_mechanical = save_mechanical,
                                                          *frargs,**frkwargs)
        
        _cls = cls(sl,index = index,prefix = index.name,
                    case_file = case_file,
                    move_batch_files = [case_file,archive_file])
        

        _cls._df = df

        return _cls

    @staticmethod
    def _submission_list_from_boundary_df(submission_object_parser : callable,
                                          submission_class : object,
                                          case_name: str,
                                          arhive_name: str,
                                          surface_files: List,
                                          bdf:DataFrame,
                                          submission_args: list,
                                          submission_kwargs: dict,
                                          seperator: str,
                                          save_mechanical = True,
                                          template_file = 'batch',
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

            mech_template = MechanicalTemplate(arhive_name,surface_files,
                                               template_file = template_file,
                                               save = save_mechanical)
            
            fluent_journal.boundary_conditions = list(bdf.loc[index])
            submission_args =\
                 submission_object_parser(submission_args,
                                          case_name,index,name,seperator,
                                          *frargs,**frkwargs)

            fluent_submission = PaceFluentSubmission(deepcopy(fluent_journal),submission_args[0], **submission_kwargs)
            mech_submission = PaceMechanicalSubmission(mech_template,submission_args[1])

            submission = submission_class(fluent_submission,mech_submission,
                                    script_name = submission_kwargs['script_name'])
            
            submit_list.append(submission)
            
        
        return submit_list,bdf.index

    @staticmethod
    def submission_args_from_boundary_df(submission_args: list,
                                         case_name: str,
                                         index,
                                         name,
                                         seperator,
                                         *frargs,
                                         **frkwargs) -> Tuple:
        
        fpbs = submission_args[0].copy()
        mpbs = submission_args[1].copy()

        mpbs.pbs.name = name + seperator + str(index) + '-mech'
        fpbs.pbs.name = name + seperator + str(index)

        return (fpbs,mpbs)

class WorkBenchEngine:

    """
    Parameters
    ----------
    file : str
            string of the .wbjn file

    Examples
    --------

    .. code-block:: python
    

    """

    WB_INIT_STATEMENT = 'runwb2 -B -R "{}"'

    os_name = sys.platform
    if os_name == 'win32' or os_name == 'win64':
        PATH = WindowsPath
        system = 'windows'
    elif os_name == 'linux' or os_name == 'posix':
        PATH = PosixPath
        system = 'posix'
    else:
        raise ValueError('Cannot determine Path structure from platform: {}'.format(os_name))
    
    def __init__(self,file: str):
        
        self.path = self.PATH(file)
        self._additional_txt = ''

    def _format_call(self):
        """
        format the text for the call, and also write the input file for 
        fluent
        """
        return self.WB_INIT_STATEMENT.format(self.path.name)
     
    def __call__(self, save = None):
        """
        This call does the following:
        (1) formats the call
        (2) changes to the directory 
        (3) opens workbench and submits journal
        (4) changes back to the original directory
        """

        txt = self._format_call()
        cwd = os.getcwd()
        os.chdir(self.path.parent)
        process = subprocess.call(txt)
        os.chdir(cwd)
        return process