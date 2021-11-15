#native imports
import dill
from abc import ABC,abstractstaticmethod
import os

#package imports
from .._msg import get_error_message
from ..link.link_exceptions import DataLinkException

__all__ = ['']

"""
Creation:
Author(s): Michael Lanahan 
Date: 06.08.2021 (ported over from different file)

Last Edit: 
Editor(s): Michael Lanahan
Date: 06.08.2021

-- Description -- 
Seperated from classes because it was starting to get a little lengthy. These are the base classes that the
classes module inherits, which contain the defining behavior of a DataModule and DataLink. The SerializableDataModule
class has the methods for writing the link and the module to a file, loading it from a file
"""

class SerializableDataModule(ABC):

    """
    SerializableDataModule

    Description
    ----------
    base class that can be serialized to a file, i.e. has a read and write method that writes (maybe?)
    all attributes to a file, and also reads them. It also needs to be extended

    Attributes
    ----------
    write_folder: basically the default write folder
    _EXT: extension of the file you're going to write

    Methods
    ----------
    Defined (and explained) below

    """
    _EXT = None

    def __init__(self,*args,**kwargs):
        self.__write_folder = None

    @property
    def write_folder(self):
        return self.__write_folder

    @write_folder.setter
    def write_folder(self,wf):
        self.__write_folder = wf
    
    def _get_write_file(self):
        """
        get the write folder
        """
        return os.path.join(self.write_folder,self._EXT)

    def _dict_representation(self):
        """
        return a dictionary representation of the class. 
        the representation written to a file. includes the class as well
        """
        d= {'class':self.__class__}
        for attr in self.__dict__:
            try:
                _,a = str(attr).split('__')
            except ValueError:
                a = str(attr)
            
            try:
                d[a] = self.__getattribute__(a)._dict_representation()
            except AttributeError:
                d[a] = self.__getattribute__(a)
        
        return d
    
    @abstractstaticmethod
    def _from_file_parser(dmdict):
        """
        gotta overwrite this so that you can interpret the information from the file 
        and re-instatiate the class
        """
        pass

    @classmethod
    def from_file(cls,file_name):
        """ 
        class method for creating from file 
        """
        dmdict = _class_method_file_loader(file_name,cls.__name__)
        return cls.from_dict(dmdict)

    @classmethod
    def from_dict(cls,dmdict):
        """ 
        re-instatiate from dictionary representation of the class. class-method
        """
        _construction_args = cls._from_file_parser(dmdict)
        return cls(*_construction_args)

    def serialize(self,file_name = None):
        """
        serialize the dictionary representation of the class to a file. can provide a file_name
        or maybe the class has a write_folder provided to write to 
        """
        if file_name is None:
            file_name = self._get_write_file()
        
        file_rep = self._dict_representation()
        _serialize_file_writer_dispatch(file_name,file_rep)
    
class DataModule(SerializableDataModule):
    
    """
    DataModule

    Description
    ----------
    base class for a datamodule. Described as a collection of filenames, a parser, and an id 
    to go along with it

    Attributes
    ----------
    files: files, list of strings
    dirs: dirs, list of strings
    identifier: the id/identifier of the data module
    file_paser: callable that parses the files


    Methods
    ----------
    Defined (and explained) below

    """

    _EXT = '.dm'

    def __init__(self,
                 fnames,
                 file_parser,
                 id,
                 *args,
                 htype = None,
                 **kwargs
                 ):

        self.__files = []
        self.__dirs = []
        super().__init__()
        
        self.sort_files(fnames)

        if not callable(file_parser):
            raise TypeError('file_parser must be callable')
        
        self.__file_parser = file_parser
        self.__identifier = id

    def sort_files(self,fnames):
        """
        sort supplied file names into directories and files, and also check if they exist
        make sure they are unique 
        """
        if not isinstance(fnames,list):
            fnames = [fnames]
        
        for fname in fnames: 
            if not os.path.exists(fname):
                raise ValueError('file does not exist')
            
            if os.path.isfile(fname):
                self.files.append(fname)
            elif os.path.isdir(fname):
                self.dirs.append(fname)
            else:
                raise ValueError('supplied name: {} does not appear to be a file or directory'.format(fname))
        
        self.files = list(set(self.files))
        self.dirs = list(set(self.dirs))

    def __call__(self):
        return self.file_parser(self.files,self.dirs)
    
    @property
    def files(self):
        return self.__files
    
    @property
    def dirs(self):
        return self.__dirs
    
    @property
    def identifier(self):
        return self.__identifier
    
    @property
    def file_parser(self):
        return self.__file_parser

    @files.setter
    def files(self,fs):
        self.__files = fs

    @dirs.setter
    def dirs(self,d):
        self.__dirs = d

    @identifier.setter
    def identifier(self,id):
        self.__identifier = id
    
    @file_parser.setter
    def file_parser(self,f_p):
        self.__file_parser = f_p

    @staticmethod
    def _from_file_parser(dmdict):
        return super()._from_file_parser()
 
class DataLink(SerializableDataModule):

    """
    DataLink

    Description
    ----------
    Base class for datalink. Defined as the combination of two datamodules, and a link_verifier (callable)
    that can verify the link between the two data modules. link_verifier must return True if the link is established,
    and False if not based on some condition

    Attributes
    ----------
    DataModule1: the first datamodule
    DataModule2: the second datamodule
    link_verifier: the callable that can verify the link between the two data moduless

    Methods
    ----------
    Defined (and explained) below

    """

    _EXT = '.dmlnk'
    def __init__(self,DataModule1,
                      DataModule2,
                      link_verifier,
                      *args,
                      **kwargs):

        super().__init__(*args,*kwargs)
        self.__DataModule1 = DataModule1
        self.__DataModule2 = DataModule2
        self.__link_verifier = link_verifier

    @property
    def DataModule1(self):
        return self.__DataModule1
    
    @property
    def DataModule2(self):
        return self.__DataModule2

    @property
    def linker_verifier(self):
        return self.__link_verifier
    
    @DataModule1.setter
    def DataModule1(self,dm1):
        self.__DataModule1  = dm1

    @DataModule2.setter
    def DataModule2(self,dm2):
        self.__DataModule2 = dm2
    
    @linker_verifier.setter
    def link_verifier(self,lnk_vfy):
        self.__link_verifier = lnk_vfy
    
    @staticmethod
    def _from_file_parser(dmdict):
        dm1_cls = dmdict['DataModule1']['class']
        dm2_cls = dmdict['DataModule2']['class']

        dm1 = dm1_cls.from_dict(dmdict['DataModule1'])
        dm2 = dm2_cls.from_dict(dmdict['DataModule2'])
        lnk_vfy = dmdict['link_verifier']

        _f = lnk_vfy(dm1(),dm2())
        if _f:
            return dm1,dm2,lnk_vfy
        else:
            msg = get_error_message('data_link_exception').format(dm1.identifier,dm2.identifier,lnk_vfy)
            raise DataLinkException(msg)

    @staticmethod 
    def link_decorator(link_verifier,*args,**kwargs):
        """
        have to decorate the link_verifier with any arguments or key-word arguments
        passed during the .link method call so that the link may be verified after 
        writing to a file
        """
        def linker(df1,df2):

            return link_verifier(df1,df2,*args,**kwargs)
        
        return linker
    
    def link(self,record_file = None,*args,**kwargs):
        """
        link function call that allows passing of additional arguments and keyword arguments 
        to the link_verifier callable. Then, write the whole thing to a file for later reading
        """
        self.link_verifier = self.link_decorator(self.link_verifier,*args,**kwargs)
        _f = self.link_verifier(self.DataModule1(),self.DataModule2())
        if _f:
            self.serialize(file_name = record_file)
        else:
            msg = get_error_message('data_link_exception').format(self.DataModule1.identifier,self.DataModule2.identifier,self.link_verifier)

def _class_method_file_loader(file_name,_name_):
        
        if isinstance(file_name,str):
            with open(file_name,'rb') as file:
                dmdict = dill.load(file)
        else:
            dmdict = dill.load(file_name)
    
        _cls = str(dmdict['class']).split('.')[-1][0:-2]
        if _cls != _name_:
            raise TypeError("{} does not contain a {} class".format(file_name,_cls))
        
        return dmdict
    
def _serialize_file_writer_dispatch(file_name,data):

    if isinstance(file_name,str):
        with open(file_name,'wb') as file:
            dill.dump(data,file)
    else:
        dill.dump(data,file_name)
