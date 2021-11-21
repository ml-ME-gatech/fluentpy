#native imports
import os
import pandas as pd
import numpy as np
import unittest
from dynaconf import Dynaconf
import pickle

#pacakge imports
from wbfluentpy.io.classes import ReportFileOut,SolutionFile,ReportFilesOut,SolutionFiles,PostDataFile,XYDataFile
#from fluentPy.fluentPyconfig import settings

"""
-- Creation -- 
Date: 05.25.2021
Author: Michael Lanahan

-- Last Edit -- 
Date: 11.21.2021
Editor: Michael Lanahan

-- Further Description --

Rigorously checking the function of the workhorse classes

> Classes Checked
- ReportFileOut
- SolutionFile
- ReportFilesOut
- SolutionFiles

"""

DIFF_TOL = 1e-10

test_settings = Dynaconf(
    settings_files=['test_settings.toml'],
    environments = True,
)


class ReportFileTests(unittest.TestCase):

    test_file_name = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF\\Fluent\\report-file-0.out'
    check_frame_name = 'test-files\\check\\report-file-0-df.pkl'
    check_converged_name = 'test-files\\check\\report-file-0-converged.pkl'
    check_skip_rows = 'test-files\\check\\report-file-0-skip.pkl'
    rfile_len = 824

    def test_report_file_len(self):

        with ReportFileOut(self.test_file_name) as rfile:                             
            self.assertEqual(len(rfile),self.rfile_len)                             #check if length is equal to expected
    
    def test_readdf_full(self):
        
        with ReportFileOut(self.test_file_name) as rfile:
            rfile.readdf()                                                          #parse data
            check_rfile = pd.read_pickle(self.check_frame_name)                     #read expected data from checks folder
            self.assertLess(np.linalg.norm(check_rfile-rfile.df),DIFF_TOL)          #check if similar to within tolerance

    def test_readdf_converged(self):

        with ReportFileOut(self.test_file_name) as rfile:
            data = rfile.readdf(skiprows = 'converged')
            compare_rfile = pd.read_pickle(self.check_converged_name)
            self.assertLess(np.linalg.norm(compare_rfile-data),DIFF_TOL)

    def test_readdf_skiprows(self):

        with ReportFileOut(self.test_file_name) as rfile:
            rfile.readdf(skiprows = 210)
            check_skip = pd.read_pickle(self.check_skip_rows)
            self.assertLess(np.linalg.norm(check_skip-rfile.df),DIFF_TOL)


class SolutionFileTests(unittest.TestCase):

    solution_file = 'test-files\\wb-folder-test\\wb-folder-test_files\\progress_files\\dp0\\FFF\\Fluent\\Solution.trn'
    solution_file2 = 'test-files\\wb-folder-test2\\wb-folder-test2_files\\progress_files\\dp0\\FFF\\Fluent\\Solution-2.trn'
    solution_check_file = 'test-files\\check\\solution-check.pkl'

        
    def test_readdf_exist(self):
        
        with SolutionFile(self.solution_file) as sfile:
            sfile.readdf()
            check_solution_file = pd.read_pickle(self.solution_check_file)

        print(sfile.df)
        self.assertLess(np.linalg.norm(np.array(check_solution_file,dtype = float)-np.array(sfile.df,dtype = float)),DIFF_TOL)


"""
class ReportFilesTests(unittest.TestCase):

    dp_folder = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0'
    columns_check_file = 'test-files\\check\\dp_load_columns.txt'
    df_check_file = 'test-files\\check\\dp_load_df-{}.pkl'
    df_arb_check_file = 'test-files\\check\\dp_load_arbitary_df-{}.pkl'
    df_variable_check = 'test-files\\check\\variable_loading.pkl'

    def test_report_files_dict(self):

        dpf = DesignPointFolder(self.dp_folder)    
        files = [f.get_report_files()[0] for f in dpf.get_fluent_folders()]
        rfiles = ReportFilesOut(files)
        for rfile,fname in zip(rfiles,files):
            self.assertIn(fname,str(rfile))
            self.assertIsInstance(rfile,ReportFileOut)
    

    def test_load_converged(self):
        
        
        #check that the loading of the result files works correctly when the converged result 
        #is requested
        

        dpf = DesignPointFolder(self.dp_folder)    
        files = [f.get_report_files()[0] for f in dpf.get_fluent_folders()]
        rfiles = ReportFilesOut(files)
        rfiles.load(convergedResult= True)
        
        #check column reading
        with open(self.columns_check_file,'r') as file:
            for line in file.readlines():
                self.assertIn(line[0:-1],rfiles.columns)
        
        #check data frames
        for i,df in enumerate(rfiles.data.values()):
            check = pd.read_pickle(self.df_check_file.format(str(i)))
            self.assertLess(np.linalg.norm(check-df),DIFF_TOL)

    def test_load_arbitrary(self):

       
       # #check that the loading of thee result files works correctly with arbitary number of rows 
       # #ignored
       

        dpf = DesignPointFolder(self.dp_folder)    
        files = [f.get_report_files()[0] for f in dpf.get_fluent_folders()]
        rfiles = ReportFilesOut(files)

        skiprows = dict.fromkeys(files)
        for i,key in enumerate(skiprows):
            skiprows[key] = i
        
        rfiles.load(skiprows = skiprows)

        for i,df in enumerate(rfiles.data):
            check = pd.read_pickle(self.df_arb_check_file.format(str(i)))
            self.assertLess(np.linalg.norm(check-rfiles.data[df]),DIFF_TOL)

    
    def test_variable_df_get(self):
    
        #check that the retrieval of a variable from multiple results files works as expected

        dpf = DesignPointFolder(self.dp_folder)    
        files = [f.get_report_files()[0] for f in dpf.get_fluent_folders()]
        rfiles = ReportFilesOut(files)

        df = rfiles.get_variable('cs-temp')
        check = pd.read_pickle(self.df_variable_check)
        
        self.assertLess(np.linalg.norm(check.fillna(value = 0)-df.fillna(value =0)),DIFF_TOL)


class SolutionFilesTests(unittest.TestCase):

    progress_files_folders = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0'
    check_param_file = 'test-files\\check\\solution_files_params_check-{}.pkl'
    check_df_files = 'test-files\\check\\solution_files_df_check-{}.pkl'
    difficult_solution_file = 'test-files\\test\\difficult_solution.trn'

    def test_read_params(self):
        dpf = DesignPointFolder(self.progress_files_folders)    
        files = [f.get_solution_files()[0] for f in dpf.get_fluent_folders()]
        sfiles = SolutionFiles(files)

        sfiles.read_params()
        for i,(ff,df) in enumerate(sfiles.input_parameters.items()):
            df.to_pickle(self.check_param_file.format(i))
            check = pd.read_pickle(self.check_param_file.format(i))
            self.assertLess(np.linalg.norm(df - check),DIFF_TOL)

    def test_load(self):

        dpf = DesignPointFolder(self.progress_files_folders)    
        files = [f.get_solution_files()[0] for f in dpf.get_fluent_folders()]
        sfiles = SolutionFiles(files)
        sfiles.load()
        for i,(ff,df) in enumerate(sfiles.items()):
            check = pd.read_pickle(self.check_df_files.format(i))
            self.assertLess(np.linalg.norm(df - check),DIFF_TOL)

    def test_get_status(self):
        with SolutionFile(self.difficult_solution_file,fluent_folder= 'test') as sf:
            print(sf.STATUS)
"""

"""
class TestPostOutputFile(unittest.TestCase): 

    file = 'test-files\\test\\yplus_and_htc_data.csv'

    def test_get_data_names(self):

        with PostDataFile(self.file) as pdf:
            df = pdf.readdf()
            
            #print(pdf.data_names)
            for key in pdf.keys():
                print(pdf[key])


class TestXYOutputFile(unittest.TestCase):

    file = 'test-files\\test\\Re19000_standard_k_epsilon'

    def test_get_data(self):

        with XYDataFile(self.file) as xydf:

            df = xydf.readdf()
            for key in xydf.keys():
                print(xydf[key])
"""

if __name__ == '__main__':
    unittest.main()