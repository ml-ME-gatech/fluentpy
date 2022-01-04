#native imports
from pandas import DataFrame,Series
from typing import List, Type

#package imports
from ..tui import UDF, PressureOutlet,FluentFluidBoundaryCondition, MassFlowInlet,\
                  WallBoundaryCondition, VelocityInlet, FluentBoundaryCondition

""""
Author: Michael Lanahan
Date Created: 08.06.2021
Last Edit: 01.04.2021

utility functions and classes for working with Fluent Batch Files
and pace utility formatting
"""

MODELS = ['energy','ke-standard','kw-standard','viscous']
ALLOWABLE_BOUNDARY_TYPES = ['mass-flow-inlet','pressure-outlet','wall','velocity-inlet']
FLUID_BOUNDARY_CONDITIIONS = ['mass-flow-inlet','pressure-outlet']

def split_boundary_name(string: str,
                        delim = ':') -> tuple:
    """
    expects a boundary condition input in the format
    name:input:type 
    """ 
    return (s.strip() for s in string.split(delim))

def sort_boundary_list(blist: list,
                       delim = ':') -> dict:

    """
    essentially develops a "log" of boundary conditions that is a dictionary
    the keys of the dictionary are the names:type and the values of the dictionary
    are lists of the variables for that particular boundary condition
    """

    log = {}
    for item in blist:
        name,variable,btype = split_boundary_name(item)
        
        if btype not in ALLOWABLE_BOUNDARY_TYPES:
            raise TypeError('boundary condiiton type specified by: {} is not allowed'.format(btype))
        
        name = name + delim + btype
        try:
            log[name].append(variable)
        except KeyError:
            log[name] = [variable]
    
    return log

def partition_boundary_table(df: DataFrame,
                             turbulence_model: str,
                             delim = ':') -> DataFrame:

    """
    partition the input boundary table into a dataframe where the 
    columns are in the format

    >  name:type

    and the rows contain the boundary conditions of the appropriate type. The number
    of rows will be identical to the number of inputs rows of the table
    """
    
    models = _infer_models_from_headers(df.columns)
    sorted_df = sort_boundary_list(df.columns)
    boundary_list = dict.fromkeys(sorted_df.keys())
    for name,svars in sorted_df.items():
        _name = name.split(delim)
        cols = [_name[0]  + delim + c + delim + _name[1] for c in svars]
        bc_map = dict(zip(cols,sorted_df[name]))
        _df = df[cols]
        boundary_list[name] = []
        for i in df.index:
        
            try:
                bc_dict = _df.loc[i].to_dict()
            except IndexError:
                bc_dict = _df.loc[i].squeeze().to_dict()
            
            boundary_list[name].append(
            make_boundary_condition_from_series(_name[1],
                                                _name[0],
                                                bc_dict,
                                                bc_map,
                                                turbulence_model,
                                                models)
                                     )
    
    bdf = DataFrame.from_dict(boundary_list)
    bdf.index = df.index
    return bdf

def _infer_models_from_headers(columns: list) -> list:
    """
    simple function for infering models from the supplied headers. 
    This is not very sophisiticated at the moment and should be carefully
    tested later - right now there are not really any consequences though
    """

    models = []
    for column in columns:
        if 'temperature' in column or 'heat-flux' in column or 'trad' in column\
        or 'tinf' in column or 'convective_heat_transfer_coefficient' in column\
        or 'q_dot' in column or 'ex_emiss' in column or 'caf' in column:
            models.append('energy')
        
        if 'turbulent-dissipation-rate' or 'intensity' in column:
            models.append('ke-standard')
        
        if 'specific-dissipation-rate' in column:
            models.append('kw-standard')
    
    return list(set(models))


def _parse_udf_from_str(string : str) -> UDF:
    """
    expects the specification of a UDF as a string
    from a table to have the following format: 

    <file_name#condition_name#udf_name#data_name>

    OR

    <file_name#condition_name#udf_name#data_name#compile>

    the second option allows for compilation of the UDF during runtime

    example
    <htc.c#convection_coefficient#udf#HTC::UDF>

    The file name can be an absolute or relative path to the file
    """

    string = string.strip()
    
    if string[0] == '<' and string[-1] == '>':
        string = string[1:-1]
        try:
            file_name,condition_name,udf_name,data_name =\
                tuple([sstr.strip() for sstr in string.split('#')])
            
            udf = UDF(file_name,udf_name,data_name,condition_name)
            
            return udf
        except ValueError:
            file_name,condition_name,udf_name,data_name,compile =\
                tuple([sstr.strip() for sstr in string.split('#')])
            
            if compile.lower() == 'compile':
                compile = True
            else:
                raise TypeError('{} not a valid option for compile field'.format(compile))
            
            udf = UDF(file_name,udf_name,data_name,condition_name)
            udf.compile = True
            
            return udf

        except ValueError:
            raise ValueError('UDF Specified by: {} not valid'.format(string))

    else:
        raise ValueError('string does not specify a UDF')

def handle_udf_boundary_condition(cls: FluentBoundaryCondition,
                                  name: str,
                                  models: List[str],
                                  turbulence_model: str,
                                   **kwargs
                                    ) -> FluentBoundaryCondition:
        
    udfs = []
    bc_kwargs = {}
    for key,value in kwargs.items():
        if isinstance(value,str):
            try:
                udfs.append(_parse_udf_from_str(value))
            except ValueError:
                bc_kwargs[key] = float(value)
            except TypeError:
                bc_kwargs[key] = bool(value)
            except TypeError:
                    raise TypeError('cannot convert value: {} from column {} to float'.format(value,key))
        else:
            try:
                bc_kwargs[key] = float(value)
            except TypeError:
                bc_kwargs[key] = bool(value)
            except TypeError:
                    raise TypeError('cannot convert value: {} from column {} to float'.format(value,key))
    
    try:
        boundary_condition = cls(name,models,turbulence_model, **bc_kwargs)
    except TypeError:
        boundary_condition = cls(name,models,**bc_kwargs)
    
    for udf in udfs:
        boundary_condition.add_udf(udf)

    return boundary_condition

def make_boundary_condition_from_series(btype: str,
                                        name: str,
                                        boundary_dict: dict,
                                        bc_map: dict,
                                        turbulence_model: str,
                                        models: list):

    """"
    The treatment of a row representation of a boundary condition
    This is an entry function to parse based upon the type of boundary
    condition we are working with
    """

    bdict = {}
    for key,value in boundary_dict.items():
        bdict[bc_map[key]] = value
    
    mapping = {'pressure-outlet':PressureOutlet,
               'mass-flow-inlet':MassFlowInlet,
               'wall':WallBoundaryCondition,
               'velocity-inlet':VelocityInlet}
    
    return handle_udf_boundary_condition(mapping[btype],
                                         name,
                                         models,
                                         turbulence_model,
                                         **bdict)