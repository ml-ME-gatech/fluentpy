from tui.fluent import CaseDataReader
import os
import subprocess

WINDOWS_FLUENT_INIT_STATEMENT = 'fluent {} -t{} -g -i {} -o {}'
FLUENT_INPUT_NAME = 'input.fluent'
FLUENT_OUTPUT_NAME = 'output.fluent'
LINE_BREAK = '\n'
EXIT_CHAR = 'q' + LINE_BREAK
EXIT_STATEMENT = 'exit'

class FluentEngine:

    """
    main class for the post processing engine using fluent
    """
    def __init__(self,file: str,
                      specification = '3ddp',
                      num_processors = 1,
                      reader = CaseDataReader):
        
        self.path,file_name = os.path.split(file)
        self.spec = specification
        self.__num_processors = num_processors
        self.__input = reader(file_name)
        self._additional_txt = ''
        self.input_file = os.path.join(self.path,FLUENT_INPUT_NAME)
        self.output_file = os.path.join(self.path,FLUENT_OUTPUT_NAME)
    

    def insert_text(self,other):
        self._additional_txt += other
    
    @property
    def num_processors(self):
        return str(self.__num_processors)

    def _fluent_initializer(self,
                            system = 'windows'):
        
        if system == 'windows':
            return WINDOWS_FLUENT_INIT_STATEMENT.format(self.spec,
                                                        self.num_processors,
                                                        FLUENT_INPUT_NAME,
                                                        FLUENT_OUTPUT_NAME) + EXIT_CHAR
    

    @property
    def input(self):
        return str(self.__input)
    
    def format_call(self):
        """
        format the text for the call, and also write the input file for 
        fluent
        """
        call_text = self._fluent_initializer()
        self.format_input_file()
        return call_text
    
    def format_input_file(self) -> None:
        """
        format the input file to fluent to read and create the surface integral
        """
        txt = self.input + LINE_BREAK
        txt += self._additional_txt + LINE_BREAK
        txt += EXIT_STATEMENT + LINE_BREAK

        with open(self.input_file,'w') as file:
            file.write(txt)
    
    def clean(self):
        """ 
        clean directory from input and output files
        """
        if os.path.exists(self.input_file):
            os.remove(self.input_file)
        
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
        
    def __call__(self):
        """
        This call does the following:
        (1) cleans the directory of the fluent case file from input and output files
        (2) formats the call
        (3) opens fluent and submits commands to fluent
        (4) cleans up the directory again
        """

        self.clean()
        txt = self.format_call()
        cwd = os.getcwd()
        os.chdir(self.path)
        process = subprocess.call(txt)
        os.chdir(cwd)
        self.clean()
        return process
