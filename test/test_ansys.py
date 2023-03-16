from fluentpy.batch.ansys  import MechanicalPBS, MechanicalTemplate,PaceMechanicalSubmission,PaceFluentMechanicalSimulation
from fluentpy.batch.pbs import FluentPBS
from fluentpy.tui import FluentJournal, Solver_Iterator, Solver
from fluentpy.batch.submit import PaceFluentSubmission

def test_mechanical():
    pbs = MechanicalPBS(WALLTIME = 12*60*60,
                        MEMORY = 4,
                        N_PROCESSORS= 8)

    # pbs.write('D:\Scripting\Code\MechanicalPBS.sh')
    template = MechanicalTemplate('Testing_NoData.wbpz', 
                                'Testing.wbpj', 
                                fluent_data_file='result.dat')


    submission = PaceMechanicalSubmission(template,pbs)

    submission.write('test_mech_template')

def test_combined_mechanical_fluid():

    fluent_pbs = FluentPBS(WALLTIME= 12*60*60,
                           N_PROCESSORS= 4,
                           MEMORY= 4)
    
    solver = Solver(solver_iterator = Solver_Iterator(niter= 1000))
    fluent_journal = FluentJournal('simulation.cas',
                                    solver = solver)
    fluent_submission = PaceFluentSubmission(fluent_journal,fluent_pbs)

    mech_pbs = MechanicalPBS(WALLTIME = 1*60*60,
                             N_PROCESSORS = 2,
                             MEMORY = 4)

    mech_template = MechanicalTemplate('Testing_NoData.wbpz')
    
    mech_submission = PaceMechanicalSubmission(mech_template,mech_pbs)
    combined_submission = PaceFluentMechanicalSimulation(fluent_submission,mech_submission)

    combined_submission.write('test_combined_submission')

def main():

    #test_mechanical()
    test_combined_mechanical_fluid()

if __name__ == '__main__':
    main()