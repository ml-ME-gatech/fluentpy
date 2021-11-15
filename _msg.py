#third party imports
import os

#package imports
from .fluentPyconfig import settings
msg_settings = settings.from_env('messages')

__all__ = ['']

"""
_msg.py is a "hidden" or support level python file that contains function interfaces
to the messaging available in the messages folder. Essentially, it is nice to organize the messages
into various folders depending upon their intent so that we can have repeat message names
for related messages in different contexts e.g. error vs warning vs report

Messages can be quite long, and thus, to improve readibility of the code I found it nice to
store them in .msg files (essentially text files) in order to reduce the length of the other 
python files
"""

def _get_message(folder,msg_name):

    path,_ = os.path.split(__file__)
    path = os.path.join(path,msg_settings.folder,folder,msg_name+'.msg')
    try:
        with open(path,'r') as file:
            txt = file.read()
    
    except FileNotFoundError:
        raise FileNotFoundError('\nMessage at location:\n {} \n not found'.format(path))

    return txt

def get_warning_message(msg_name):

    return _get_message(msg_settings.warning_folder,msg_name)

def get_error_message(msg_name):

    return _get_message(msg_settings.error_folder,msg_name)

def get_report_message(msg_name):

    return _get_message(msg_settings.report_folder,msg_name)