from matplotlib import pyplot as plt
from fluentPy.io.post import readFluentReportFile
from fluentPy.io._util import getFoldersThatContainExt
from basic import basic_line_plot
import numpy as np

def testBasicFormatPlot():

    path = 'D:\\Michael\\Fluent\\HEMJ_60d-SKE\\HEMJ-60deg-SKE_files\\dp0'

    resultFiles = getFoldersThatContainExt(path,'FFF','.out')
    
    """
    filenames = []
    for rfiles in resultFiles.values():
        for r in rfiles:
            filenames += [r]
    
    print(resultFiles)
    test_file = filenames
    """
    test_file = resultFiles['FFF-3'][0]
    data = readFluentReportFile(test_file)
    print('file: {}'.format(test_file))
    array = np.array(data)
    array = array[:,1:]
    diff_data = np.abs((array[1:,:] - array[0:-1,:])/array[0:-1,:])
    print(np.max(diff_data))
    fig,ax = plt.subplots()
    names = ['CS-Temp','Max Temp','Inlet Pressure']
    basic_line_plot(ax,np.array(data.index[1:]),diff_data,
    'Iteration','Absolute Normalized Change',names = names,yscale = 'log')

    plt.show()


def main():

    testBasicFormatPlot()


if __name__ == '__main__':
    main()