=========================================
ACCESS-NRI Model Live Diagnostics v0.0.1
=========================================

**Framework for interactive monitoring and diagnostic analyses of the ACCESS model suite.**

The ACCESS-NRI Model Live Diagnostics framework is designed to provide useful and practical Jupyter-based tools for interactive monitoring and diagnostic 
analyses of currently running (aka 'live') ACCESS climate models on the `Australian NCI supercomputer Gadi <https://nci.org.au/our-systems/hpc-systems>`_.

The primary purpose of the ACCESS-NRI Model Live Diagnostics package is to provide a simple, easy to use and accessible framework for the 
ACCESS modelling community to check, monitor, visualise and evaluate model behaviour and progress on currently running or ‘live’ ACCESS 
models on Gadi. In addition to monitoring a live model, the package provides the functionality to load, 
visualise and compare legacy ACCESS model data with the selected live user model.

What does this package do?
===========================

This package is currently in active development within the Model Evaluation Team at the `Australian Earth System Simulator (ACCESS-NRI) <https://www.access-nri.org.au/>`_
so watch this space for version updates containing new features, model diagnostics tools and visualisation options! 

We value your feedback, especially in the form of reporting issues/bugs or suggesting ways to improve the framework. To do so, please open an 
`issue <https://github.com/ACCESS-NRI/MED-live-diagnostics/issues>`_.

Usage / installation instructions
==================================
The med-diagnostics package is pre-installed in the Gadi `ACCESS-NRI MED conda environment <https://github.com/ACCESS-NRI/MED-condaenv>`_. To use this environment for your ARE JupyterLab session
simply set the following parameters in the ARE JupyterLab **'Advanced options'**:

+-------------------------+----------------------------------+
| Module directories      | ``/g/data/xp65/public/modules``  |
+-------------------------+----------------------------------+
| Modules                 | ``conda/access-med``             |
+-------------------------+----------------------------------+

Alternatively, the med-diagnostics package can be installed directly into your chosen conda environment on Gadi either from the 
`access-nri conda channel <https://anaconda.org/accessnri/med-diagnostics>`_ or `PyPI <https://pypi.org/project/med-diagnostics/>`_.

+-------------------------+-------------------------------------------------+
| conda                   | ``conda install -c accessnri med-diagnostics``  |
+-------------------------+-------------------------------------------------+
| PyPI                    | ``pip install med-diagnostics``                 |
+-------------------------+-------------------------------------------------+

Getting started
=========================
To use the med-diagnostics package use: ``import med_diagnostics``         


An example Jupyter notebook describing usage options can be found in the `docs/notebooks <https://github.com/ACCESS-NRI/MED-live-diagnostics/tree/main/docs/notebooks>`_ directory.

The full documentation is available from `readthedocs <https://med-live-diagnostics.readthedocs.io/en/latest/index.html>`_. 

------------

+---------------+-------------------------------------+
| Documentation | |docs|                              |
+---------------+-------------------------------------+
| Package       | |pypi| |conda|                      |
+---------------+-------------------------------------+
| License       | |license|                           |
+---------------+-------------------------------------+

.. |docs| image:: https://readthedocs.org/projects/med-live-diagnostics/badge/?version=latest
        :target: https://med-live-diagnostics.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. |pypi| image:: https://img.shields.io/pypi/v/med-diagnostics
        :target: https://pypi.org/project/med-diagnostics/
        :alt: PyPI package
        
.. |conda| image:: https://img.shields.io/conda/v/accessnri/med-diagnostics
        :target: https://anaconda.org/accessnri/med-diagnostics
        :alt: Conda package

.. |license| image:: https://img.shields.io/github/license/ACCESS-NRI/med-live-diagnostics
        :target: https://github.com/ACCESS-NRI/med-live-diagnostics/blob/main/LICENSE
        :alt: Apache-2.0 License
