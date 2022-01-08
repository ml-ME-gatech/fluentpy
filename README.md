# fluentpy
## Overview

The fluentpy package is meant as a high level scripting interface to fluent. The main purposes are to read fluent output files, and to create fluent input files. This is accomplished by creating a library of classes that can read and write fluent input files. This package was originally created to support batch parameter runs on a HPC Linux System, but has reached a stage of development that I have decided to make it more accessible for other uses. 

The main usage is thus through the "batch" module, creating batch folder structures from parameter tables. I expose all of the "low" level Python classes creating the TUI commands from the parsing of the batch file in the "tui" module, so that the advanced user can use these to create their own scripts. 

This project is in its infancy, and there is still a ton of work to complete if it ever wants to get to v1.0 so any support is much appreciated.

### IO 
The fluentio module contains a number of classes for reading the basic files created during a fluent simulation. The fluentio module is thus (mostly, there are some exceptions) meant for dealing with simulation _outputs_. 

#### Contributing
All classes must inherit the FluentFile base class, and implement the neccesseary "readdf()" method (even if there is no readdf() method required, in this case, raise a NotImplementedError). If you would like to add additional functionality to the FluentFile base class I am ammenable to improvements. 

In general, modification of exisiting classes are accetable if there is an obvious benefit such as interpability, performance, reducing errors, ect.. but this will require some demonstration before implementation.

### TUI
the tui modules contains classes supporting modification of a driving fluent journal file. The goal of this module is to allow the creation of TUI commands in a pythnoic way, while reducing the number of user inputs required. Most of these commands are then implemented through the "FluentRun" interface, which allows creation of the input file. The tui module is thus primarily used for _inputs_.

#### Contributing
There are a lot of contributions here that can be made, as there is a lot of fluent functionality. In general, please determine if it makes sense to inherit from an existing base class such as

1. FluentBoundary Condition (or FluentFluidBoundaryCondition, FluentSolidBoundaryCondition)
2. RPSetVarModification
3. TwoEquationModelConstants
4. ModelModification/ViscousModelModification
5. MaterialProperty
6. MaterialModification
7. FluentSolidZone

To add the addittional functionality that you require. 

