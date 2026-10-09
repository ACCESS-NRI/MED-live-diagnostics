# Getting started

This tutorial walks through Model Live Diagnostics in two parts:

- **Part 1 (section 3):** start a session with reference models only, and learn the plotting controls on existing ACCESS model runs. You don't need a run of your own for this part.
- **Part 2 (section 4):** start a session on your own live model output, plot it, compare it with the reference models, and run analysis recipes.

For an overview of what the package does, see the [Home page](../pages/index.md). The full API documentation can be found in the [API reference](../pages/api.md).

The package is still a work in progress. We value your feedback, especially in the form of reporting issues/bugs or suggesting ways to improve the framework. To do so, please open an issue [here](https://github.com/ACCESS-NRI/MED-live-diagnostics/issues).

------------------

### 0. Start an ARE session
As described in the [quick-start guide](../pages/index.md#quick-start-guide) on the home page, start an ARE JupyterLab session using the ACCESS-NRI MED conda environment (`conda/access-med`), which has the `med_diagnostics` package pre-installed.

To follow this tutorial, you need to be a member of these NCI projects, and add them to the ARE **Storage** setting (e.g. `gdata/xp65+gdata/ik11`):

- `xp65`: the ACCESS-NRI MED conda environment and the [ACCESS-NRI Intake Catalogue](https://github.com/ACCESS-NRI/access-nri-intake-catalog).
- `ik11`: the ACCESS-OM2 reference model runs used in part 1.
- For part 2, the project that holds your own model output (e.g. `gdata/<project>` or `scratch/<project>`).

Other reference models are stored in other projects. See the catalogue's [supported project list](https://github.com/ACCESS-NRI/access-nri-intake-catalog/blob/main/docs/project_list.rst) and the [NCI project access documentation](https://opus.nci.org.au/display/Help/How+to+connect+to+a+project).

### 1. Import the package
In a new notebook, import the `med_diagnostics` package.

```python
import med_diagnostics
```

### 2. Create live model session
Create a session. It takes no arguments.

```python
session = med_diagnostics.session.CreateModelDiagnosticsSession()
```

This shows the **Start a model diagnostics session** section:

![Start a model diagnostics session](/assets/notebooks/2026tutorial_session_start.png)

- **Path to model output directory/files on Gadi**: enter the path to your live model output, or leave it blank to only view reference models.
- **Select model type**: choose the type of ACCESS model. Supported values are `CM2`, `CM3`, `ESM15`, `ESM16`, `MOM6`, `OM2` and `OM3`. This also sets which reference models are offered.

Click the <span style="color:green">"Start Session"</span> button. If the path doesn't exist or you don't have permission to read it, a <span style="color:darkred">warning</span> appears so you can fix the path and try again.

For part 1, leave the path blank, select `OM2`, and click "Start Session".

### 3. Part 1: Explore reference models

Reference models are existing ACCESS model runs of the selected type, found in the [ACCESS-NRI Intake Catalogue](https://github.com/ACCESS-NRI/access-nri-intake-catalog). The plotting controls here are the same ones you will use on your own run in part 2, so this is a good place to learn them.

With no path entered, the start section collapses and only the **Load and plot reference models** section appears. The <span style="color:lightblue">status</span> box in the start section reads "Session started with reference models only". A session summary is printed above the interface, including the Dask cluster address (e.g. /proxy/8787/status). Add this to the "Dask Dashboard URL" in the JupyterLab left panel to monitor data loading.

#### 3.1. Loading reference model data

i) The reference model dropdown lists every model of the selected type in the catalogue (here, every `OM2` model). Click "Reference model information" to see a description of the selected model. Choose a reference model and click "Load reference model".

![Reference model dropdown](/assets/notebooks/2026tutorial_image_8.png)

ii) Once the reference model loads, a second dropdown lists its datasets. Select the dataset you want to view and click "Load reference dataset".

![Reference dataset dropdown](/assets/notebooks/2026tutorial_image_9.png)

#### 3.2. Plotting data

Plotting takes three steps: choose what to plot, assign the axes, then choose any slices.

i) Once the dataset loads, the plotting controls appear. From here, you can:

- **Select a variable**: choose a model variable from the dropdown.
- **Choose a plot type**: Line, Heatmap or Animation. Datasets with fewer dimensions may only support line plots.
- **Toggle variable names**: use the "Display Variable Long Names" switch to show long or short names, if the defaults are unclear.

Then click the <span style="color:green">"Select variable and plot type"</span> button.

ii) The axis options depend on the plot type. For a line plot, select the x-axis dimension (e.g. time); for an animated heatmap, assign dimensions to the X, Y and Z axes. Then click the <span style="color:green">"Plot data"</span> button.

iii) If the variable has dimensions that aren't on an axis (e.g. ocean depth in OM2), sliders appear so you can choose a slice of each. Depending on the dataset and plot type, there may be none. Choose your slices and click the <span style="color:green">"Confirm Slices & Plot"</span> button to load the plot.

![Reference data UI](/assets/notebooks/2026tutorial_image_10.png)

![Reference data plot](/assets/notebooks/2026tutorial_image_11.png)

iv) Each plot has a <span style="color:darkred">"Remove Plot"</span> button beneath it, which removes that plot from the section.

!!! tip "Optional"
    Repeat this with as many datasets, variables and plot types as you like. After a plot is made, the buttons change to "Add Plot" (same variable and plot type, e.g. with different axes or slices) and "Add new plot with different variable/ plot type". To switch to a different reference model, click "Clear reference model" and load a new one.

When you are ready to move on to your own run, expand the **Start a model diagnostics session** section and click the <span style="color:darkred">"End Session"</span> button.

### 4. Part 2: Monitor your own run

In the start section, enter the path to your live model output, select its model type, and click "Start Session".

![User session start](/assets/notebooks/2026Tutorial_session_start_user.png)

The start section collapses and four collapsible sections appear:

- **Load and plot user data** (section 4.1)
- **Load and plot reference models** (works as in part 1)
- **Overlay user and reference models** (section 4.2)
- **Run analysis recipes** (section 4.3)

!!! tip
    This tutorial covers the sections in order, but once the catalogue is built you can use them in any order.

#### 4.1. Loading and plotting user data

i) The **Load and plot user data** section shows the <span style="color:orange">catalog</span>, <span style="color:lightblue">status</span> and <span style="color:darkred">warning</span> information boxes. While MLD builds an intake catalogue of your live model output, the session summary and the following <span style="color:lightblue">status</span> message are shown. Depending on the size of the output, this can take several minutes.

![Session summary](/assets/notebooks/2026tutorial_image_1.png)

ii) Once the catalogue is built, the <span style="color:lightblue">status</span> message updates and the <span style="color:orange">catalog</span> box shows the date and time of the last catalogue build.

![Status message update](/assets/notebooks/2026tutorial_image_2.png)

iii) The dropdown lists every dataset in your model output. Select the dataset you want to monitor, choose how many years to load (see the tip below), and click "Load dataset".

![Available datasets dropdown](/assets/notebooks/2026tutorial_image_3.png)

!!! tip "Choosing how many years to load"
    Next to each dataset dropdown are the **Years to load** controls. Loading fewer years is the main way to keep load times and memory use down.

    - **Most recent**: load the last *N* years of output (the default, *N* = 10). This is usually what you want when monitoring a live run.
    - **First**: load the first *N* years of output.
    - **All years**: load every file in the dataset. The year box is disabled in this mode.

    The text beside the button shows how many files and which years your selection will load, e.g. "Loads 10 of 120 files, 1991–2000". The user dataset is shared by all sections, so loading it in one section loads it (and its year selection) in the others too.

iv) Once the dataset loads, the plotting controls appear. Choosing a variable, plot type, axes and slices works exactly as in section 3.2.

![Plotting interface](/assets/notebooks/2026tutorial_image_4.png)

![Axis assignment](/assets/notebooks/2026tutorial_image_5.png)

![Slice configuration](/assets/notebooks/2026tutorial_image_6.png)

![Generated plot](/assets/notebooks/2026tutorial_image_7.png)

!!! tip "Optional"
    To monitor a different dataset, select it and click "Load different dataset".

#### 4.2. Comparing user and reference models (optional)
The **Overlay user and reference models** section compares your run with reference models, either as overlaid line plots or side-by-side heatmaps. It can also plot the difference between the user and reference datasets, to highlight where they differ.

i) Select the user dataset to compare in "Select user dataset", set the years to load, and click "Load User Dataset". If you already loaded a dataset in section 4.1, it is selected here automatically and the button reads "Load different dataset".

ii) Choose the variable to compare from the "Variable selection" dropdown.

iii) Select a reference model from the dropdown and click "Add reference model". If the reference model has a dataset matching your user dataset, it loads automatically; if not, the model is skipped. Repeat this to add as many reference models as you like, or click "Clear loaded data" to remove them all and start again. Then select a plot type (Line or Heatmap (grid)) and click "Select variable and plot type".

![Add reference model](/assets/notebooks/2026tutorial_image_12.png)

iv) Select the axes and choose an analysis type from the dropdown:

- **None (plot all loaded data)**: plots the datasets overlaid (or side by side for heatmaps).
- **Plot Difference (Ref. - User data)**: plots the difference between each reference dataset and the user dataset.
- **Plot All Data & Difference**: plots both the datasets and their differences.

Then click the <span style="color:green">"Plot data"</span> button.

![Analysis type dropdown](/assets/notebooks/2026tutorial_image_13.png)

v) For line plots, if the reference models cover a wider x-axis range than the user dataset (e.g. a longer time period), you are asked to "Choose how to constrain the x-axis bounds":

- **Constrain to user dataset bounds**: zoom the x-axis to the range of the user dataset.
- **Constrain to min-max reference dataset bounds**: show the full range covered by all loaded datasets.

Select an option and click "Plot data".

vi) If the variable needs slicing, sliders appear as in section 3.2. Choose your slices and click the <span style="color:green">"Confirm Slices & Plot"</span> button to load the plots.

![Comparison heatmap](/assets/notebooks/2026tutorial_image_14.png)

![Comparison difference heatmap](/assets/notebooks/2026tutorial_image_15.png)

#### 4.3. Running analysis recipes (optional)
The **Run analysis recipes** section runs predefined analyses ("recipes") on your user dataset, such as the Niño 3.4 sea surface temperature anomaly (`recipe_sst_anomaly_nino34`), a regional mean on the MOM5 grid (`recipe_regional_mean_mom5`), or the OM3 timeseries suites (`recipe_om3_timeseries` and `recipe_om3_timeseries_mapped`). See [Built-in analysis recipes](built_in_recipes_tutorial.md) for what each one does and the options it takes. You can also write your own recipes; see [Adding custom analyses](adding_custom_analyses.md).

i) Select the dataset in "Select dataset to analyse", set the years to load, and click "Load dataset". If you already loaded a user dataset in section 4.1 or 4.2, it is selected here automatically.

ii) Choose a recipe from "Select analysis recipe" and click "Select recipe". A description of the recipe appears, along with inputs for its options (e.g. the variable or region to use).

![Analysis section](/assets/notebooks/2026tutorial_image_16.png)

iii) Fill in the options and click "Plot data". As with the other sections, each plot has a "Remove Plot" button, and the button changes to "Add Plot" so you can run the recipe again with different options. If a recipe fails, the error is shown in the <span style="color:darkred">warning</span> box.

![Analysis plot](/assets/notebooks/2026tutorial_image_17.png)

!!! tip "Running a suite of analyses"
    Some recipes are **suites**: one click of "Plot data" runs several analyses and adds one plot for each, in order. The status box then reads "Plots created". Each plot gets its own "Remove Plot" button, so you can remove the ones you don't need. Any recipe can be a suite, including your own (see [Running a suite of analyses](adding_custom_analyses.md#running-a-suite-of-analyses)).

### 5. End live model session

When you have finished, expand the **Start a model diagnostics session** section and click the <span style="color:darkred">"End Session"</span> button, or run:

```python
session.end_session()
```

This closes the Dask client and removes the session's sections, freeing up compute resources on Gadi. To start another session, enter a new path and model type and click "Start Session".
