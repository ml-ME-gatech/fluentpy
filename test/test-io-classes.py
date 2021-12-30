#native imports
import pandas as pd
import numpy as np
import unittest
import pickle

#pacakge imports
from fluentpy.fluentio import ReportFileOut,SolutionFile,PostDataFile,\
                                      XYDataFile,SurfacePointFile,SurfaceIntegralFile,\
                                      SphereSliceFile

"""
-- Creation -- 
Date: 05.25.2021
Author: Michael Lanahan

-- Last Edit -- 
Date: 12.28.2021
Editor: Michael Lanahan

-- Further Description --

Checking the function of the io classes

"""

DIFF_TOL = 1e-10

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
    check_solution2 = 'test-files\\check\\solution-check2.pkl'
        
    def test_readdf_exist(self):
        
        for solution_string,check_string in zip([self.solution_file,self.solution_file2],[self.solution_check_file,self.check_solution2]):
            with SolutionFile(solution_string) as sfile:
                sfile.readdf()
                check_solution_file = pd.read_pickle(check_string)

            self.assertLess(np.linalg.norm(np.array(check_solution_file,dtype = float)-np.array(sfile.df,dtype = float)),DIFF_TOL)

class TestPostOutputFile(unittest.TestCase): 

    file = 'test-files\\test\\yplus_and_htc_data.csv'
    check_df = 'test-files\\check\\post_df-check.pkl'
    check_keys = 'test-files\\check\\post_df-keys-check.pkl'

    def test_get_data_names(self):

        with PostDataFile(self.file) as pdf:
            df = pdf.readdf()
            
            with open(self.check_keys,'w') as file:
                file.write('\n'.join(list(pdf.keys())))

            with open(self.check_keys,'r') as file:
                check_keys = file.read().split('\n')

            self.assertListEqual(check_keys,list(pdf.keys()))
        
        check = pd.read_pickle(self.check_df)
        self.assertLess(np.linalg.norm(np.array(df,dtype = float)- np.array(check,dtype = float)),DIFF_TOL)

class TestXYOutputFile(unittest.TestCase):

    file = 'test-files\\test\\Re19000_standard_k_epsilon'
    check_file = 'test-files\\check\\XYread-{}.pkl'

    def test_get_data(self):

        with XYDataFile(self.file) as xydf:

            df = xydf.readdf()
            for key in xydf.keys():
                df = xydf[key]

                checkdf = pd.read_pickle(self.check_file.format(key))
                self.assertLess(np.linalg.norm(np.array(df,dtype = float) - np.array(checkdf,dtype = float)),DIFF_TOL)

class TestSurfacePointFile(unittest.TestCase):

    create_file = 'test-files\\check\\test_surface_point_file.spf'
    check_create = 'test-files\\check\\test_surface_point_file_check.spf'
    output_file = 'test-files\\test\\test_output.psf'
    check_output = 'test-files\\check\\test_output_psf.pkl'

    def test_create(self):

        X = np.array([[1,1,1],[2,2,2],[3,3,3]])
        SurfacePointFile.write_fluent_input_from_table(X,self.create_file,['temperature'])

        with open(self.create_file,'r') as file:
            text = file.read()
        
        with open(self.check_create,'r') as file:
            check_text = file.read()
            check_text = check_text.replace(self.check_create,self.create_file)
        
        self.assertEqual(text,check_text)

    def test_read_output(self):

        with SurfacePointFile(self.output_file) as spf:
            df = spf.readdf()

        check = pd.read_pickle(self.check_output).to_numpy()
        self.assertLess(np.linalg.norm(df.to_numpy()- check),DIFF_TOL)

class TestSphereSliceFile(unittest.TestCase):

    create_file = 'test-files\\check\\test_surface_point_file.ssf'
    check_create = 'test-files\\check\\test_surface_point_file_check.ssf'
    output_file = 'test-files\\test\\test_output.ssf.so'
    check_output = 'test-files\\check\\test_output_ssf.pkl'

    def test_create(self):

        X = np.array([[1,1,1],[2,2,2],[3,3,3]])
        R = np.array([1,2,3])
        SurfacePointFile.write_fluent_input_from_table(X,self.create_file,['temperature'])

        with open(self.create_file,'r') as file:
            text = file.read()
        
        with open(self.check_create,'r') as file:
            check_text = file.read()
            check_text = check_text.replace(self.check_create,self.create_file)
        
        self.assertEqual(text,check_text)

    def test_read_output(self):
        
        with SphereSliceFile(self.output_file) as ssf:
            df = ssf.readdf()
                
        check = pd.read_pickle(self.check_output).to_numpy()
        self.assertLess(np.linalg.norm(df.to_numpy()- check),DIFF_TOL)

class TestSurfaceIntegralFile(unittest.TestCase):

    test_file = 'test-files\\test\\surface_integral_file_test.sif'
    check_file = 'test-files\\check\\check_sif.sif'

    def test_read(self):

        with SurfaceIntegralFile(self.test_file) as sif:
            test_dict = sif.read()
        
        with open(self.check_file,'rb') as file:
            check_dict = pickle.load(file)
        
        self.assertDictEqual(test_dict,check_dict)
            
if __name__ == '__main__':
    unittest.main()