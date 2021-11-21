#native imports
import dill
from abc import ABC,abstractstaticmethod
import os

#package imports
from .._msg import get_error_message

__all__ = ['']

"""
Creation:
Author(s): Michael Lanahan 
Date: 06.08.2021 (ported over from different file)

Last Edit: 
Editor(s): Michael Lanahan
Date: 11.21.2021

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
