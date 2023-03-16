from fluentpy.batch.pbs import PythonPBS
from fluentpy.pace import PaceScript

def test_apdl():
    
    
    script = PaceScript('test-files/test/pace_hw.py',
                         'test-files/test_python_submission')
    pbs = PythonPBS(script,
                        WALLTIME = 12*60*60,
                        MEMORY = 4,
                        N_PROCESSORS= 8)



    pbs.write('test-files/check/write_python.pbs')
    script.write('test-files/check/pace_hw.py')

def main():

    test_apdl()

if __name__ == '__main__':
    main()
