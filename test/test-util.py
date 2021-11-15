import os
from wbfluentpy.io._util import _get_wb_parent_folder_from_path,_get_wb_from_fluent_folder_trn_out,_get_wb_files_from_design_point
import unittest
from dynaconf import Dynaconf
from wbfluentpy.fluentPyconfig import settings

"""

-- Creation -- 
Date: 05.27.2021
Author: Michael Lanahan

-- Last Edit -- 
Date: 06.01.2021
Editor: Michael Lanahan

-- Further Description --

check that the function of certain utility functions is correct

> Functions checked
_get_wb_parent_folder_from_path
_get_wb_from_fluent_folder_trn_out
_get_wb_files_from_design_point

"""

test_settings = Dynaconf(
    settings_files=['test_settings.toml'],
    environments = True,
)

class TestGetFluentParentFolder(unittest.TestCase):

    def test_detect(self):
        
        PATH = 'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF\\Fluent\\report-file-0.out'
        PARENT_PATH = 'Y:Michael\\fluentPy\\test\\test-files\\wb-folder-test'
        parent_folder =  _get_wb_parent_folder_from_path(PATH)
        self.assertEqual(os.path.normpath(parent_folder),os.path.normpath(PARENT_PATH))
        
    def test_find(self):
        
        PATH = 'Y:\\Michael\\fluentPy\\test\\'
        PARENT_PATH = 'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test'
        parent_folder = _get_wb_parent_folder_from_path(PATH)
        self.assertEqual(os.path.normpath(parent_folder),os.path.normpath(PARENT_PATH))

    def test_none(self):
        PATH = 'Y:\\Michael\\CO2\\Reproduce_Chen2017'
        parent_folder = _get_wb_parent_folder_from_path(PATH)
        self.assertIsNone(parent_folder)

class TestGetWBMapping(unittest.TestCase):

    def test_map(self):
        PATH = 'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\FFF'

        rfile_name = 'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF\Fluent\\report-file-0.out'
        sfile_name = 'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\progress_files\\dp0\\FFF\\Fluent\\Solution.trn'
        rfile,sfile = _get_wb_from_fluent_folder_trn_out(PATH)

        self.assertEqual(rfile,rfile_name)
        self.assertEqual(sfile,sfile_name)

class TestGetDPFolders(unittest.TestCase):

    dp_path = 'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0'
    def test_get(self):

        expected_solution = ['Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF\\Fluent\\report-file-0.out', 
                             'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF-12\\Fluent\\report-file-0.out', 
                             'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF-3\\Fluent\\report-file-0.out', 
                             'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF-6\\Fluent\\report-file-0.out', 
                             'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF-9\\Fluent\\report-file-0.out']
        expected_results =  ['Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\progress_files\\dp0\\FFF\\Fluent\\Solution.trn', 
                             'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\progress_files\\dp0\\FFF-12\\Fluent\\Solution.trn', 
                             'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\progress_files\\dp0\\FFF-3\\Fluent\\Solution.trn', 
                             'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\progress_files\\dp0\\FFF-6\\Fluent\\Solution.trn', 
                             'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\progress_files\\dp0\\FFF-9\\Fluent\\Solution.trn']
        expected_folders = ['Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF', 
                            'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF-12', 
                            'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF-3', 
                            'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF-6', 
                            'Y:\\Michael\\fluentPy\\test\\test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF-9']

        solfiles,rfiles,fluent_folders = _get_wb_files_from_design_point(self.dp_path,checkfolder = False)

        for test,expected in zip([solfiles,rfiles,fluent_folders],[expected_solution,expected_results,expected_folders]):
            self.assertEqual(test,expected)

if __name__ == '__main__':
    unittest.main()