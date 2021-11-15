import unittest
from wbfluentpy.io.filesystem import WorkBenchFolder ,DesignPointFolder,FluentFolder
import os

class TestWBBaseClass(unittest.TestCase):

    wb_folder_path = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\'
    wb_root = 'test-files\\wb-folder-test'
    dp_folder = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0'
    files_dir = 'test-files\\wb-folder-test\\wb-folder-test_files'
    progress_dir = 'test-files\\wb-folder-test\\wb-folder-test_files\\progress_files'
    def test_instantation(self):

        wbf = WorkBenchFolder(self.wb_folder_path)
        self.assertEqual(wbf.wb_root,os.path.abspath(self.wb_root))
   
    def test_get_files_dir(self):

        wbf = WorkBenchFolder(self.wb_folder_path)
        self.assertEqual(wbf.files_dir,os.path.abspath(self.files_dir))

    def test_get_progress_dir(self):
        wbf = WorkBenchFolder(self.wb_folder_path)
        self.assertEqual(wbf.progress_dir,os.path.abspath(self.progress_dir))

    def test_get_design_points(self):

        wbf = WorkBenchFolder(self.wb_folder_path)
        dp_list = wbf.get_design_points()
        self.assertEqual(dp_list,[DesignPointFolder(os.path.abspath(self.dp_folder))])


class TestDesignPointFolder(unittest.TestCase):

    dp_folder = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0'
    wb_root = 'test-files\\wb-folder-test'
    
    def test_instantation(self):

        dpf = DesignPointFolder(self.dp_folder)
        self.assertEqual(dpf.wb_root,os.path.abspath(self.wb_root))
        self.assertEqual(os.path.abspath(self.dp_folder),dpf.dp_root)


    def test_get_fluent_folders(self):
        dpf = DesignPointFolder(self.dp_folder)
        ffs = dpf.get_fluent_folders()
        
        for ff in os.listdir(self.dp_folder):
            self.assertIn(FluentFolder(os.path.abspath(os.path.join(self.dp_folder,ff))),ffs)

class TestFluentFolder(unittest.TestCase):

    fluent_folder = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF'
    dp_folder = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0'
    wb_root = 'test-files\\wb-folder-test'
    report_files = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\FFF\\Fluent\\report-file-0.out'
    solution_files ='test-files\\wb-folder-test\\wb-folder-test_files\\progress_files\\dp0\\FFF\\Fluent\\Solution.trn'

    def test_instatation(self):

        ff = FluentFolder(self.fluent_folder)
        self.assertEqual(ff.wb_root,os.path.abspath(self.wb_root))
        self.assertEqual(ff.dp_root,os.path.abspath(self.dp_folder))
        self.assertEqual(ff.ff_root,os.path.abspath(self.fluent_folder))

    def test_get_report_files(self):

        ff = FluentFolder(self.fluent_folder)
        
        rfiles = ff.get_report_files()
        self.assertEqual(rfiles,[os.path.abspath(self.report_files)])

    def test_get_solution_files(self):

        ff = FluentFolder(self.fluent_folder)
        sfiles = ff.get_solution_files()
        self.assertEqual(sfiles,[os.path.abspath(self.solution_files)])


def main():
    unittest.main()

if __name__ == '__main__':
    main()

