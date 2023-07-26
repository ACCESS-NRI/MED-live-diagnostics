ACCESS-NRI Model Diagnostics v0.0.1
===================================

.. toctree::
   :maxdepth: 2
   :hidden:

Welcome to the documentation and reference guide for the `ACCESS-NRI <https://www.access-nri.org.au/>`_ Model Live Diagnostics package. 
The Model Live Diagnostics framework is designed to provide useful and practical Jupyter-based tools for the monitoring and diagnostic 
analyses of currently running (aka 'live') ACCESS climate models on the Australian NCI supercomputer Gadi.

This documentation aims to introduce these new tools, and support both new and existing users to get the most out of them using the 
Australia Research Environment (ARE).

The ACCESS-NRI Model Live Diagnostics package, and the tools that support it, are still a work in progress. We value your feedback, 
especially in the form of reporting issues/bugs or suggesting ways to improve the framework. To do so, please open an 
issue `here <https://github.com/ACCESS-NRI/MED-live-diagnostics/issues>`_.

What does this package do?
==========================
The primary purpose of the ACCESS-NRI Model Live Diagnostics package is to provide a simple, easy to use and accessible framework for the ACCESS 
modelling community to check, monitor, visualise and evaluate model behaviour and progress on currently running or 'live' ACCESS models on the `Australian 
NCI supercomuter Gadi <https://nci.org.au/our-systems/hpc-systems>`_. In addition to monitoring a live model, the package provides the functionality to 
load, visualise and compare legacy ACCESS model data with the selected live user model. 

This package is currently in active development within the Model Evaluation Team at the `Australian Earth System Symulator (ACCESS-NRI) <https://www.access-nri.org.au/>`_
so watch this space for version updates containing new features, model diagnostics tools and visualisation options!

Quick-start guide
==================
The ACCESS-NRI Model Live Diagnostics framework is intended to be used in Jupyter notebooks running on Gadi. While it may be possible 
to use the framework outside of Jupyter notebooks, user experience will be impacted as this option is not supported.

Prerequisites
^^^^^^^^^^^^^

As MLD uses both the `ACCESS-NRI Intake Catalog <https://github.com/ACCESS-NRI/access-nri-intake-catalog/tree/main>`_ to handle model data 
and the `Australian Research Environment (ARE) <https://are-auth.nci.org.au/>`_ to run JupyterLab, you will need to have the following:

#. **An account at NCI**: see the `NCI documentation for creating an account <https://opus.nci.org.au/display/Help/How+to+create+an+NCI+user+account>`_ if you don't have one. 
   Note you will need to join a project with a compute allocation. If you don't know what project is 
   appropriate you will need to seek help from your local group or IT support.

#. **Access to the project(s) that house the model data you are interested in**: the ACCESS-NRI Intake Catalog references data 
   products across multiple projects on Gadi. You can find the list of currently support projects 
   `here <https://github.com/ACCESS-NRI/access-nri-intake-catalog/blob/main/docs/project_list.rst>`_.

   If you wish to be able to access **all** the data in the ACCESS-NRI Intake Catalog, you will need to be a member of **all** 
   these projects. See the `NCI documentation for how to join projects <https://opus.nci.org.au/display/Help/How+to+connect+to+a+project>`_.

   .. attention::
      ACCESS-NRI Intake Catalog users will only be able to load data from projects that they have access to.

#. **Access to the** :code:`xp65` **or** :code:`hh5` **projects**: these projects provide public 
   analysis environments in which the ACCESS-NRI Intake Catalog is installed (along with many other useful 
   packages). Alternatively, you can install the ACCESS-NRI Intake Catalog into your own environment.

   .. warning::
      The ACCESS-NRI Intake Catalog is actually not yet installed in the :code:`hh5` environments, so for now 
      you'll have to use the :code:`xp65` environment.


Installation and getting started
^^^^^^^^^^^^^
#. Clone the **MED-live-diagnostics** repository found at https://github.com/ACCESS-NRI/MED-live-diagnostics to an accessbile project location on Gadi.

#. Log into to `ARE <are.nci.org.au>`_ and start a JupyterLab instance with the following minimum recommended settings:

   +-----------------------+-------------------------------------+
   | Compute Size          | Medium (4 cpus, 18G mem)            |  
   +-----------------------+-------------------------------------+
   | Storage               | All projects you wish to access     |     
   +-----------------------+-------------------------------------+
   
   Advanced Options:
   
   +-----------------------+-------------------------------------+
   | Module directories    | /g/data/xp65/public/modules         |
   +-----------------------+-------------------------------------+
   | Modules               | conda/access-med                    |
   +-----------------------+-------------------------------------+

#. You should now have an ARE JupyterLab instance running using the `ACCESS-NRI MED Conda environment <https://github.com/ACCESS-NRI/MED-condaenv>`_.

4. Open the one of tutorial notebooks from the `examples <https://github.com/ACCESS-NRI/MED-live-diagnostics/tree/main/examples>`_, update the path to your MLD clone on Gadi and get started! 


ACCESS-NRI Model Diagnostics reference
======================================

med_diagnostics.data
^^^^^^^^^^^^^

.. automodule:: med_diagnostics.data
   :members:
   :undoc-members:
   :show-inheritance:

med_diagnostics.diagnostics
^^^^^^^^^^^^^

.. automodule:: med_diagnostics.diagnostics
   :members:
   :undoc-members:
   :show-inheritance:

med_diagnostics.session
^^^^^^^^^^^^^

.. automodule:: med_diagnostics.session
   :members:
   :undoc-members:
   :show-inheritance:

med_diagnostics.ui
^^^^^^^^^^^^^

.. automodule:: med_diagnostics.ui
   :members:
   :undoc-members:
   :show-inheritance:
