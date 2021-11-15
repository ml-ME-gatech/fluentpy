import os
import sys

"""
#Items to exclude from adding to the path
EXLUDE = ['__pycache__']

#get the directory that this file is located in
head,_ = os.path.split(__file__)
sys.path.append(head)

#get the folders
files = os.listdir(head)

#add all subsequent folders to the path
#NOTE: If we want this to act recursively, will have to make this a little more complicated
#but this tends to not be the case in other packages
for f in files:
    folder = os.path.join(head,f)
    if os.path.isdir(folder) and f not in EXLUDE:
        sys.path.append(folder)

"""