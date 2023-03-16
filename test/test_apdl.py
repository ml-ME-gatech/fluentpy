from fluentpy.batch.ansys  import APDL_PBS, APDL_Journal,PaceAPDLSubmission

def test_apdl():
    pbs = APDL_PBS(WALLTIME = 12*60*60,
                        MEMORY = 4,
                        N_PROCESSORS= 8)

    journal = APDL_Journal('test-files/test/apdl_test.dat')

    submission = PaceAPDLSubmission(journal,pbs)

    submission.write('test_apdl_submission')

def main():

    test_apdl()

if __name__ == '__main__':
    main()
