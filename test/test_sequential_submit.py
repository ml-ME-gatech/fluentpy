from fluentpy.batch.ansys  import APDL_PBS, APDL_Journal,PaceAPDLSubmission,SequentialPaceSubmission
from fluentpy.batch.pbs import PythonPBS
from fluentpy.pace import PaceScript
from fluentpy.batch.fluent import FluentPBS
from fluentpy.batch.submit import PaceFluentSubmission
from fluentpy.tui import FluentJournal

def test_sequential():
    apdl_pbs = APDL_PBS(WALLTIME = 12*60*60,
                        MEMORY = 4,
                        N_PROCESSORS= 8)

    apdl_journal = APDL_Journal('test-files/test/apdl_test.dat')
    apdl_submission = PaceAPDLSubmission(apdl_journal,apdl_pbs)

    script = PaceScript('test-files/test/pace_hw.py',
                         'test-files/test_python_submission')
    
    python_pbs = PythonPBS(script,
                           WALLTIME = 12*60*60,
                           MEMORY = 4,
                           N_PROCESSORS= 8)

    fluent_pbs = FluentPBS(WALLTIME = 12*60*60,
                           MEMORY = 4,
                           N_PROCESSORS = 8)
    fluent_journal = FluentJournal('test.case')

    fluent_submission = PaceFluentSubmission(fluent_journal,fluent_pbs)

    submission = SequentialPaceSubmission([apdl_submission,
                                           python_pbs,
                                           fluent_submission])
            

    submission.write('test_sequential_submission')

def main():

    test_sequential()

if __name__ == '__main__':
    main()
