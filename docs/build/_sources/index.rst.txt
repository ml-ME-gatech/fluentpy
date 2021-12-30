Welcome to fluentpy's API documentation!
========================================
The documentation for API is split into IO (in fluentio),TUI, and batch. 

fluentio
========
fluentio is a submodule intended to provided convinient classes for reading (and sometimes writing) 
output files created from fluent, almost exclusively into the pandas DataFrame format. Common files
include solution files (or transcript files), report files, and post data files, or files created by
exporting surface data from CFD Post. This list will grow as needed and support will be added for additional
file formats

** The solution file is challenging to read due to the format of the text data. While no cases have been
found that read incorrectly presently, it is not to difficult to imagine cases where this will fail. Please
report the issue on github.

.. automodule:: fluentpy.fluentio
    :members:

TUI
===
The tui module provides basic class interface building blocks for producing strings interperable
by the tui interface in fluent. These are only required if something needs to be modified at run time,
so if a fluent case is set-up entirely the way you want it, don't bother. These do provide a convinient
interface for scripting exotic batch jobs, and are the base interface for the batch module. In order
to make progress and provide support for basic cases, the functionality of these interfaces has been limited
in some cases, such as boundary conditions, or cell zone modification. Additional functionality will be
added to exisiting classes and additional classes will be added as need be.

.. automodule:: fluentpy.tui
    :members:

.. toctree::
   :maxdepth: 2
   :caption: Contents:

batch
=====
.. automodule :: fluentpy.batch.submit
    :members:

.. automodule :: fluentpy.batch.pbs
    :members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
