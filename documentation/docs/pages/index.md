# ACCESS-NRI Model Live Diagnostics

Welcome to the documentation and reference guide for the [ACCESS-NRI](https://www.access-nri.org.au/) Model Live Diagnostics package. Model Live Diagnostics provides practical Jupyter-based tools for interactive monitoring and diagnostic analysis of currently running, or "live", ACCESS climate models on the Australian NCI supercomputer Gadi.

The framework is intended for use in the [Australian Research Environment (ARE)](https://are.nci.org.au/) and is still under active development. Please report bugs and suggestions through the [GitHub issue tracker](https://github.com/ACCESS-NRI/MED-live-diagnostics/issues).

## What does this package do?

Model Live Diagnostics helps the ACCESS modelling community check, monitor, visualise, and evaluate the behaviour and progress of live ACCESS models on [Gadi](https://nci.org.au/our-systems/hpc-systems). It can also load, visualise, and compare legacy ACCESS model data with the selected live user model.

Version 2.0 introduces:

- **Interactive animations** for visualising changes over time.
- **Multidimensional data slicing** via dynamic interface sliders.
- **Calculated difference overlays** for direct reference-versus-user model comparisons.

## Quick-start guide

The framework is intended for ARE JupyterLab sessions running on Gadi. Use outside Jupyter notebooks is not supported.

### Prerequisites

Before starting, make sure you:

1. **Have an NCI account.** See the [NCI account documentation](https://opus.nci.org.au/display/Help/How+to+create+an+NCI+user+account). You will also need to join a project with a compute allocation.
2. **Can access the projects containing your model data.** The [ACCESS-NRI Intake Catalog](https://github.com/ACCESS-NRI/access-nri-intake-catalog/tree/main) references data across multiple Gadi projects. See the [supported project list](https://github.com/ACCESS-NRI/access-nri-intake-catalog/blob/main/docs/project_list.rst) and the [NCI project access documentation](https://opus.nci.org.au/display/Help/How+to+connect+to+a+project).
3. **Are a member of the ACCESS-NRI `xp65` project** to access the [ACCESS-NRI conda environment](https://github.com/ACCESS-NRI/MED-condaenv).

### Start an ARE JupyterLab session

1. Log in to [ARE](https://are.nci.org.au) and start a JupyterLab instance. The recommended settings for these large datasets are:

   | Setting | Recommendation |
   | --- | --- |
   | Compute size | XX-Large (28 CPUs, 126 GB memory) |
   | Storage | For example, `gdata/project1+gdata/project2` |

   In **Advanced options**, use:

   | Setting | Value |
   | --- | --- |
   | Module directories | `/g/data/xp65/public/modules` |
   | Modules | `conda/access-med` |

2. Start the session with the [ACCESS-NRI MED conda environment](https://github.com/ACCESS-NRI/MED-condaenv).
3. Follow the [Getting started tutorial](../notebooks/getting_started_tutorial.ipynb) to begin a Model Live Diagnostics session.

### Install the package directly

The package is pre-installed in the ACCESS-NRI MED conda environment. Alternatively, install it from the [access-nri conda channel](https://anaconda.org/accessnri/med-diagnostics) or [PyPI](https://pypi.org/project/med-diagnostics/):

=== "conda"

    ```bash
    conda install -c accessnri med-diagnostics
    ```

=== "PyPI"

    ```bash
    pip install med-diagnostics
    ```
