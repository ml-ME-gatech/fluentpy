#native imports
import os
import unittest
import pandas as pd
import numpy as np

#package imports
from wbfluentpy.io.filesystem import FluentFolder,DesignPointFolder
from wbfluentpy.link.linker_utils import zero_norm_linker_dict,zero_percent_diff_linker_dict
from wbfluentpy.link.classes import DesignPointModule,DefaultFluentFolderLink,DefaultFluentFolderModule,ExcelFileModule
from wbfluentpy.io.filesystem import FluentFolder
#other package imports
from hemjpy.io.legacy import getCaseData

"""
-- Creation -- 
Date: 05.31.2021
Author: Michael Lanahan

-- Last Edit -- 
Date: 06.11.2021
Editor: Michael Lanahan

-- Further Description --
Testing data link files

> Functions Checked
- zero_norm_linker_dict
- zero_percent_diff_linker_dict
"""


class TestEstablishNormLink(unittest.TestCase): 

    def test_establish_zero_norm(self):

        shared_cols = ['foo','bar']
        cols1 = shared_cols + ['else']
        cols2 = shared_cols
        shared_array = np.random.random([1000,2])*100

        additional_rows = np.random.random([1000,2])*100
        additional_columms = np.random.random([2000,1])*100

        array1 = np.concatenate([np.concatenate([shared_array,additional_rows],axis = 0),
        additional_columms],axis = 1)
        
        array2 = shared_array.copy()
        array2[0,:] = shared_array[2,:]
        array2[2,:] = shared_array[0,:]

        df1 = pd.DataFrame(array1,columns = cols1)
        df2 = pd.DataFrame(array2,columns = cols2)
        link = zero_norm_linker_dict(df1,df2)
        
        switched = [0,2]
        for i in range(0,1000):
            if i not in switched:
                self.assertEqual(link[i],i)
        
        self.assertEqual(link[0],2)
        self.assertEqual(link[2],0)

class TestEstablishPercentLink(unittest.TestCase):
    dp_folder = 'test-files\\wb-folder-test\\wb-folder-test_files\\dp0\\'
    excel_file_name = 'Y:\\Michael\\hemjpy\\data\\legacy.xlsx'

    @property
    def excel_parser(self):

        def excel_parser(*args):

            return getCaseData('SimParams',filter_units = True)
        
        return excel_parser
    
    def excel_row_getter(self,row):

        def row_getter(files,dirs):
            dat = getCaseData('SimParams',filter_units = True)
            return dat.loc[row,:]
        
        return row_getter
    
    def test_establish_zero_percent(self):
        ignore_columns = ['Omega-out','Omega-in']
        dpm = DesignPointModule(self.dp_folder)
        param_df = dpm()
        
        excel_func = self.excel_parser
        excel_df = excel_func()

        link_dict = zero_percent_diff_linker_dict(param_df,excel_df,ignore_columns = ignore_columns)
        
        #make the links
        for frow,erow in link_dict.items():
            fluentfolder = param_df.index[frow]
            eindex = excel_df.index[erow]
            
            efunc = self.excel_row_getter(eindex)
            print(fluentfolder)
            ffm = DefaultFluentFolderModule(fluentfolder)
            efm = ExcelFileModule(self.excel_file_name,efunc)
            link = DefaultFluentFolderLink(ffm,efm)
            link.link(ignore_columns = ignore_columns)
        
        #read and verify the links
        for frow in link_dict:
            print(param_df.index[frow])
            rfile = FluentFolder(param_df.index[frow]).get_report_files()[0]
            fluentfolder = os.path.split(os.path.split(rfile)[0])[0]
            print(fluentfolder)
            link = DefaultFluentFolderLink.from_file(os.path.join(fluentfolder,'.dmlnk'))

def main():
    unittest.main()

if __name__ == '__main__':
    main()

