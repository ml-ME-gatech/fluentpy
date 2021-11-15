#native imports
import os
import re
from pathlib import WindowsPath
#package imports
from ..fluentPyconfig import settings as configsettings

DP_TAG = 'dp'
FF_TAG = 'FFF'
PROGESS_TAG = 'progress_files' 
REPORT_EXT = '.out'
SOLUTION_EXT = '.trn'

"""
Creation:
Author(s): Michael Lanahan 
Date: 06.09.2021

Last Edit: 
Editor(s): Michael Lanahan
Date: 06.11.2021

-- Description -- 
classes and methods for working with the folder structure of ANSYS workbench and ANSYS fluent
"""

""" 
filesys classes here for working with workbench folder structure
"""

class WorkBenchFolder(WindowsPath): 
    
    """ 
    WorkBenchFolder

    Description
    ----------
    the base work bench folder class, inherits from windows path

    Attributes
    ----------
    wb_root: the root directory of the work bench folder
    files_dir: the directory of the files folder
    progress_dir: the directory of the progress folder
    __name__: the name of the project

    Methods
    ----------
    Defined (and explained) below
    """
    
    def __init__(self,path):

        super().__init__()

        path = _path_clean_up(path)
        self.wb_root = _get_wb_parent_folder_from_path(path).replace(':',':\\')
        self.__files_dir = None
        self.__progress_dir = None
        self.__name__ = os.path.split(self.wb_root)[0]
    
    @property
    def wb_root(self):
        return self.__wb_root
    
    @wb_root.setter
    def wb_root(self,wbr):
        self.__wb_root = wbr

    @property
    def files_dir(self):
        if self.__files_dir is None:
            self._get_files_dir()
        
        return self.__files_dir

    @files_dir.setter
    def files_dir(self,fd):
        self.__files_dirs = fd
    
    @property
    def progress_dir(self):
        if self.__progress_dir is None:
            self._get_progress_dir()
        
        return self.__progress_dir
    
    @progress_dir.setter
    def progress_dir(self,pd):
        self.__progress_dir = pd
    
    def _get_files_dir(self):
        _,wbname = os.path.split(self.wb_root)
        self.__files_dir =  os.path.join(self.wb_root, wbname + '_files')

    def _get_progress_dir(self):
        self.__progress_dir = os.path.join(self.files_dir,PROGESS_TAG)

    def get_design_points(self,absolute = False):
        """
        get all of the design point folders in the work bench directory
        """

        _,wb_project_name = os.path.split(self.wb_root) 
        wb_files_folder = os.path.join(self.wb_root,wb_project_name + '_files')
        return _get_matching_tag(wb_files_folder,DP_TAG,DesignPointFolder,absolute= absolute)
        
class DesignPointFolder(WorkBenchFolder):

    """
    DesignPointFolder

    Description
    ----------
    the folder that contains the design points, inherits from WorkBenchFolder

    Attributes
    ----------
    dp_root: the root directory of the design point 
    dp_progress_root: the root directory of the design point in the progress branch
    __name__: the head, i.e. the folder name

    Methods
    ----------
    Defined (and explained) below
    """

    def __init__(self,path):

        path = _path_clean_up(path)
        super().__init__(path)
        self.dp_root,_ = _get_head_tail_by_head_name(path,DP_TAG,contained = True)
        self.__name__ = os.path.split(self.dp_root)[1]
        self.dp_progress_root = os.path.join(self.progress_dir,self.__name__)
        
    @property
    def dp_root(self):
        return self.__dp_root

    @dp_root.setter
    def dp_root(self,dpr):
        self.__dp_root = dpr

    @property
    def dp_progress_root(self):
        return self.__dp_progress_root

    @dp_progress_root.setter
    def dp_progress_root(self,pr):
        self.__dp_progress_root = pr

    def get_fluent_folders(self,absolute = False,strrep = False):
        """
        get a list of the fluent folders in the design point directory
        """

        lst =  _get_matching_tag(self.dp_root,FF_TAG,FluentFolder,absolute= absolute)
        if strrep:
            lst = [ff.ff_root for ff in lst]
        
        return lst

class FluentFolder(DesignPointFolder):
    """
    FluentFolder 

    Description
    ----------
    the folder that contains the fluent simulation, there are likely many in a design point

    Attributes
    ----------
    ff_root: the root directory of the fluent folder
    ff_progress_root: the root directroy of the fluent folder in the progress branch
    __name__: the head i.e. the folder name

    Methods
    ----------
    Defined (and explained) below
    """

    def __init__(self,path):

        path = _path_clean_up(path)

        super().__init__(path)

        if PROGESS_TAG in path:
            path = path.replace(PROGESS_TAG+'\\','')
        
        self.ff_root,_ = _get_head_tail_by_head_name(path,FF_TAG,contained = True)
        self.__name__ = os.path.split(self.ff_root)[1]
        self.ff_progress_root = os.path.join(self.dp_progress_root,self.__name__)

    @property
    def ff_root(self):
        return self.__ff_root
    
    @ff_root.setter
    def ff_root(self,ffr):
        self.__ff_root = ffr

    @property
    def ff_progress_root(self):
        return self.__ff_progress_root
    
    @ff_progress_root.setter
    def ff_progress_root(self,ffpr):
        self.__ff_progress_root = ffpr
    
    def get_report_files(self):      
        """
        get files from fluent folder root directory with the extension specified in REPORT_EXT
        """


        files = _get_all_files(self.ff_root,REPORT_EXT)
        return files
    
    def get_solution_files(self):
        """
        get files from fluent folder root directory with the extension specified in REPORT_EXT
        """
        files = _get_all_files(self.ff_progress_root,SOLUTION_EXT)
        return files


def _path_clean_up(path):

    """ 
    get path string into a consistent format - absolute and with normalized 
    slashes
    """

    if not os.path.isabs(path): 
        path = os.path.abspath(path)
    
    path = os.path.normpath(path)
    path = path.replace(':',':\\')

    return path

def _get_matching_tag(dir,tag,operator = None,absolute = False):

    _file_list = []
    for file in os.listdir(dir):
        if tag in file:
            if operator is not None:
                _file_list.append(operator(os.path.join(dir,file)))
            else:
                if absolute:
                    _file_list.append(os.path.join(dir,file))
                else:
                    _file_list.append(file)

    return _file_list

def _path_iter_trim(path,n):

    """
    iteratively trim a path n times
    """

    for i in range(n):
        path,_ = os.path.split(path)
    
    return path

def _get_head_tail_by_head_name(path,head, contained = True):
    
    """
    Trim a path until the requested head is found, and return the remaining head and tail
    """ 
    _path = os.path.normpath(path)
    delim = list(re.finditer(r"\\",_path))

    chunk = _path[delim[-1].end():]
    found = False
    for i in reversed(range(len(delim)-1)):
        if contained:
            if head in chunk:
                found = True
                break
        else:
            if chunk == head:
                found = True
                break
        chunk = _path[delim[i].end():delim[i+1].start()]
    
    if found:
        try:
            return os.path.join(_path[0:delim[i+1].start()],chunk),_path[delim[i+1].end():delim[i+2].start()]
        except IndexError:
            return os.path.join(_path[0:delim[i+1].start()],chunk),None
    else:
        return None, None

def _get_folders_that_contain_ext(path: str,    #path to results folder
                             tag: str,     #tag in the folders that denotes it may contain a result file
                             ext: str     #extension of the results file
                              ):

    """
    Description
    ----------
    Get folders that contain the extension specified in a parent directory

    Parameters
    ----------
    path: the path to the parent directory
    tag:  folder tag to narrow search, i.e. only search folders with this tag contained in the folder name
    ext:  file extensions

    Returns
    """
    folders = _get_folders(path,tag)
    rfiles = {}
    for folder in folders:
        filepath = _get_all_files(os.path.join(path,folder),ext)
        if filepath:
            rfiles[folder] = filepath

    return rfiles


def _get_fluent_folders(path: str,       
                        env = 'default', 
                        fmt = '',          
                        checkfolder = True,
                        ):
    
    """
    Description
    ----------
    higher level function that takes some fluent settings and 
    bakes them into the function _get_folders_that_contain_ext and 
    does some additional checks (in the default environment) to ensure 
    that the folders returned are indeed fluent folders

    Parameters
    ----------
    path: str or pathlike variable to be understood as a path by os module
    env: the environment to reference from settings.toml
    fmt: format of the extension file, a string
    checkfolder: check to make sure that the folder has the expected structure

    Returns
    ----------

    """
    envsettings = configsettings.from_env(env)
    fsettings = configsettings.from_env('fluent-default')
    files = _get_folders_that_contain_ext(path,fsettings['foldertag'],fmt)
    if envsettings.checkfolder and checkfolder:
        kfiles = dict()
        for file in files:
            try:
                fpath = os.path.join(path,str(file))
                fs = FolderStructure.from_settings(fpath,fsettings)
                fs.validateExpectedStructure()
                kfiles[file] = files[file]
            except AttributeError:
                pass
    else:
        kfiles = files

    return list(kfiles.keys())



def _get_all_files(folder: str, #folder within to start search
                   ext:str     #extensions to consider
                   ): 

    """
    Description
    ----------
    get all files within a folder, even if there are subfolders, and return the full path
    can specify an extension of the file to exclude other files
    """

    fileNames = []
    walk = os.walk(folder)
    for (path,directories,files) in walk:
        for f in files:
            _,fext = os.path.splitext(f)
            if ext == fext or ext == fext[1:] or ext == '':
                fileNames += [os.path.join(path,f)]

    if not fileNames:
        return [None]

    return fileNames

def _get_folders(path: str,  
                 tag: str,
                 ):

    if tag == '':
        return os.listdir(path)
    
    else:
        vresult = []
        for folder in os.listdir(path):
            if tag in folder:
                vresult += [folder]
        
        return vresult


def _get_wb_parent_folder_from_path(path):

    """
    Parameters
    ----------
    path: string or path-like such that the os module may understand it as such

    Returns
    ----------
    parent_folder: the parent folder of the workbench folder if identified, None if
    no folder is found

    Relies upon the fact that workbench will not load unless you have the folder structure
    present:

    parent_directory\\
        parent_directory_files\\
    
    Examples
    ----------
    (1)
    PATH = 'D:\\TopFolder\\Simulations\\SpecificSimulation\\SpecificSimulation_files\\dp0
    parent_folder = _get_wb_parent_folder_from_path(PATH)
    "D:\\TopFolder\\Simulations\\SpecificSimulation"

    (2)
    PATH = D:\\TopFolder\\Simulations\\SpecificSimulation
    parent_folder = _get_wb_parent_folder_from_path(PATH)
    "D:\\TopFolder\\Simulations\\SpecificSimulation"
    """

    isdir = os.path.isdir(path)
    isfile = os.path.exists(path)

    if not isdir and not isfile:
        raise FileNotFoundError('Path doesnt appear to lead to a folder or file')

    def __detect_repeated_string():
        
        _path =os.path.normpath(path)
        parts = _path.split(os.sep)
        for i in range(len(parts)-1):
            if parts[i] + '_files' == parts[i+1]:
                return os.path.join(*parts[0:i+1])
        
        return None

    def __find_repeated_string(starting_path):

        _path =os.path.normpath(starting_path)
        parts = [ p + '_files' for p in _path.split(os.sep)]
        walk = os.walk(starting_path)
        
        for (path,directories,files) in walk:
            if not directories:
                return None 
            else:
                for dir in directories:
                    if dir in parts:
                        return _path

                for dir in directories:
                    parent_folder = __find_repeated_string(os.path.join(starting_path,dir))
                    if parent_folder is not None:
                        return parent_folder
                
                return None

    parent_folder = __detect_repeated_string()
    if parent_folder == None:
        return __find_repeated_string(path)

    else:
        return parent_folder

def _resolve_fluent_file_path(folders,
                              pad,
                              ext):

    _folders = []
    for folder in folders:
        path = os.path.join(folder,pad)
        files = os.listdir(path)
        for f in files:
            _,cext = os.path.split(ext)
            if ext == cext:
                _folders.append(os.path.join(path,f))
    
    return _folders


def _get_wb_files_from_design_point(dp_folder,checkfolder = True):

    _dpfolder = os.path.abspath(os.path.normpath(dp_folder).strip('/').strip('\\'))
    fluent_folders = _get_fluent_folders(_dpfolder,checkfolder = checkfolder)
    rfiles = []
    sfiles = []
    ffolders = []
    for folder in fluent_folders:
        ffolders.append(os.path.join(_dpfolder,folder))
        r,s = _get_wb_from_fluent_folder_trn_out(os.path.join(_dpfolder,folder))
        rfiles.append(r)
        sfiles.append(s)
    
    return rfiles,sfiles,ffolders

def _get_wb_from_fluent_folder_trn_out(folder):

    folder = os.path.normpath(folder).strip('/').strip('\\')
    fluent_settings = configsettings.from_env('fluent-default')
    
    def _check_ext_in_dir(dir,ext):
        for f in os.listdir(dir):
            _,t_ext = os.path.splitext(f)
            if ext == t_ext:
                return True,f
        
        return False, None

    #parse to get the structure of the folder, look for the fluent folder
    #and the design point folder
    if fluent_settings['foldertag'] in folder:
        _fluent_folder,_ = _get_head_tail_by_head_name(folder,fluent_settings['foldertag'],contained = True)
        _,fluent_folder = os.path.split(_fluent_folder)
        _design_point_name,_ = _get_head_tail_by_head_name(_fluent_folder,'dp',contained = True)
        _,design_point_name = os.path.split(_design_point_name)
    else:
        raise ValueError('Could not find a fluent folder with tag: {} in provided path: {}'.format(fluent_settings['foldertag'],folder))
    
    #parse to get the workbench project folder
    try:
        wb_project = _get_wb_parent_folder_from_path(folder)
        name = os.path.split(wb_project)[1] + '_files'
    except TypeError:
        raise FileNotFoundError("The folder structure does not appear to be that of a work bench project")
    
    #make the solution folder
    solution_folder = os.path.join(wb_project,name,fluent_settings['progress_file_folder'],
                                   design_point_name,fluent_folder,fluent_settings['fluent_files_folder'])
    
    #norm the solution folder and get the file
    solution_folder = solution_folder.replace(':',':\\')
    _flag, sfile = _check_ext_in_dir(solution_folder,fluent_settings['solution_file_ext'])

    if not _flag:
        raise ValueError('{} file not found in progress files fluent folder, cannot get wb file paths'.format(fluent_settings['solution_file_ext']))

    #make the report file folder
    report_folder = os.path.join(wb_project,name,design_point_name,fluent_folder,
                                 fluent_settings['fluent_files_folder'])
    
    report_folder = report_folder.replace(':',':\\')
    _flag,rfile = _check_ext_in_dir(report_folder,fluent_settings['report_file_ext'])
    if not _flag:
        raise ValueError('{} file not found in design point files fluent folder, cannot get wb file paths'.format(fluent_settings['report_file_ext']))
    


    return os.path.join(report_folder,rfile),os.path.join(solution_folder,sfile)
    
class FolderStructure:

    def __init__(self,path: str,
                      dirs: str,
                      files: str
                ):

        if not os.path.exists(path) or not os.path.isdir(path):
            raise FileExistsError('supplied path does not exist or is not a directory')
        
        self.__path = path
        self.__dirs = self.parseinput(dirs,'directory')
        self.__files = self.parseinput(files,'files')

    @property
    def path(self):
        return self.__path

    @property
    def files(self):
        return self.__files

    @property
    def dirs(self):
        return self.__dirs

    @path.setter
    def path(self,p):
        self.__path = p
    
    @files.setter
    def files(self,f):
        self.__files = f
    
    @dirs.setter
    def dirs(self,d):
        self.__dirs = d
    
    #parse inputs into the properties
    def parseinput(self,arg,string):
        msg1 = '{} must be specified as strings or list of strings'
        msg2 = '{} list must contain only strings'
        if isinstance(arg,str):
            return [arg]
        elif isinstance(arg,list):
            for a in arg:
                if not isinstance(a,str):
                    raise TypeError(msg2.format(string))
            
            return arg
        else:
            raise TypeError(msg1.format(string))
        
    #build folderStructure from a settings object
    @classmethod
    def from_settings(cls,
                      path: str,        #string path
                      settings          #settings object from dynaconf
                      ):
        
        return cls(path,settings['dirs'],settings['files'])


    def validate_expected_structure(self, walk =None):

        if walk is None:
            walk = os.walk(self.path)
        
        dir_track = dict.fromkeys(self.dirs)
        file_track = dict.fromkeys(self.files)

        for parent,dirnames,filenames in walk:
            dirname = os.path.split(parent)[1]
            if dirname in dir_track:
                dir_track[dirname] = True
            for f in filenames:
                _,ext = os.path.splitext(f)
                if ext in file_track:
                    file_track[ext] = True

        flag = True
        for d,b in dir_track.items():
            if not b:
                raise AttributeError('Could not find directory: {} at path: \n{}'.format(d,self.path))
                break
        
        for f,b in file_track.items():
            if not b:
                raise AttributeError('Could not find file: {} at path: \n{}'.format(f,self.path))


def main():
    pass

if __name__ == '__main__':
    main()