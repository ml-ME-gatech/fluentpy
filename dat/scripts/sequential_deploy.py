from pace import get_job_status
import os
import subprocess
import time

backend = '<backend>'

def wait_for_job(jobid: str) -> None:

    status = ''
    while True:
        if status.lower() == 'completed':
            break
        else:
            time.sleep(1.0)
            status = get_job_status(jobid)
            if status is None:
                status = ''
                
def submit_job(file: str) -> str:

    #run the .pbs script in question in question
    text = backend + ' ' + file
    output = subprocess.run(text,shell= True,capture_output= True,text= True)
    jobid = output.stdout.split('.')[0]
    return jobid

def main():

    files = '<file_list>'
    for file in files:
        jobid = submit_job(file)
        wait_for_job(jobid)

if __name__ == '__main__':
    main()
