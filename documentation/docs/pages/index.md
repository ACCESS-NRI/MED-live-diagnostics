# ACCESS-NRI Model Live Diagnostics

Welcome to the documentation and reference guide for the [ACCESS-NRI](https://www.access-nri.org.au/) Model Live Diagnostics (MLD) package, developed by the Model Evaluation and Diagnostics (MED) team. The package is installed as `med-diagnostics` and imported in Python as `med_diagnostics`. Model Live Diagnostics provides practical Jupyter-based tools for interactive monitoring and diagnostic analysis of currently running, or "live", ACCESS climate models on the Australian NCI supercomputer Gadi.

The framework is intended for use in the [Australian Research Environment (ARE)](https://are.nci.org.au/) and is still under active development.

## What does this package do?

Model Live Diagnostics helps the ACCESS modelling community check, monitor, visualise, and evaluate the behaviour and progress of live [ACCESS models](https://docs.access-hive.org.au/models/access_models/) on [Gadi](https://nci.org.au/our-systems/hpc-systems). It can also load, visualise, and compare legacy ACCESS model data with the selected live user model. It supports ACCESS-CM2, ACCESS-CM3, ACCESS-OM2, ACCESS-OM3, ACCESS-ESM1.5, ACCESS-ESM1.6, ACCESS-AM3 and MOM6 output.

A session opens an interactive interface in your notebook with four collapsible sections:

- **Load and plot user data.** Builds an Intake catalogue (a searchable data index) from your live model output, so you can load any of its datasets and plot a variable as a line plot, heatmap, or an interactive heatmap over time. Sliders let you slice through extra dimensions such as ocean depth.

- **Load and plot reference models.** Loads any model of the same type from the [ACCESS-NRI Intake Catalogue](https://github.com/ACCESS-NRI/access-nri-intake-catalog) and plots its data with the same controls.
- **Overlay user and reference models.** Overlays line plots or shows heatmaps side by side for your run and as many reference models as you like, and can plot the difference between them to highlight discrepancies.
- **Run analysis recipes.** Runs ready-made analyses on your data, such as the Niño 3.4 index or area-weighted regional mean timeseries, or apply your own custom analyses.

## Quick-start guide

The framework only works on Gadi, and the interface requires an ARE JupyterLab session.

### Prerequisites

Before starting, make sure you:

1. **Have an NCI account.** See the [NCI account documentation](https://opus.nci.org.au/display/Help/How+to+create+an+NCI+user+account). You will also need to join a project with a compute allocation.
2. **Can access the projects containing your model data.** The [ACCESS-NRI Intake Catalog](https://github.com/ACCESS-NRI/access-nri-intake-catalog/tree/main) references data across multiple Gadi projects. See the [supported project list](https://github.com/ACCESS-NRI/access-nri-intake-catalog/blob/main/docs/project_list.rst) and the [NCI project access documentation](https://opus.nci.org.au/display/Help/How+to+connect+to+a+project).
3. **Are a member of the ACCESS-NRI `xp65` project** to access the [ACCESS-NRI analysis3 environment](https://docs.access-hive.org.au/getting_started/environments/).

### Start an ARE JupyterLab session

1. Log in to [ARE](https://are.nci.org.au) and start a JupyterLab instance with access to the [ACCESS-NRI analysis3 conda environment](https://docs.access-hive.org.au/getting_started/environments/). Use the following settings:

    | Setting | Recommendation |
    | --- | --- |
    | Compute size | XX-Large (28 CPUs, 126 GB memory) |
    | Storage | E.g. `gdata/xp65+gdata/ik11` are required for the getting started tutorial |

    In **Advanced options**, use:

    | Setting | Value |
    | --- | --- |
    | Module directories | `/g/data/xp65/public/modules` |
    | Modules | `conda/analysis3` |

2. Follow the [Getting started tutorial](tutorials/getting_started_tutorial.md) to begin a Model Live Diagnostics session.

### Install the package directly

The package is pre-installed in the ACCESS-NRI analysis3 environment. Alternatively, install it from the [access-nri conda channel](https://anaconda.org/accessnri/med-diagnostics) or [PyPI](https://pypi.org/project/med-diagnostics/):

=== "conda"

    ```bash
    conda install -c accessnri med-diagnostics
    ```

=== "PyPI"

    ```bash
    pip install med-diagnostics
    ```

---
The package is still a work in progress. We value your feedback, especially in the form of reporting issues/bugs or suggesting ways to improve the framework. To do so, please open an issue [here](https://github.com/ACCESS-NRI/MED-live-diagnostics/issues).

---

[Next: Tutorials :material-arrow-right:](tutorials/index.md){ .md-button }
