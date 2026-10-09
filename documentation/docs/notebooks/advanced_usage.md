# Advanced Usage

To get started with model live diagnostics, please see the [getting started tutorial](getting_started_tutorial.md). The following guide provides further information about the options available within the package.

### 1. Create live model session
`CreateModelDiagnosticsSession()` takes no arguments. It shows a start section where you enter the model output path and model type, then click "Start Session" (see the [getting started tutorial](getting_started_tutorial.md#2-create-live-model-session)). The path is optional: leave it blank to start a session with reference models only. In that case no user catalogue is built, only the **Load and plot reference models** section is shown, and `session.return_model_data_catalog()` returns `None`.

Starting a session triggers the following tasks in the background:

- Start a local `dask` cluster (`distributed.LocalCluster(threads_per_worker=1)`) and client, which are used to load the model data. The dashboard address is printed in the session summary and can be added to the 'Dask Dashboard URL' in the JupyterLab left panel to monitor data retrieval.
- If a model output path was entered, retrieve the most up-to-date nominated model data and build a new ESM datastore, using the [ACCESS-NRI intake catalog](https://github.com/ACCESS-NRI/access-nri-intake-catalog.git). N.B. This is saved as a compressed *.csv in the notebook's working directory. If a catalog already exists within the notebook's working directory, and is valid and up to date, the datastore is not overwritten. 
- Initialise the [HoloViz Panel](https://panel.holoviz.org/) widget, and create the <span style="color:orange">catalog</span>, <span style="color:lightblue">status</span>, and <span style="color:darkred">warning</span> information boxes.

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

- This safely closes the Dask client and cluster and removes the session's sections of the interface, ending the current session. It does the same as the "End Session" button. You can then start a new session from the start section without creating a new `CreateModelDiagnosticsSession` instance.

```python
session.end_session()
```

### 5. Troubleshooting and UI Warnings
The interface features built-in error handling to prevent crashes from invalid visualisations or missing data. When an issue occurs or the interface automates a step, a <span style="color:darkred">warning</span> bar will appear at the top of the UI. 

Common triggers for these warnings include:

-   **Invalid Plot Configurations:** Attempting to assign the same dimension to multiple axes, or selecting a complex plot type (like a Heatmap or Animation) for a dataset that lacks the required dimensions. In these cases, the UI will prompt you to fix the axes or automatically downgrade your selection to a Line plot.

-   **Missing Overlay Data:** When using the multiplot feature, you may load reference models that do not contain the matching dataset or the specific variable you are attempting to plot. The interface will warn you and automatically drop these incompatible models from the overlay.

-   **Automated Plotting:** If a dataset only has one viable dimension for a Line plot, the UI will briefly warn you that it is bypassing the axis selection step to generate the plot automatically.

-   **Analysis Recipe Failures** If a predefined recipe has an invalid configuration passed to it, or if there is an error in a user defined recipe, details will appear in the warning textbox in the analysis section.
 
If a plot fails to generate, review the <span style="color:darkred">warning</span> bar and adjust your dropdown selections accordingly. The warning message will clear automatically once a valid plot is successfully generated.
