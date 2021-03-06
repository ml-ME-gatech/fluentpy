from multiprocessing.sharedctypes import Value
from typing import List, Union
from pathlib import PurePath, WindowsPath,PosixPath
import os
import shutil
import sys
import json

DAT_PATH = 'dat'
def get_fluent_path(version: str) -> PurePath:

    """ 
    get the fluent path based on available versions

    Parameters
    ---------
    version : str
            fluent version as a string, like:
            19.1 
    """

    path,_ = os.path.split(__file__)

    file_name = os.path.join(path,DAT_PATH,'fluent-paths.json')

    with open(file_name,'r') as file:
        paths = json.load(file)
    
    if version not in paths:
        string = 'allowable fluent versions:\n' + [v for v in paths].join('\n')
        raise ValueError('fluent version {} not allowed.\n {}'.format(version,string))

    return paths[version]


def sort_list_of_lists_by_list_len(input_list: list) -> list:

    list_len = [len(inner) for inner in input_list]
    permutation = sorted(range(len(list_len)), key = lambda t: list_len[t])

    return permutation

def apply_permutation_to_list(input_list: list,
                              permutation: list) -> list:

    return [input_list[i] for i in permutation]

def _surface_construction_arg_validator(id: list,
                                        variable: list,
                                        surface_type: list) -> tuple:

    """
    static function meant to validate the construction arguments
    also converts all of the arguments
    id,variable,surface_type 

    into lists by default so that multiple evaluations may be made with a single
    fluent engine call. If the input is a str for each of these, the list
    will be a len = 1 list.
    """

    return_tuple = []
    variable_names = ['id','variable','surface_type']
    len_list = 0
    cc= 0
    for list_or_str,var_name in zip([id,variable,surface_type],variable_names):
        if isinstance(list_or_str,str):
            return_tuple.append([list_or_str])
        elif isinstance(list_or_str,list):
            if var_name == 'id':
                to_append = []
                for item in list_or_str:
                    if isinstance(item,str) or isinstance(item,int):
                        to_append.append([str(item)])
                    elif isinstance(item,list):
                        inner_append = []
                        for inner_item in item:
                            inner_append.append(str(inner_item))
                        
                        to_append.append(inner_append)
                    else:
                        raise ValueError('ids may only be specified as integer or strings')
                
                return_tuple.append(to_append)

            else:
                for item in list_or_str:
                    if not isinstance(item,str):
                        raise ValueError('{} may only be specified as strings'.format(var_name))
                
                return_tuple.append(list_or_str)

        elif isinstance(list_or_str,int) and var_name == 'id':
            return_tuple.append([str(list_or_str)])
        else:
            raise ValueError('argument: {} must be a string or a list'.format(var_name))
        
        if cc == 0:
            len_list = len(return_tuple[0])
        
        if len(return_tuple[-1]) != len_list:
            raise ValueError('All input variables must be lists of the same length')

        cc+=1

    #getting some really weird bugs if the number of id's is not
    #greater than or equal to the previous number of listed id's
    #on multiple surface integral evaluations
    _return_tuple = []
    len_perm = sort_list_of_lists_by_list_len(return_tuple[0])
    for rt in return_tuple:
        _return_tuple.append(apply_permutation_to_list(rt,len_perm))
        
    return tuple(_return_tuple) 

def main():

    make_udf_folder_structure_linux('test_udf_arch',['xvelocity.c'],
                                    'lnamd64',False,'2ddp')

if __name__ == '__main__':
    main()