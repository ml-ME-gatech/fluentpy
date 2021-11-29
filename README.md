# fluentpy
## Overview

Package is meant as a high level interface to fluent. The main purposes are to read fluent output files, and to create fluent input files. This is accomplished by creating a library of classes that can read and write fluent input files.

### IO 
The io module contains a number of classes for reading the basic files created during a fluent simulation. The io module is thus (mostly, there are some exceptions) meant for dealing with simulation _outputs_. 

### TUI
the tui modules contains classes supporting modification of a driving fluent journal file. The goal of this module is to allow the creation of TUI commands in a pythnoic way, while reducing the number of user inputs required. Most of these commands are then implemented through the "FluentRun" Interface, which allows creation of the input file. The tui module is thus primarily used for _inputs_.

