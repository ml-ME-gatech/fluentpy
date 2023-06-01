#native imports
from multiprocessing.sharedctypes import Value
from pandas import DataFrame,Series
from typing import List, Type
import numpy as np 
#package imports
from ..tui import UDF, KEpsilonRNGModelConstants, PressureOutlet, MassFlowInlet,\
                  WallBoundaryCondition, VelocityInlet, FluentBoundaryCondition,\
                  KEpsilonModelConstants, KOmegaModelConstants,GEKOModelConstants,\
                  FluidMaterialModification, KOmega_SSTModelConstants, NoTurbulenceModel,\
                  KEpsilonRNGModelConstants, KOmega_BSLModelConstants,KOmegaLowReCorrection

""""
Author: Michael Lanahan
Date Created: 08.06.2021
Last Edit: 01.05.2021

utility functions and classes for working with Fluent Batch Files
and pace utility formatting
"""

MODELS = [  'ke-realizable',
            'ke-rng',
            'ke-standard',
            'kw-bsl',
            'kw-sst',
            'kw-geko',
            'geko',
            'kw-standard',
            'k-kl-w',
            'reynolds-stress-model',
            'laminar']

ALLOWABLE_BOUNDARY_TYPES = ['mass-flow-inlet','pressure-outlet','wall',
                            'velocity-inlet','model modification','fluid-modification']

FLUID_BOUNDARY_CONDITIIONS = ['mass-flow-inlet','pressure-outlet']

def split_header_name(string: str,
                        delim = ':') -> tuple:
    """
    expects a boundary condition/model modification
    input in the format
    
    name:input:type 

    or model modification in the form:

    model:input
    """ 
    return list((s.strip() for s in string.split(delim)))

def sort_boundary_list(blist: list,
                       delim = ':') -> dict:

    """
    essentially develops a "log" of boundary conditions that is a dictionary
    the keys of the dictionary are the names:type and the values of the dictionary
    are lists of the variables for that particular boundary condition
    """

    log = {}
    for item in blist:
        split_header = split_header_name(item)

        if len(split_header) == 3:
            name,variable,btype = split_header
        elif len(split_header) == 2:
            name,variable = split_header
            btype = 'model modification'
        
        try:
            if btype not in ALLOWABLE_BOUNDARY_TYPES:
                raise TypeError('boundary condition type specified by: {} is not allowed'.format(btype))
        except UnboundLocalError as ule:
            raise ValueError('improper columns specification:"{}" - leading to: {}'.format(item,str(ule)))
        
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
        
        if _name[1] == 'model modification':
            cols = [_name[0]  + delim + c for c in svars]
        else:
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
        
        if 'turbulent_dissipation_rate' in column:
            models.append('ke-standard')
        
        if 'specific_dissipation_rate' in column:
            models.append('kw-standard')
    
    return list(set(models))


def _parse_udf_from_str(string : str) -> UDF:
    """
    Parameters
    ----------
    string : str
            the string that could specify a udf.
            expects the specification of a UDF as a string
            from a table to have the following format: 

            <file_name> or <file_name#compile = True>

            OR

            <data_name>

            the first option allows for compilation of the UDF during runtime.
            the second option must be specified as <variable_name::lib_name>.
            The file name can be an absolute or relative path to the file

    Examples
    --------
    these examples would produce a valid UDF object in python.
    1. <udf/src/my_custom_profile.c>
    2. <udf/src/my_custom_profile.c#compile = False>
    3. <udf/src/my_custom_profile.c#compile = True>
    4. <x_velocity::libudf>
    """

    string = string.strip()
    
    if string[0] == '<' and string[-1] == '>':
        string = string[1:-1].strip()

        if '::' in string:
            return UDF(data_name= string)
        else:
            split_tuple = string.split('#')
            if len(split_tuple) == 1:
                return UDF(file_name = split_tuple[0])
            else:
                compile = split_tuple[1].split('=')[1].strip().lower().capitalize()
                if compile == 'True':
                    return UDF(file_name = split_tuple[0].strip(),
                               compile = True)
                else:
                    return UDF(file_name = split_tuple[0].strip(),
                               compile = False)

    else:
        raise ValueError('string does not specify a UDF')

def handle_udf_boundary_condition(cls: FluentBoundaryCondition,
                                  name: str,
                                  models: List[str],
                                  turbulence_model: str,
                                   **kwargs
                                    ) -> FluentBoundaryCondition:
        
    udfs = {}
    bc_kwargs = {}
    for key,value in kwargs.items():
        if isinstance(value,str):
            try:
                udfs[key] = _parse_udf_from_str(value)
            except ValueError:
                bc_kwargs[key] = float(value)
            except TypeError:
                try:
                    bc_kwargs[key] = bool(value)
                except TypeError:
                    raise TypeError('cannot convert value: {} from column {} to float'.format(value,key))
        elif isinstance(value,list):
            bc_kwargs[key] = value
        else:
            try:
                bc_kwargs[key] = float(value)
            except TypeError:
                try:
                    bc_kwargs[key] = bool(value)
                except TypeError:
                    raise TypeError('cannot convert value: {} from column {} to float'.format(value,key))
    
    try:
        boundary_condition = cls(name,models,turbulence_model, **bc_kwargs)
    except TypeError:
        boundary_condition = cls(name,models,**bc_kwargs)
    
    for attr,udf in udfs.items():
        boundary_condition.__setattr__(attr,udf)

    return boundary_condition

def handle_model_modification(cls: object,
                              **kwargs) -> object:
    
    return cls(**kwargs)

def handle_fluid_modification(cls: object,
                              name: str,**kwargs) -> object:

    return cls(name,**kwargs)

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
               'velocity-inlet':VelocityInlet,
               'ke-standard':KEpsilonModelConstants,
               'kw-standard':KOmegaModelConstants,
               'ke-realizable':KEpsilonModelConstants,
               'ke-rng': KEpsilonRNGModelConstants,
               'kw-SST': KOmega_SSTModelConstants,
               'kw-sst': KOmega_SSTModelConstants,
               'kw-BSL': KOmega_BSLModelConstants,
               'kw-bsl': KOmega_BSLModelConstants,
               'kw-low-re': KOmegaLowReCorrection,
               'kw-geko':GEKOModelConstants,
               'geko':GEKOModelConstants,
               'fluid-modification':FluidMaterialModification,
               'laminar': NoTurbulenceModel}
    
    if btype != 'model modification' and btype != 'fluid-modification':
        return handle_udf_boundary_condition(mapping[btype],
                                         name,
                                         models,
                                         turbulence_model,
                                         **bdict)
    elif btype == 'model modification':
        return handle_model_modification(mapping[name], **bdict)
    
    elif btype == 'fluid-modification':
        return handle_fluid_modification(mapping[btype],name,**bdict)