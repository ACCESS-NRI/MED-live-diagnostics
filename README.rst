=========================================
ACCESS-NRI Model Live Diagnostics v2.0
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

This package is actively developed within the Model Evaluation Team at `Australia's climate simulator (ACCESS-NRI) <https://www.access-nri.org.au/>`_.
It supports ACCESS-CM2, ACCESS-CM3, ACCESS-OM2, ACCESS-OM3, ACCESS-ESM1.5, ACCESS-ESM1.6 and MOM6 output.

A session opens an interactive interface in your notebook with four collapsible sections:

* **Load and plot user data.** Builds an intake catalogue from your live model output, so you can load any of its datasets and plot a variable as a line plot, heatmap, or animation over time. Sliders let you slice through extra dimensions such as ocean depth.
* **Load and plot reference models.** Loads any model of the same type from the `ACCESS-NRI Intake Catalogue <https://github.com/ACCESS-NRI/access-nri-intake-catalog>`_ and plots its data with the same controls.
* **Overlay user and reference models.** Overlays line plots or shows heatmaps side by side for your run and as many reference models as you like, and can plot the difference between them to highlight discrepancies.
* **Run analysis recipes.** Runs ready-made analyses on your data, such as the Niño 3.4 index, area-weighted regional mean timeseries, and the ACCESS-OM3 timeseries suites, which make a whole set of plots in one click.

You can also choose how many years of output to load, write your own analysis recipes and have them appear in the interface, and work with the loaded data directly in Python.

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


The full documentation, including tutorials on getting started, the built-in analysis recipes, adding custom analyses and advanced usage, is available from `readthedocs <https://model-live-diagnostics.readthedocs.io/en/latest/>`_.
The tutorial sources are in the `documentation/docs/notebooks <https://github.com/ACCESS-NRI/MED-live-diagnostics/tree/main/documentation/docs/notebooks>`_ directory.

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