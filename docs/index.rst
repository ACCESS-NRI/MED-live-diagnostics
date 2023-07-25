.. Model Diagnostics documentation master file, created by
   sphinx-quickstart on Thu Jul 20 12:26:45 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

ACCESS-NRI Model Diagnostics documentation
=============================================
Welcome to the documentation and reference guide for the `ACCESS-NRI <https://www.access-nri.org.au/>`_ Model Live Diagnostics package. 
The Model Live Diagnostics framework is designed to provide useful and practical Jupyter-based tools for the monitoring and diagnostic 
analyses of currently running (aka 'live') ACCESS climate models on the Australian NCI supercomputer Gadi.

This documentation aims to introduce these new tools, and support both new and existing users to get the most out of them using the 
Australia Research Environment (ARE).

The ACCESS-NRI Model Live Diagnostics package, and the tools that support it, are still a work in progress. We value your feedback, 
especially in the form of reporting issues/bugs or suggesting ways to improve the framework. To do so, please open an 
issue `here <https://github.com/ACCESS-NRI/MED-live-diagnostics/issues>`_.



.. toctree::
   :maxdepth: 2
   :hidden:



Quick-start guide
==================
The ACCESS-NRI Model Live Diagnostics framework is intended to be used in Jupyter notebooks running on Gadi. While it may be possible 
to use the framework outside of Jupyter notebooks, user experience will be impacted as it is not supported.

Prerequisites
^^^^^^^^^^^^^

In order to use MLD, you will need to have the following:

#. **An account at NCI**: see the `NCI documentation for creating an account 
   <https://opus.nci.org.au/display/Help/How+to+create+an+NCI+user+account>`_ if you don't have one. 
   Note you will need to join a project with a compute allocation. If you don't know what project is 
   appropriate you will need to seek help from your local group or IT support.

#. **Access to the projects that house the model data you're interested in**: the catalog references data 
   products across multiple projects on Gadi.  Currently, data is included from the following projects:

   .. include:: ../project_list.rst

   If you wish to be able to access all the data in the catalog, you will need to be a member of all 
   these projects. See the `NCI documentation for how to join projects 
   <https://opus.nci.org.au/display/Help/How+to+connect+to+a+project>`_.

   .. attention::

      Catalog users will only be able to load data from projects that they have access to.

#. **Access to the** :code:`xp65` **or** :code:`hh5` **projects**: these projects provide public 
   analysis environments in which the ACCESS-NRI catalog is installed (along with many other useful 
   packages). Alternatively, you can install the catalog into your own environment.

   .. warning::
      The ACCESS-NRI catalog is actually not yet installed in the :code:`hh5` environments, so for now 
      you'll have to use the :code:`xp65` environment. 

==================
med_diagnostics package reference
==================

data
----------------------------

.. automodule:: med_diagnostics.data
   :members:
   :undoc-members:
   :show-inheritance:

diagnostics
-----------------------------------

.. automodule:: med_diagnostics.diagnostics
   :members:
   :undoc-members:
   :show-inheritance:

session
-------------------------------

.. automodule:: med_diagnostics.session
   :members:
   :undoc-members:
   :show-inheritance:

ui
--------------------------

.. automodule:: med_diagnostics.ui
   :members:
   :undoc-members:
   :show-inheritance:
