# ACCESS-NRI Model Live Diagnostics

Welcome to the documentation and reference guide for the [ACCESS-NRI](https://www.access-nri.org.au/) Model Live Diagnostics (MLD) package, developed by the Model Evaluation and Diagnostics (MED) team. The package is installed as `med-diagnostics` and imported in Python as `med_diagnostics`. Model Live Diagnostics provides practical Jupyter-based tools for interactive monitoring and diagnostic analysis of currently running, or "live", ACCESS climate models on the Australian NCI supercomputer Gadi.

The framework is intended for use in the [Australian Research Environment (ARE)](https://are.nci.org.au/) and is still under active development. Please report bugs and suggestions through the [GitHub issue tracker](https://github.com/ACCESS-NRI/MED-live-diagnostics/issues).

## What does this package do?

Model Live Diagnostics helps the ACCESS modelling community check, monitor, visualise, and evaluate the behaviour and progress of live ACCESS models on [Gadi](https://nci.org.au/our-systems/hpc-systems). It can also load, visualise, and compare legacy ACCESS model data with the selected live user model. It supports ACCESS-CM2, ACCESS-CM3, ACCESS-OM2, ACCESS-OM3, ACCESS-ESM1.5, ACCESS-ESM1.6 and MOM6 output.

A session opens an interactive interface in your notebook with four collapsible sections:

- **Load and plot user data.** Builds an intake catalogue from your live model output, so you can load any of its datasets and plot a variable as a line plot, heatmap, or animation over time. Sliders let you slice through extra dimensions such as ocean depth.
- **Load and plot reference models.** Loads any model of the same type from the [ACCESS-NRI Intake Catalogue](https://github.com/ACCESS-NRI/access-nri-intake-catalog) and plots its data with the same controls.
- **Overlay user and reference models.** Overlays line plots or shows heatmaps side by side for your run and as many reference models as you like, and can plot the difference between them to highlight discrepancies.
- **Run analysis recipes.** Runs ready-made analyses on your data, such as the Niño 3.4 index, area-weighted regional mean timeseries, and the ACCESS-OM3 timeseries suites, which make a whole set of plots in one click. See [Built-in analysis recipes](../notebooks/built_in_recipes_tutorial.md).

You can also:

- **Choose how many years to load** (most recent, first, or all years) to keep load times and memory use down.
- **Write your own analysis recipes**, with their own options, plot customisations, and suites of plots, and have them appear in the interface. See [Adding custom analyses](../notebooks/adding_custom_analyses.md).
- **Work with the data directly** in Python, for example by retrieving the catalogue or a loaded dataset. See [Advanced usage](../notebooks/advanced_usage.md).

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
3. Follow the [Getting started tutorial](../notebooks/getting_started_tutorial.md) to begin a Model Live Diagnostics session.

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
