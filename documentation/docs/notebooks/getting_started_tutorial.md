# Getting started

This tutorial walks through a Model Live Diagnostics session: starting it, loading and plotting live model data, comparing it with reference models, running analysis recipes and ending the session. For an overview of what the package does, see the [Home page](../pages/index.md). The full API documentation can be found in the [API reference](../pages/api.md).

The package is still a work in progress. We value your feedback, especially in the form of reporting issues/bugs or suggesting ways to improve the framework. To do so, please open an issue [here](https://github.com/ACCESS-NRI/MED-live-diagnostics/issues).

------------------

### 0. Install and start an ARE Session
As described in the [quick-start guide](../pages/index.md#quick-start-guide) on the homepage, start an ARE JupyterLab session using the ACCESS-NRI MED conda environment (`conda/access-med`), which has the `med_diagnostics` package pre-installed.

### 1. Set up access
Import the `med_diagnostics` package.

```python
import med_diagnostics
```

### 2. Create live model session
- `model_type`: str. The type of ACCESS model. Supported values are `CM2`, `OM2`, `CM3`, `OM3`, `ESM15`, `ESM16` and `MOM6` (not case-sensitive).
- `model_path`: str. The path to the model output directory/files on Gadi.

```python
session = med_diagnostics.session.CreateModelDiagnosticsSession(
    model_type="OM2", model_path="path/to/your/live/model/data/output"
)
```

### 3. Using the interface

Running `CreateModelDiagnosticsSession()` starts a session with four collapsible sections for monitoring your model run:

- **Load and plot user data** (3.1)
- **Load and plot reference models** (3.2)
- **Overlay user and reference models** (3.3)
- **Run analysis recipes** (3.4)

#### 3.1. Loading and Plotting User Data

i) Upon startup, the <span style="color:orange">orange</span> 'catalog', <span style="color:lightblue">blue</span> 'status', and <span style="color:darkred">red</span> 'warning' information boxes will load. You will see the following session summary and <span style="color:lightblue">blue</span> status message while the new intake catalogue is being built from the live model data. Depending on the size of the model data, this can take a number of minutes. The Dask cluster address (in this case: /proxy/8787/status) can be used to monitor data retrieval by adding it to the 'Dask Dashboard URL' found in the left panel.

![Session summary](/assets/notebooks/2026tutorial_image_1.png)

ii) Once the live model data catalogue has been successfully built, the <span style="color:lightblue">blue</span> status message will update and the <span style="color:orange">orange</span> status message will report the time and date of the last live model catalogue build.

![Status message update](/assets/notebooks/2026tutorial_image_2.png)

iii) All available datasets from the selected model will be listed in the dropdown. Select the dataset you wish to monitor, choose how many years to load (see below), and click 'Load dataset'.

![Available datasets dropdown](/assets/notebooks/2026tutorial_image_3.png)

!!! tip "Choosing how many years to load"
    Next to each dataset dropdown are the **Years to load** controls. Loading fewer years is the main way to keep load times and memory use down.

    - **Most recent**: load the last *N* years of output (the default, *N* = 10). This is usually what you want when monitoring a live run.
    - **First**: load the first *N* years of output.
    - **All years**: load every file in the dataset. The year box is disabled in this mode.

    The text beside the button shows how many files and which years your selection will load, e.g. "Loads 10 of 120 files, 1991–2000". The user dataset is shared by all sections, so loading it in one section loads it (and its year selection) in the others too.

iv) Once loaded, the plotting interface will appear. From here, you can:

- Select a variable: Choose a model variable from the dropdown list.
- Choose a plot type: Select Line, Heatmap, or Animation. Note that datasets with fewer dimensions may only support line plots.
- Toggle variable names: Use the "Display Variable Long Names" switch to toggle between long and short names if the defaults are unclear.

Once these options have been selected, press the <span style="color:green">green</span> "Select variable and plot type" button.

![Plotting interface](/assets/notebooks/2026tutorial_image_4.png)

v) The UI options vary by plot type. To animate a heatmap over time, for instance, assign values to the X, Y, and Z axes as shown below. Once these options have been selected, press the <span style="color:green">green</span> "Plot data" button.

![Axis assignment](/assets/notebooks/2026tutorial_image_5.png)

vi) If your dataset includes extra dimensions (e.g., ocean depth in OM2), sliders will appear so you can slice the data. Depending on the dataset and plot type, you may need to configure zero or more slices. Once you have selected your slice configuration, press the <span style="color:green">green</span> "Confirm Slices & Plot" button, and your plot will begin to load.

![Slice configuration](/assets/notebooks/2026tutorial_image_6.png)

![Generated plot](/assets/notebooks/2026tutorial_image_7.png)

vii) Each plot has a <span style="color:darkred">red</span> "Remove Plot" button beneath it, which removes that plot from the section.

!!! tip "Optional"
    This process can be repeated with as many datasets, variables, and plot types as desired. After a plot is made, the buttons change to "Add Plot" (same variable and plot type, e.g. with different axes or slices) and "Add new plot with different variable/ plot type". To monitor a different dataset, select it and click "Load different dataset".

#### 3.2. Loading and Plotting Reference Model Data (Optional)
The live model data can be compared with any alternative/legacy ACCESS models of the same type (e.g. CM2, OM2) found within the [ACCESS-NRI Intake Catalogue](https://github.com/ACCESS-NRI/access-nri-intake-catalog).

i) The reference model dropdown menu is pre-filled with all available models of the same type from the [ACCESS-NRI Intake Catalogue](https://github.com/ACCESS-NRI/access-nri-intake-catalog) (in this example the list contains all models of type 'OM2'). Click "Reference model information" to see a description of the selected model. Select the reference model of choice and click 'Load reference model'.

![Reference model dropdown](/assets/notebooks/2026tutorial_image_8.png)

ii) Once the reference model loads, a new dropdown menu will appear displaying all of its available datasets. Select the dataset you wish to monitor and click 'Load reference dataset'.

![Reference dataset dropdown](/assets/notebooks/2026tutorial_image_9.png)

iii) Once loaded, the standard UI for selecting a variable, plot type, axes, and slices will appear, allowing you to plot the desired data.

![Reference data UI](/assets/notebooks/2026tutorial_image_10.png)

![Reference data plot](/assets/notebooks/2026tutorial_image_11.png)

!!! tip "Optional"
    This process can be repeated with as many datasets, variables, and plot types as desired. To switch to a different reference model, click "Clear reference model" and load a new one.

#### 3.3. Comparing User and Reference Models (Optional)
This section allows you to compare data by overlaying line plots or displaying heatmaps side-by-side. It also provides the option to plot the difference between the user and reference datasets to help highlight any discrepancies.

i) Select the user dataset to compare in "Select user dataset", set the years to load, and click "Load User Dataset". If you have already loaded a dataset in section 3.1, it is selected here automatically, and the button reads "Load different dataset".

ii) Choose the variable to compare from the "Variable selection" dropdown.

iii) Select a reference model from the dropdown menu and click "Add reference model". If a dataset matching your loaded user dataset exists, it will load automatically; if no match is found, the model will be skipped. You can repeat this process to add as many reference models as you like, or click "Clear loaded data" to remove them all and start again. Finally, select your preferred plot type (Line or Heatmap (grid)) and click "Select variable and plot type".

![Add reference model](/assets/notebooks/2026tutorial_image_12.png)

iv) Next, select your relevant axes and choose an analysis type from the dropdown menu. Your options are:

- None (plot all loaded data): Plots the data overlaid (or side-by-side for heatmaps).
- Plot Difference (Ref. - User data): Plots the calculated difference between the datasets.
- Plot All Data & Difference: Displays both the loaded data and the calculated differences.

Once configured, click the green "Plot data" button, and if slices are required, the slice configuration UI will show.

![Analysis type dropdown](/assets/notebooks/2026tutorial_image_13.png)

v) For line plots, if the reference models cover a wider x-axis range than the user dataset (e.g. a longer time period), you will be asked to "Choose how to constrain the x-axis bounds":

- Constrain to user dataset bounds: zoom the x-axis to the range of the user dataset.
- Constrain to min-max reference dataset bounds: show the full range covered by all loaded datasets.

Select an option and click "Plot data".

vi) Once configured, click the 'Confirm Slices & Plot' button. The selected plots will then load.

![Comparison heatmap](/assets/notebooks/2026tutorial_image_14.png)

![Comparison difference heatmap](/assets/notebooks/2026tutorial_image_15.png)

#### 3.4. Running Analysis Recipes (Optional)
The **Run analysis recipes** section runs predefined analyses ("recipes") on the loaded user dataset, such as the Niño 3.4 sea surface temperature anomaly (`recipe_sst_anomaly_nino34`) or a regional mean on the MOM5 grid (`recipe_regional_mean_mom5`).

i) Select the dataset in "Select dataset to analyse", set the years to load, and click "Load dataset". If a user dataset is already loaded, it is selected here automatically.

ii) Choose a recipe from "Select analysis recipe" and click "Select recipe". A description of the recipe will appear, along with input widgets for its options (e.g. the variable or region to use).

![Analysis section](/assets/notebooks/Analysis_section.png)

iii) Fill in the options and click "Plot data". As with the other sections, each plot has a "Remove Plot" button, and the button changes to "Add Plot" so you can run the recipe again with different options. If a recipe fails, the error is shown in the <span style="color:darkred">red</span> warning box.

!!! tip "Writing your own recipes"
    You can add your own analyses to this section. See the [Adding custom analyses](adding_custom_analyses.md) tutorial. After registering a new recipe, click "Refresh analysis recipes" to add it to the dropdown.

### 4. End live model session

```python
session.end_session()
```
