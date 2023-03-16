def custom_splitter(file_or_full_path,
                    return_char = '/'):
    """
    motivated by the fact that for some reason on PACE the os.path.split
    module is NOT functioning correctly 
    """

    file_or_full_path = file_or_full_path.strip()
    if ':' in file_or_full_path:
        directory_path,full_path = file_or_full_path.split(':')
    else:
        directory_path = ''
        full_path = file_or_full_path
    
    chunks = []
    split_path = full_path.split('/')
    for sp in split_path:
        for c in sp.split("\\"):
            for e in c.split('\\\\'):
                if e != '':
                    chunks.append(e)
    
    if directory_path is not None:
        chunks.insert(0,directory_path + ':')
    
    if len(chunks) == 1:
        return None,chunks[0]
    else:
        return return_char.join(chunks[0:-1]),chunks[-1]

def get_matching_external_datafiles(external_load_data):
    """ 
    function that iterates through an "ExternalLoadData" object and finds
    all of the files associated with it. Matches the file names here
    to the file names in data_file_names

    Logs INFO if matching is found between data_file_names and the 
         discovered file names
    Logs WARNING if a new data file name could not be found to replace the old
          this could be intentional, or it could not
    Logs ERROR if a old file name could be found that matches one of the new file
          names and hence will not be used, this is probably not intentional
          and should be logged as an error
    """
    matching = dict()
    logging.info('finding matching input data files to exisiting data files...')
    old_data_files = []
    for i in range(MAX_NUMBER_FILES):
        try:
            if i == 0:
                name = EXTERNAL_DATA_FILE
            else:
                name = str(EXTERNAL_DATA_FILE) + ' ' + str(i)

            external_load_file_data = external_load_data.GetExternalLoadFileData(Name = name)

            location = external_load_file_data.File.Location
            _,file_name = custom_splitter(location)
            old_data_files.append(file_name)

            if file_name in data_file_names:
                matching[name] = data_file_names[file_name]
                logging.info('found matching data file: ' + data_file_names[file_name])
            else:
                logging.warning('Could not find new data file to replace file with filename:' +file_name \
                                + ' - using old data file')
        except:
            logging.info('determined ' + str(i+1) + ' files to be replaced')
            break
    
    for dfn in data_file_names:
        if dfn not in old_data_files:
            logging.error('Could not find file to replace with new data file: ' + dfn)
    
    return matching

def update_external_data_files(external_load_data,matching):
    """
    Updates the file names in the ExternalLoadFileData
    to match the newly supplied file names based on a matching dictionary
    """
    logging.info('replacing existing data files with matching input data filess...')
    
    for name,file in matching.items():
        logging.info('replacing:' + name + ' with file:' + file)
        external_load_file_data = external_load_data.GetExternalLoadFileData(Name = name)
        external_load_file_data.ModifyFileData(FilePath= AbsUserPathName(file))