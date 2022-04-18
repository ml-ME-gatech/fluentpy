"""
Author: Michael, Matthew Chan
Date Created: 04.04.2022
Last Edit 04.04.2022

Integration with the other products in the ansys suite
"""

import os
from .submit import FluentSubmission
from .pbs import FluentPBS
from .pbs import DefaultPBS

LINE_BREAK = '\n'

dat_path = os.path.split(os.path.split(__file__)[0])[0]
dat_path = os.path.join(dat_path,'dat')

class MechanicalPBS(FluentPBS):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)

    def format_call(self):
        """
        format the whole script here
        """
        txt = self.pbs() + LINE_BREAK
        txt += self.format_change_dir(self.PBS_PDIR) +LINE_BREAK
        txt += self.format_load_ansys(self.version) +LINE_BREAK
        txt += self.format_mechanical_footer(self.input_file) \
                + LINE_BREAK

        return  txt

    def format_mechanical_footer(self, input_file: str) -> str:
        """
        format the mechanical call in the pbs script
        """
        return 'runwb2 -B -R "' + input_file + '"'

class PaceMechanicalSubmission(FluentSubmission):

    PACE_MECH_PBS = 'mechanical.pbs'

    def __init__(self, mechanical_journal, mechanical_pbs: MechanicalPBS):
        super().__init__(None)

        self.write_file_attributes = {'mechanical_journal':mechanical_pbs.input_file,
                                      'mechanical_pbs':self.PACE_MECH_PBS}

        self.mechanical_journal = mechanical_journal

        self.mechanical_pbs = mechanical_pbs

    def execute_command(self, f: str) -> str:
        return ['qsub ',self.PACE_MECH_PBS]
    
    def _from_file_parser(dmdict : dict):
        
        mechanicalpbs = dmdict['mechanical_pbs']['class']
        pbs = mechanicalpbs.from_dict(dmdict['mechanical_pbs'])
        mechanicalrun = dmdict['mechanical_journal']['class']
        run = mechanicalrun.from_dict(dmdict['mechanical_journal'])

        return ([run,pbs],)


        
class MechanicalJournal:

    def __init__(self, archive_path: str, 
                       project_path: str, 
                       finaldata_path: str, 
                       exportdata_path: str,
                       version='19.1.103'):
        
        self.version = version
        self.archieve_path = archive_path
        self.project_path = project_path
        self.finaldata_path = finaldata_path
        self.exportdata_path = exportdata_path

    def read_template(self)-> str:
        with open(os.path.join(dat_path,'.wbjn.template'), 'r') as file:
            text = file.read()
        return text    

    def __str__(self):
        text = self.read_template()
        return text.format(self.version, self.archieve_path, 
                            self.project_path, self.finaldata_path, 
                            self.exportdata_path)

    def write(self, filename: str):
        with open(filename, 'w') as file:
            file.write(str(self))  
        print(filename)
