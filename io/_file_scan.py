import re
import numpy as np
import itertools


__all__ = ['']

"""
Creation:
Author(s): Michael Lanahan 
Date: 05.10.2021

Last Edit: 
Editor(s): Michael Lanahan
Date: 09.16.2021

-- Description -- 
low level functions for scanning through text that return a very specific requested output
and perform further parsing on the found text. In general, I try to keep as little as possible 
in memory because cfd type files have a tendency to be huge and it is better to look at buffers of 
files instead of the whole file if possible with very large text files to avoid memory issues, though
performance is undoubtadly hit when compared to built in python functions. 

- BUGS 05.25.2021
if the buffer is to small in _buffered_file_line_search, there is a chance that the splitting of the 
text could land directly between search phrases - i.e. split the search phrase in half, and the text
will not be found.
"""

def _buffered_file_line_search(search_function: callable):        #the search function

    """
    Parameters
    ----------
    search_function: the function to perform the search on the specified chunk of text

    Returns
    ----------
    the requested text, if found, or None, if the requested text was not found

    This is meant to function as a decorator for the actual search functions to facilitate
    the buffered file saerching
    """

    def search_wrapper(file,                              
                        *args,                            
                        buffer = 1024**2,      
                        **kwargs):
        
        """
        Parameters
        ----------
        file: the TextIOWrapper object native to python
        *args: additional function arguments for input into the search_function
        buffer: the buffer to read
        **kwargs: additional keyword arguments for input into the search_function

        Returns
        ----------
        stripped text found 
        """
        
        text = ''
        continue_flag = True
        record = False
        while continue_flag:
            input_text = file.read(buffer)
            
            if input_text == '':
                break
            
            out_text,continue_flag,record = search_function(input_text,
                                                            record = record,
                                                            *args,**kwargs)
            
            if record:
                text += out_text
        
        return text.strip()

    return search_wrapper

#Finds the text between a lines of two phrases, starts on the next line
#after the phrase found, and stops on the line before the last phrase

@_buffered_file_line_search
def _get_text_between_phrase_lines(text: str,                #text block
                                    pair: list,               #list with len() = 2
                                    include_pairs = False,     #option to include the lines containing the pairs
                                    record = False,
                              ):

    """
    Parameters
    ----------
    text: the text block to search, a string
    pair: the two phrases to locate and record the text between, a list of strings
    include_pairs: include the pairs on the returned next
    record: keyword argument meant to be used with the buffered_file_line_search decorator

    Returns
    ----------
    the requested text if found, or part of the requested text if the buffer does not contain
    the full amount of text between phrases
    """

    start = re.search(pair[0],text)
    end = re.search(pair[1],text)

    if include_pairs:
        if start:
            start = start.start()
        if end:
            end = end.end()
    else:
        if start:
            start = start.end()
        if end:
            end = end.start()

    if start and end:
        return text[start:end],False,True
    
    elif not start and end:
        return text[0:end],False,True
    
    elif start and not end:
        return text[start:],True,True
    
    elif not start and not end:

        if record:
            return text,True,True
        else: 
            return None,True,False

@_buffered_file_line_search
def _get_repeated_text_phrase_lines(text: str,    #the name of the file
                               phrase: str,  #the phrase to search for
                               record = False,
                               endline = '\n'
                               ):
    """
    Description
    ----------
    searches the file for a phrase that is supposedly repeated on multiple 
    lines in row, and returns the block of text for which the phrase is repeated

    Parameters
    ----------
    text: the text block to search, a string
    phrase: the repeated phrase to look for
    record: keyword argument meant to be used with the buffered_file_line_search decorator
    endline: the end of a line character in case this differs from the default

    Returns
    ----------
    the requested block of text, or part of the requested block of text if found
    returns None if not found
    """

    eol1,eol2 = itertools.tee(re.finditer('\n',text),2)
    _start = False
    line = text[0:next(eol2).start()]
    if phrase in line:
        output = line
    else:
        output = ''
    
    cflag = True
    for e2,e1 in zip(eol2,eol1):
        line = text[e1.start():e2.start()]
        if phrase in line:
            _start = True
            output += line
        else:
            if _start:
                cflag = False
                break
                

    if output != '':
        try:
            next(eol2)
            return output,cflag,True
        except StopIteration:
            return output,cflag,True
    
    else:
        return output,True,record
            

def _convert_delimited_text(text:str,
                            delim:str,
                            newline:str,
                            dtype:type,
                            force_columns = True,
                            empty_columns = 'donotfilemptycolumns') -> np.ndarray:

    """
    Description
    ----------
    converts a block of text that contains delimited values into a numpy array

    Parameters
    ----------
    text: text to convert - string
    delim: the delimiter
    newline: the newline character
    dtype: datatype to convert the values to
    force_columns: the number of columns in the array to force - this may
                   cause issues if you are not positive on the width
    empty_columns: if columns are empty, what do you fill the columns with.
                    the default, donotfilemptycolumns, will raise a ValueError

    Returns
    ----------
    Returns the converted values as a numpy array. If values cannot be converted
    will place nan in array

    Limitations
    ----------
    will only support adding width to the columns on the last rows
    this would required some additional thought to let it fill in intermediate columns
    """

    def _column_coerce(loldat: list,
                        width: int) -> None:

        """
        make the list of lists a uniform size to make the np.array
        intializer happy
        """
        
        if empty_columns == 'donotfilemptycolumns': 
            raise ValueError('must specificy empty_columns as something other than donotfilemptycolumns')
        
        for i in range(len(loldat)):
            for _ in range(width - len(loldat[i])):
                loldat[i].append(empty_columns)

    lines_start,lines_end = itertools.tee(re.finditer(newline,text))
    loldat = []
    loldat.append([dtype(r) for r in re.split(delim,text[0:next(lines_end).start()].strip())])
    
    max_col = len(loldat[0])
    coerce = False
    
    #main parsing login down here - as you can see 
    #this is expecting some pretty nice looking txt data
    for ls,le in zip(lines_start,lines_end):
        line = text[ls.start():le.start()].strip()
        row = re.split(delim,line)
        if max_col < len(row):
            coerce = True
            max_col = len(row )
        if max_col != len(row):
            coerce = True
        
        dat = []
        for v in row:
            try:
                dat.append(dtype(v))
            except ValueError:
                dat.append(None)
        
        loldat.append(dat)

    if force_columns and coerce:
        _column_coerce(loldat,max_col)
    
    return np.array(loldat)