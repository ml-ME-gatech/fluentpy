from pace import get_job_name,get_job_status
import os
import subprocess
import time

solution_file_name  = '<solution_file_name>'
submit_file = '<submit_file>'
backend = '<backend>'
check_time = <check_time>
num_resubmit = <num_resubmit>

def submit_job(file: str,
               backend: str) -> str:

    #run the .pbs script in question in question
    text = backend + ' ' + file
    output = subprocess.run(text,shell= True,capture_output= True,text= True)
    jobid = output.stdout.split('.')[0]
    return jobid

def get_job_dict() -> dict:
    job_dict = {}
    with open('jobid.txt','r') as jobfile:
        for line in jobfile.readlines():
            job_folder,job_id = line.split(',')
            job_folder = job_folder.strip()
            job_id = job_id.strip() 
            job_dict[job_folder] = job_id

    return job_dict

def write_job_dict(job_dict: dict) -> None:

    with open('jobid.txt','w') as jobfile:
        for job_folder,job_id in job_dict.items():
            jobfile.write(job_folder + ',' + job_id + '\n')
    
def log_job(job_folder: str,
            job_id: str) -> None:

    jobdict = get_job_dict()
    jobdict[job_folder] = job_id
    write_job_dict(jobdict)

def resubmit_job(file: str,
                 job_folder: str,
                 backend: str) -> str:
    
    if backend == 'qsub':
        del_cmd = 'qdel'
    elif backend == 'sbatch':
        del_cmd = 'scancel'
    
    subprocess.run(del_cmd + ' ' + job_id ,shell= True,capture_output= True,text= True)
    os.chdir(job_folder)
    jobid =  submit_job(file,backend)
    os.chdir('..')
    log_job(job_folder,jobid)
    return jobid
    
for i in range(num_resubmit):
    time.sleep(check_time)
    print('Checking for failed job submissions...{}'.format(i+1))

    job_dict = get_job_dict()

    flag = True
    for jobfolder,job_id in job_dict.items():
        if os.path.exists(os.path.join(jobfolder,solution_file_name)):
            pass
        else:
            status = get_job_status(job_id)
            if status == 'Running' or status == 'Completed':
                flag = False
                print('Re-submitting job in folder: {} with id: '.format(jobfolder,job_id))
                resubmit_job(submit_file,jobfolder,backend)
            elif status == 'Queued':
                flag = False
            
    if flag: 
        print('All Jobs have been submitted successfully')
        break
