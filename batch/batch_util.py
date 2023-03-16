import os

def _parse_pykwargs(default_script,
                    **pykwargs):

    if 'script_name' not in pykwargs:
        pykwargs['script_name'] = default_script
    
    if pykwargs['script_name'] == default_script:
        path,_ = os.path.split(os.path.split(__file__)[0])
        folder = os.path.join(path)
        pace_lib = os.path.join(folder,'pace.py')

        if 'python_libs' not in pykwargs:
            pykwargs['python_libs'] = [pace_lib]
        else:
            if pace_lib not in pykwargs['python_libs']:
                pykwargs['python_libs'].append(pace_lib)

    return pykwargs