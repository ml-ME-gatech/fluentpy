from typing import Union
from pathlib import WindowsPath,PosixPath, PurePath
import os
import sys
import subprocess

submit_file = '<submit_file>'
solution_file_name  = '<solution_file_name>'
backend = '<backend>'

def check_completed(path: Union[WindowsPath,PosixPath]) -> bool:

    for file in path.iterdir():
        if file.name == solution_file_name:
            return True
    
    return False

def submit_job(file: str,
                backend: str) -> str:

    #run the .pbs script in question in question
    text = backend + ' ' + file
    subprocess.run(text,shell= True,capture_output= True,text= True)

def resubmit_job(path: Union[WindowsPath,PosixPath]):

    os.chdir(path.name)
    submit_job(submit_file)
    os.chdir('..')

def main():
    os_name = sys.platform
    if os_name == 'win32' or os_name == 'win64':
        _PATH = WindowsPath
    elif os_name == 'linux' or os_name == 'posix':
        _PATH = PosixPath
    else:
        raise ValueError('Cannot determine Path structure from platform: {}'.format(os_name))

    path = _PATH(__file__)
    path = _PATH(path.parent)

    for file in path.iterdir():
        if file.is_dir():
            if not check_completed(file):
                resubmit_job(file)
        
if __name__ == '__main__':
    main()



