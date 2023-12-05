ACCESS-NRI Model Live Diagnostics 
============================

.. toctree::
   :maxdepth: 0
   :hidden:

   self
   notebooks/getting_started_tutorial
   med_diagnostics

Current version ``v1.0``

Welcome to the documentation and reference guide for the `ACCESS-NRI <https://www.access-nri.org.au/>`_ Model Live Diagnostics package. 
The Model Live Diagnostics framework is designed to provide useful and practical Jupyter-based tools for interactive monitoring and diagnostic 
analyses of currently running (aka 'live') ACCESS climate models on the Australian NCI supercomputer Gadi.

This documentation aims to introduce these new tools, and support both new and existing users to get the most out of them using the 
`Australia Research Environment <https://are.nci.org.au/>`_ (ARE).

The ACCESS-NRI Model Live Diagnostics package, and the tools that support it, are still a work in progress. We value your constructive feedback, 
especially in the form of reporting issues/bugs or suggesting ways to improve the framework. To do so, please feel free to open an 
issue `here <https://github.com/ACCESS-NRI/MED-live-diagnostics/issues>`_.

What does this package do?
==========================
The primary purpose of the ACCESS-NRI Model Live Diagnostics package is to provide a simple, easy to use and accessible framework for the ACCESS 
modelling community to check, monitor, visualise and evaluate model behaviour and progress on currently running or 'live' ACCESS models on the `Australian 
NCI supercomputer Gadi <https://nci.org.au/our-systems/hpc-systems>`_. In addition to monitoring a live model, the package provides the functionality to 
load, visualise and compare legacy ACCESS model data with the selected live user model. 

This package is currently in active development within the Model Evaluation Team at the `Australian Earth System Symulator (ACCESS-NRI) <https://www.access-nri.org.au/>`_
so watch this space for version updates containing new features, model diagnostics tools and visualisation options!

Quick-start guide
==================
The ACCESS-NRI Model Live Diagnostics framework is intended to be used in ARE ``JupyterLab`` sessions running on Gadi. While it may be possible 
to use the framework outside of Jupyter notebooks, user experience will be impacted as this option is not supported.

Prerequisites
^^^^^^^^^^^^^

Model Live diagnostics uses both the `ACCESS-NRI Intake Catalog <https://github.com/ACCESS-NRI/access-nri-intake-catalog/tree/main>`_ to handle model data 
and the `Australian Research Environment (ARE) <https://are.nci.org.au/>`_ to run ``JupyterLab`` sessions. Before starting, please ensure you:

#. **Have an account at NCI**: see the `NCI documentation for creating an account <https://opus.nci.org.au/display/Help/How+to+create+an+NCI+user+account>`_ if you don't have one. 
   Note you will need to join a project with a compute allocation in order to run MLD. If you don't know which project is appropriate you will need to seek help from your local 
   group or IT support.

#. **Access to the project(s) that house the model data you are interested in**: the `ACCESS-NRI Intake Catalog <https://github.com/ACCESS-NRI/access-nri-intake-catalog/tree/main>`_ references data 
   products across multiple projects on Gadi. You can find the list of currently support projects 
   `here <https://github.com/ACCESS-NRI/access-nri-intake-catalog/blob/main/docs/project_list.rst>`_.

   If you wish to be able to access **ALL** the data in the ACCESS-NRI Intake Catalog, you will need to be a member of **ALL** supported projects. If you are unsure how to join projects on Gadi, 
   please see the `NCI documentation <https://opus.nci.org.au/display/Help/How+to+connect+to+a+project>`_ for instructions.

#. **RECOMMENDED** Join the ACCESS-NRI project ``xp65`` to gain access to the `ACCESS-NRI conda environment <https://github.com/ACCESS-NRI/MED-condaenv>`_ on Gadi.

Start an ARE JupyterLab session
^^^^^^^^^^^^^

#. Log into to `ARE <https://are.nci.org.au>`_ and start a ``JupyterLab`` instance with the following recommended settings:

   As these datasets are fairly large / memory intensive, the following 'Custom' settings are recommended to minimise SU consumption:

   +-----------------------+----------------------------------------------+
   | Compute Size          | Custom (2 cpus, 18G mem)                     |  
   +-----------------------+----------------------------------------------+
   | Storage               | e.g. ``gdata/project1+gdata/project2``       |     
   +-----------------------+----------------------------------------------+
   
   Advanced Options:

   It is recommended that you use the `ACCESS-NRI MED conda environment <https://github.com/ACCESS-NRI/MED-condaenv>`_ that comes pre-installed with the Model Live Diagnostics package
   when running ARE JupyterLab sessions.
   
   +-------------------------+----------------------------------+
   | Module directories      | ``/g/data/xp65/public/modules``  |
   +-------------------------+----------------------------------+
   | Modules                 | ``conda/access-med``             |
   +-------------------------+----------------------------------+

#. You should now have an ARE ``JupyterLab`` instance running using the `ACCESS-NRI MED Conda environment <https://github.com/ACCESS-NRI/MED-condaenv>`_.

#. Follow the 'Getting started' tutorial found `here <https://med-live-diagnostics.readthedocs.io/en/latest/notebooks/getting_started_tutorial.html>`_ to begin your first Model Live Diagnostics session.

Installing the package directly
^^^^^^^^^^^^^

Alternatively, the Model Live Diagnostics package can be installed directly into your chosen conda environment on Gadi either from the 
`access-nri conda channel <https://anaconda.org/accessnri/med-diagnostics>`_ or `PyPI <https://pypi.org/project/med-diagnostics/>`_.

+---------------+-------------------------------------------------+
| conda         | ``conda install -c accessnri med-diagnostics``  |
+---------------+-------------------------------------------------+
| PyPI          | ``pip install med-diagnostics``                 |
+---------------+-------------------------------------------------+

