from multiprocessing.sharedctypes import Value
from tkinter.tix import MAX
import pandas as pd
from typing import Union
from numpy.polynomial.polynomial import Polynomial
import numpy as np
import os

"""
Author: Michael Lanahan
Date created: 07.29.2021
Last Edit: 11.21.2021

Description
----------------
The purpose of this library is to provide some basic classes for easily 
creating fluent material library files - essentially formatted text files
leveraging the pandas library. For some reason entering in this data into fluent
is virtually impossible if you have more than a few data points - so this should 
take some of the tedium out of it.
"""

DEFAULT_INTERPOLATION = 'polynomial piecewise-linear'

class Material:

        """
        Description
        ----------
        The Material class is a basic class for describing a material in fluent -
        either a solid or a fluid. 

        Parameters
        ----------
        df: DataFrame - data for the material
        name: str - name of the material 
        mattype: str - type of the material, either fluid or solid
        chemical_formulae: None by default, but can be added
        interpolation_type: how to interpolate the data, options are taken from Fluent 

        Methods
        ----------
        add_property(pd.Series,interpolation_type: None) - allows the addition of properties to the materials, such as viscosity,
                                                     conductivity, ect.... 

                                                     The first argument is a series containing the data for the property
                                                     of the material, while the second argument is the type of interpolation to use 
                                                     which if not provided defaults to the global interpolation type
        write(file)- writes the material to a file
        """

        endchar = '\t)'
        def __init__(self,df:pd.DataFrame,
                          name: str,
                          mattype: str,
                          chemical_formulae = None,
                          interpolation_type = DEFAULT_INTERPOLATION):

                mattype = mattype.lower()
                self.check_initializer(df,name,mattype)

                try:
                        if isinstance(interpolation_type,str):
                                self.__interpolation_type = {key:interpolation_type for key in df.columns}
                except AttributeError:
                        self.__interpolation_type = interpolation_type

                self.__df = df
                self.__txt = '\t('  + name + ' ' + mattype + '\n'
                if chemical_formulae is None:
                        chemical_formulae = '#f'
                
                self.__txt += '\t\t(chemical-formula . ' + chemical_formulae + ')\n'
                
                self.data_to_text()

        @staticmethod
        def check_initializer(*args):

            """
            check initialization arguments
            """
            
            if not isinstance(args[0],pd.DataFrame) and not isinstance(args[0],pd.Series) and not isinstance(args[0],Polynomial):
                raise TypeError('first argument must be a dataframe, series, or polynomial')

            if not isinstance(args[1],str):
                raise TypeError('name argument must be string')

            if not isinstance(args[2],str):
                raise TypeError('material type must be a string, either solid or fluid')
            else:
                if args[2] != 'fluid' and args[2] != 'solid':
                    raise ValueError('material types other than fluid and solid not supported')

        @property
        def df(self):
                return self.__df
        
        @property
        def interpolation_type(self):
            return self.__interpolation_type
        
        @property
        def txt(self):
                return self.__txt
        
        @txt.setter
        def txt(self,text):
                self.__txt = text

        def add_property(self,data: pd.Series,interpolation_type = None) -> None:
            
            if interpolation_type is None:
                    interpolation_type = self.interpolation_type
        
            self.txt += '\t'+ str(Property(data,interpolation_type= interpolation_type)) + ')\n'

        def data_to_text(self):
            
            for name in self.df.columns:
                self.add_property(self.df[name],self.interpolation_type[name])

        def __str__(self):
                return self.txt + self.endchar
        
        def write(self,f):
                try:
                        with open(f,'w') as file:
                                file.write(self.__str__()) 
                except TypeError:
                        f.write(self.__str__())

class FluentPolynomial:

        MAX_ORDER = 8
        MIN_ORDER = 1

        def __init__(self, coeff: np.ndarray):
                
                self.coeff = coeff.squeeze()
                if self.coeff.ndim != 1:
                        if self.coeff.ndim == 0:
                                self.coeff = np.array(self.coeff)
                        else:
                                raise ValueError('coefficients must be interpreable as a 1-D array')

                if self.coeff.shape[0] > self.MAX_ORDER:
                        raise ValueError('Maximumum polynomial order of: {} '.format(self.MAX_ORDER-1))
                
                if self.coeff.shape[0] < self.MIN_ORDER:
                        raise ValueError('Minimum polynomial order of: {} '.format(self.MIN_ORDER-1))
        
        def __str__(self) -> str:

                txt = '(polynomial '
                for coeff in self.coeff:
                        txt += str(coeff) + ' '
        
                return txt[0:-1] + ')'

                
class Property:

        """
        Description:
        -----------
        class for represnting properties of Materials - A Material is thus just collection
        of Properties. 

        Parameters:
        -----------
        df: pd.Series - a Series object containing the data for the Property
        interpolation_type: str - a string specifying the type of interpolation to use on the data

        Methods:
        -----------
        __str__() - string representation of a property which is interable by Fluent
        """


        def __init__(self,df: pd.Series,
                           interpolation_type = DEFAULT_INTERPOLATION):

                self.__df = df
                self.__interpolation_type = interpolation_type

        @property
        def df(self):
                return self.__df

        @property
        def interpolation_type(self):
                return self.__interpolation_type

        def _txt_constant_property(self,prop_name: str,
                                        constant: float) -> str:

            return  '(constant . ' + str(constant) + ')'
        
        def _to_polynomial(self) -> str:

                if isinstance(self.df,Polynomial):
                        return str(FluentPolynomial(np.fliplr(self.df.coeff)))
                else:
                        return str(FluentPolynomial(self.df.to_numpy()))

        def _series_property(self) -> str:

            txt = '('+ self.interpolation_type + ' '
            for i in range(self.df.shape[0]):
                    txt += '(' + str(self.df.index[i]) + ' . ' + str(self.df.iloc[i]) + ')' + ' '

            txt = txt[0:-1]
            txt += ')'
            return txt

        def _piecewise_polynomial(self):
            if self.df.shape[0] == 1:
                return self._txt_constant_property(self.df.name,self.df.iloc[0])
            
            else:
                return self._series_property()
        
        def to_txt(self):
                txt = '\t(' + self.df.name + ' '
                
                if self.interpolation_type == DEFAULT_INTERPOLATION or self.interpolation_type == 'constant':
                        txt += self._piecewise_polynomial()
                elif self.interpolation_type == 'polynomial':
                        txt += self._to_polynomial()
                else:
                        raise ValueError('interpolation type: {} not supported'.format(self.interpolation_type))
                return txt

        def __str__(self):
                return self.to_txt()

class MaterialDataBase:
        """
        Description
        -----------
        Class for representing a material data base from Fluent, or an .scm file. 
        This consists of a collection of Materials with some Fluent Specific heading

        Parameters
        -----------
        matlist: list - a list of materials

        Methods
        -----------
        read(file) - read in a list of materials from a file
        write(file) - write material library to a file
        append(material) - append a material to the library
        """
        
        endchar = ')'
        thisdir = os.path.split(__file__)[0]
        header_file = os.path.join(thisdir,'dat','mat_prop_header_text.txt')
        
        with open(header_file,'r') as file:
                init_text = file.read()

        def __init__(self,matlist: list):
                self.__txt = self.init_text + '\n\n(\n'
                for material in matlist:
                        self.__txt += str(material) + '\n\n'

        @property
        def txt(self):
                return self.__txt
        
        @txt.setter
        def txt(self,text):
                self.__txt = text

        def __str__(self):
                return self.txt + self.endchar
        
        def write(self,file):
                with open(file,'w') as file:
                        file.write(self.__str__())
        
        def read(self,file):
                with open(file,'r') as file:
                        self.txt = file.read()

        def append(self,material:Material):
                self.txt += str(material) + '\n\n'
