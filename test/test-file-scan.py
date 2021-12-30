from fluentpy._file_scan import _get_repeated_text_phrase_lines,_get_text_between_phrase_lines
import unittest

"""

-- Creation -- 
Date: 05.23.2021
Author: Michael Lanahan

-- Last Edit -- 
Date: 05.25.2021
Editor: Michael Lanahan

-- Further Description --

check the ability of the _file-scan functions and make sure the low level operations are performing as expected

> Functions checked
- getTextBetweenPhraseLines
- getRepeatedTextPhraseLines

"""


class TestgetTextBetweenPhraseLines(unittest.TestCase): 

    test_file = 'test-files\\test\\Solution.trn'
    check_text_file = 'test-files\\check\\check_solution.txt'
    _SOL_START_PHRASE = r'Setting Post Processing and Surfaces information ...	 Done.'
    _SOL_END_PHRASE = r'Reading "\\"| gunzip -c'

    def test_text_search(self):

        with open(self.test_file,'r') as file:
            text =_get_text_between_phrase_lines(file,[self._SOL_START_PHRASE,self._SOL_END_PHRASE])
        
        with open(self.check_text_file,'r') as file:
            check = file.read()

        self.assertEqual(text,check)

class TestgetRepeatedTextPhraseLines(unittest.TestCase):

    test_file = 'test-files\\test\\Solution.trn'
    check_file = 'test-files\\check\\check_solution.txt'
    _PARAM_PHRASE = r'WB->Fluent:Parameter name:'

    def test_phrase_line_search(self):

        with open(self.test_file,'r') as file:
            text = _get_repeated_text_phrase_lines(file,self._PARAM_PHRASE)
        
        with open(self.check_file,'r') as file:
            check = file.read()
        
        self.assertEqual(text,check)

if __name__ == '__main__':
    unittest.main()