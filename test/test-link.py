#native imports
import os
import unittest
import pandas as pd
import numpy as np
import pickle

#package imports
from wbfluentpy.link.classes import ReportFileModule,DefaultFluentFolderModule,ExcelFileModule,DesignPointModule,DefaultFluentFolderLink
from wbfluentpy.link.linker_utils import zero_norm_linker_dict,zero_diff_link_verification,zero_percent_diff_link_verification
from wbfluentpy.io.filesystem import FluentFolder,DesignPointFolder

#other package imports
from hemjpy.io.legacy import getCaseData

"""
-- Creation -- 
Date: 05.31.2021
Author: Michael Lanahan

-- Last Edit -- 
Date: 06.07.2021
Editor: Michael Lanahan

-- Further Description --
Testing data link files

> Classes Checked
- ReportFileModule
- DefaultFluentFolderModule
- ExcelFileModule
- DesignPointModule 
- DefaultFluentFolderLink
"""

DIFF_TOL = 1e-10

class TestReportFileModule(unittest.TestCase):

    test_fname = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF\\Fluent\\report-file-0.out'
    check_rfm_df = 'test-files\\check\\check_df_report_file_module_parse.pkl'
    serialized_rfm_file = 'test-files\\check\\serialized_df_module.dm'

    def test_incorrect_construction(self):
        
        string = self.test_fname.replace('out','none') 
        with self.assertRaises(TypeError):   
            rfm = ReportFileModule(string,'FFF')
    
    def test_correct_constructer(self):

        rfm = ReportFileModule(self.test_fname,'FFF')
        self.assertEqual(rfm.files[0],self.test_fname)

    def test_data_frame_parse(self):

        rfm = ReportFileModule(self.test_fname,'FFF')
        df = rfm()
        check = pd.read_pickle(self.check_rfm_df)
        self.assertLess(np.linalg.norm(df-check),DIFF_TOL)

    def test_serialize_rmf(self):
        rfm = ReportFileModule(self.test_fname,'FFF')
        rfm.serialize(self.serialized_rfm_file)
        rfm_check = ReportFileModule.from_file(self.serialized_rfm_file)

        self.assertEqual(rfm.identifier,rfm_check.identifier)
        self.assertEqual(rfm.dirs,rfm_check.dirs)
        self.assertEqual(rfm.files,rfm_check.files)

class TestFluentFolderModule(unittest.TestCase):

    test_folder = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF'
    file_check_list = ['test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF\\Fluent\\report-file-0.out',
     'test-files\\wb-folder-test\\wb-folder-test_files\\progress_files\\dp0\\FFF\\Fluent\\Solution.trn']
    dir_check_list = ['test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF']
    data_frame_check = 'test-files\\check\\check_df_fluent_folder_module_parse.pkl'
    serialized_ffm_file = 'test-files\\check\\check_seralize_ffm.pkl'
    
    def test_correct_constructer(self):
        self.file_check_list = [os.path.abspath(f) for f in self.file_check_list]
        self.dir_check_list = [os.path.abspath(d) for d in self.dir_check_list]

        ffm = DefaultFluentFolderModule(self.test_folder)
        for test,check in zip([ffm.files,ffm.dirs],[self.file_check_list,self.dir_check_list]):
            for file in check:
                self.assertIn(file,test)
            
            for file in test:
                self.assertIn(file,check)

    def test_data_frame_parser(self):
        ffm = DefaultFluentFolderModule(self.test_folder)
        data = ffm()
        check = pd.read_pickle(self.data_frame_check)
        self.assertLess(np.linalg.norm(data-check),DIFF_TOL)

    def test_serialize_ffm(self):

        ffm = DefaultFluentFolderModule(self.test_folder)
        ffm.serialize(self.serialized_ffm_file)

        ffm_check = DefaultFluentFolderModule.from_file(self.serialized_ffm_file)
        
        self.assertEqual(ffm.identifier,ffm_check.identifier)
        self.assertEqual(ffm.dirs,ffm_check.dirs)
        self.assertEqual(ffm.files,ffm_check.files)

class TestExcelFileModule(unittest.TestCase):

    excel_file_path = 'Y:\\Michael\\hemjpy\\data\\legacy.xlsx'
    excel_file_check_df = 'test-files\\check\\check_excel_file_module_df.pkl'
    serialized_efm_file = 'test-files\\check\\serialized_efm_files.dm'

    @property
    def excel_parser(self):

        def excel_parser(*args):

            return getCaseData('MatLabOutputs')
        
        return excel_parser

    def test_correct_constructer(self):
        efm = ExcelFileModule(self.excel_file_path,self.excel_parser)
        self.assertEqual(efm.files[0],self.excel_file_path)

    def test_data_frame_parser(self):
        efm = ExcelFileModule(self.excel_file_path,self.excel_parser)
        data = efm().fillna(value = 0)
        check = pd.read_pickle(self.excel_file_check_df)
        self.assertLess(np.linalg.norm(data-check),DIFF_TOL)

    def test_serialize_efm(self):
        efm = ExcelFileModule(self.excel_file_path,self.excel_parser)
        efm.serialize(self.serialized_efm_file)

        efm_check = ExcelFileModule.from_file(self.serialized_efm_file)

        self.assertEqual(efm.identifier,efm_check.identifier)
        self.assertEqual(efm.dirs,efm_check.dirs)
        self.assertEqual(efm.files,efm_check.files)

class TestDesignPointModule(unittest.TestCase):

    DP_PATH = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0'
    check_file_path = 'test-files\\check'
    file_list_check_file = 'test_dpmodule_file.pkl'
    dir_list_check_file = 'test_dp_module_dir.pkl'
    df_check_file = 'test_dpm_df.pkl'
    serialized_dpm_file = 'test_serialize_dpm.dm'

    def test_correct_constructer(self):
        dpm = DesignPointModule(self.DP_PATH)
        with open(os.path.join(self.check_file_path,self.file_list_check_file),'rb') as file:
            files = pickle.load(file)
            
        with open(os.path.join(self.check_file_path,self.dir_list_check_file),'rb') as file:
            dirs = pickle.load(file)
        
        dirs = [os.path.abspath(d) for d in dirs]

        for group in dpm.files:
            self.assertEqual(dpm.files[group],files[group])
        
        self.assertEqual(dpm.dirs,dirs)
    
    def test_data_frame_parser(self):

        dpm = DesignPointModule(self.DP_PATH)
        df = dpm()
        check = pd.read_pickle(os.path.join(self.check_file_path,self.df_check_file))
        self.assertLess(np.linalg.norm(df-check),DIFF_TOL)
    
    def test_serialize_dfm(self):
        dpm = DesignPointModule(self.DP_PATH)
        dpm.serialize(os.path.join(self.check_file_path,self.serialized_dpm_file))

        dpm_check = DesignPointModule.from_file(os.path.join(self.check_file_path,self.serialized_dpm_file))

        self.assertEqual(dpm.identifier,dpm_check.identifier)
        
        self.assertEqual(dpm.dirs,dpm_check.dirs)
        self.assertEqual(dpm.files,dpm_check.files)

        df = dpm()
        df_check = dpm_check()

        self.assertLess(np.linalg.norm(df-df_check),DIFF_TOL)

class TestFluentFolderLink(unittest.TestCase):

    test_folder = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF-3\\'
    excel_file_path = 'Y:\\Michael\\hemjpy\\data\\legacy.xlsx'

    
    
    def excel_row_getter(self,row):

        def excel_parser(*args):

            data = getCaseData('SimParams',filter_units = True)
            return data.loc[row,:]

        return excel_parser

    def test_link_verifier(self):

        ffm = DefaultFluentFolderModule(self.test_folder)
        excel_func = self.excel_row_getter(425)
        efm = ExcelFileModule(self.excel_file_path,excel_func)

        fdat = ffm()
        edat = efm()

        self.assertTrue(zero_percent_diff_link_verification(fdat,edat,
        ignore_columns= ['Omega-out','Omega-in']))
    
    def test_link_creation(self):

        excel_func = self.excel_row_getter(425)
        efm = ExcelFileModule(self.excel_file_path,excel_func)
        ffm = DefaultFluentFolderModule(self.test_folder)
        
        
        link = DefaultFluentFolderLink(ffm,efm)
        link.link(ignore_columns = ['Omega-out','Omega-in'])
        self.assertTrue(os.path.isfile(os.path.join(self.test_folder,'.fpplnk')))


    def test_link_read_and_verify(self):
        
        excel_func = self.excel_row_getter(425)
        efm = ExcelFileModule(self.excel_file_path,excel_func)
        ffm = DefaultFluentFolderModule(self.test_folder)
        
        link = DefaultFluentFolderLink(ffm,efm)
        link.link(ignore_columns = ['Omega-out','Omega-in'])

        rlink = DefaultFluentFolderLink.from_file(os.path.join(self.test_folder,'.dmlnk'))

  

def main():
    unittest.main()

if __name__ == '__main__':
    main()