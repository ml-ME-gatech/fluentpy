import os
from wbfluentpy.io._util import _get_fluent_folders, FolderStructure
import unittest
from dynaconf import Dynaconf
from wbfluentpy.fluentPyconfig import settings

"""

-- Creation -- 
Date: 05.19.2021
Author: Michael Lanahan

-- Last Edit -- 
Date: 05.20.2021
Editor: Michael Lanahan

-- Further Description --

checking to make sure that various safety features perform as expected such as
checking folder structure

> Functions checked
- getFluentFolders

> Classes checked
- FolderStructure
"""

test_settings = Dynaconf(
    settings_files=['test_settings.toml'],
    environments = True,
)

PATH = 'D:\\Michael\\Fluent\\HEMJ_60d-SKE\\HEMJ-60deg-SKE_files\\dp0\\FFF'
class TestFileCheck(unittest.TestCase):
    
    dirs = ['DM','Fluent','Post']
    ext = ['.cst','.set','.xml']
    
    def test_correct_default_constructer(self):
        
        #check the default constructure
        fs = FolderStructure(PATH,self.dirs,self.ext)
        self.assertEqual(fs.dirs,self.dirs)
        self.assertEqual(fs.files,self.ext)

        #These cases should not work
        with self.assertRaises(TypeError):
            FolderStructure(PATH,1,self.ext)
        
        with self.assertRaises(TypeError):
            FolderStructure(PATH,self.dirs,1)
        
        with self.assertRaises(TypeError):
            FolderStructure(PATH,[1,'hello'],self.ext)
        
        with self.assertRaises(TypeError):
            FolderStructure(PATH,self.dirs,[1,'this','is',5.0])
    
    def test_class_constructer(self):

        #check the class constructer

        foldersettings = test_settings.from_env('fluentfolder')
        fs = FolderStructure.from_settings(PATH,foldersettings)
        self.assertEqual(fs.dirs,foldersettings['dirs'])
        self.assertEqual(fs.files,foldersettings['files'])

    def test_structure_validation_method(self):

        #this should work
        fs = FolderStructure(PATH,self.dirs,self.ext)
        fs.validate_expected_structure()

        #this should not work
        with self.assertRaises(AttributeError):
            fs = FolderStructure(PATH,self.dirs,self.ext + ['.nonsense'])
            fs.validate_expected_structure()
        
        #this should not work
        with self.assertRaises(AttributeError):
            fs = FolderStructure(PATH,self.dirs + ['none'],self.ext)
            fs.validate_expected_structure()

if __name__ == '__main__':
    unittest.main()
