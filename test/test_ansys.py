from fluentpy.batch.ansys  import MechanicalPBS, MechanicalJournal
from fluentpy.batch.ansys import PaceMechanicalSubmission

pbs = MechanicalPBS(WALLTIME = 12*60*60,
                    MEMORY = 4,
                    N_PROCESSORS= 8,
                    input_file= 'class3.wbjn')

# pbs.write('D:\Scripting\Code\MechanicalPBS.sh')
journal = MechanicalJournal('D:/Scripting/InputFiles/Testing_NoData.wbpz', 
                    'D:/Scripting/Trial 1/Testing.wbpj', 
                    'D:/Scripting/InputFiles/HEMJ60deg-2-5-00150.dat.gz', 
                    'D:/Scripting/Trial 1/Output.csv',
                    )

submission = PaceMechanicalSubmission(journal,pbs)

submission.write('Test')