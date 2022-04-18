import subprocess

#alter to file name
file = '{}'

#run the .pbs script in question in question
text = 'qsub ' + file
subprocess.run(text,shell= True)