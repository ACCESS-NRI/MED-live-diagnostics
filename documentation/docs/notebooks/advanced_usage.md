# Advanced Usage

To get started with model live diagnostics, please see the [getting started tutorial](getting_started_tutorial.md). The following guide provides further information about the options available within the package.

### 1. Create live model session
- `model_type`: str (Type of ACCESS model, case-insensitive. Use one of the following):
    - CM2
    - CM3
    - OM2
    - OM3
    - ESM15
    - ESM16
    - MOM6
- `model_path`: str (Path to model output directory/files on Gadi.)

Creating a `CreateModelDiagnosticsSession()` instance triggers the following tasks in the background:

- Start a local `dask` cluster (`distributed.Client(threads_per_worker=1)`), which is used to load the model data. Its dashboard address is printed in the session summary and can be added to the 'Dask Dashboard URL' in the JupyterLab left panel to monitor data retrieval.
- Retrieve the most up-to-date nominated model data and build a new ESM datastore, using the [ACCESS-NRI intake catalog](https://github.com/ACCESS-NRI/access-nri-intake-catalog.git). N.B. This is saved as a compressed *.csv in the notebook's working directory. If a catalog already exists within the notebook's working directory, and is valid and up to date, the datastore is not overwritten. 
- Initialises the [HoloViz Panel](https://panel.holoviz.org/) widget, and creates the <span style="color:orange">orange</span> 'catalog', <span style="color:lightblue">blue</span> 'status', and <span style="color:darkred">red</span> 'warning' information boxes.

```python
import med_diagnostics

session = med_diagnostics.session.CreateModelDiagnosticsSession(
    model_type="OM2", model_path="path/to/your/live/model/data/output"
)
```

![Model Live Diagnostics widget on startup](/assets/notebooks/AdvUsage_Widget_startup.png)

### 2. Access to Data
While the UI provides a quick way to visualise your model runs, advanced users may wish to interact directly with the underlying data structures for custom analysis in their Jupyter Notebook. 

#### Retrieve the Data Catalogue
You can extract the active Intake-ESM datastore object directly from your session. 
- A convenience function to return the currently loaded live model data catalogue.
- **Returns:** An Intake catalogue containing the user's model data.
- **Return type:** `intake-esm` datastore object.

```python
datastore = session.return_model_data_catalog()
datastore
```

![Data catalogue output](/assets/notebooks/AdvUsage_catalog_output.png){ width="70%" }

#### Retrieve a loaded Dataset
You can extract the loaded dataset object directly from your session. 
- A convenience function to return the currently loaded dataset.
- **Returns:** An `xarray` dataset containing the user's model data.
- **Return type:** `xarray` dataset. 

```python
dataset = session.return_loaded_dataset()
dataset
```

![Loaded dataset output](/assets/notebooks/AdvUsage_dataset_output.png){ width="80%" }

!!! warning "Load a dataset first"
    `return_loaded_dataset()` raises an `AttributeError` if no dataset has been loaded yet. Select a dataset and click "Load dataset" in the interface before calling it.

### 3. Define a custom analysis to be performed in MLD

Please see the [Adding custom analyses](adding_custom_analyses.md) tutorial to see in detail how to add a custom analysis recipe. 

### 4. Session Management
To free up compute resources on Gadi, it is best practice to close the Dask client when you have finished your analysis.

- This safely closes the Dask client and clears all four sections of the interface to end the current `CreateModelDiagnosticsSession` instance.

```python
session.end_session()
```

### 5. Troubleshooting and UI Warnings
The interface features built-in error handling to prevent crashes from invalid visualisations or missing data. When an issue occurs or the interface automates a step, a <span style="color:darkred">red</span> warning bar will appear at the top of the UI. 

Common triggers for these warnings include:

-   **Invalid Plot Configurations:** Attempting to assign the same dimension to multiple axes, or selecting a complex plot type (like a Heatmap or Animation) for a dataset that lacks the required dimensions. In these cases, the UI will prompt you to fix the axes or automatically downgrade your selection to a Line plot.

-   **Missing Overlay Data:** When using the multiplot feature, you may load reference models that do not contain the matching dataset or the specific variable you are attempting to plot. The interface will warn you and automatically drop these incompatible models from the overlay.

-   **Automated Plotting:** If a dataset only has one viable dimension for a Line plot, the UI will briefly warn you that it is bypassing the axis selection step to generate the plot automatically.

-   **Analysis Recipe Failures** If a predefined recipe has an invalid configuration passed to it, or if there is an error in a user defined recipe, details will appear in the warning textbox in the analysis section.
 
If a plot fails to generate, review the red warning bar and adjust your dropdown selections accordingly. The warning message will clear automatically once a valid plot is successfully generated.
