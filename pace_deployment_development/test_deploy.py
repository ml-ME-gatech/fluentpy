from fluentpy.pace import PaceScript
from fluentpy.batch.pbs import PythonPBS, FluentPBS
from fluentpy.batch.submit import PaceFluentSubmission
from fluentpy.tui import FluentJournal


def test_python():
    ps = PaceScript('my_script.py','test')
    ppbs = PythonPBS(ps,
                    WALLTIME= 10,
                    MEMORY= 1)

    ppbs.write('test.pbs')

def test_fluent_deployment():

    pbs = FluentPBS(WALLTIME= 10*60*60,
                    MEMORY = 6,
                    N_PROCESSORS= 6)
    
    journal = FluentJournal('dummy.cas')

    submission = PaceFluentSubmission(journal,pbs)
    submission.write('fluent_test')


def main():

    #test_python()
    test_fluent_deployment()




if __name__ == '__main__':
    main()