import subprocess
import os

folder = os.path.dirname(os.path.realpath(__file__))
folder = os.path.split(folder)[1]

#alter to file name
file_name = '<file_name>'
backend = '<backend>'

#run the .pbs script in question in question
def submit_job(file: str) -> str:

    #run the .pbs script in question in question
    text = backend + ' ' + file
    output = subprocess.run(text,shell= True,capture_output= True,text= True)
    jobid = output.stdout.split('.')[0]
    return jobid

jobid = submit_job(file_name)
with open('../jobid.txt','a') as jobidfile:
    jobidfile.write(folder + ',' + jobid + '\n')
