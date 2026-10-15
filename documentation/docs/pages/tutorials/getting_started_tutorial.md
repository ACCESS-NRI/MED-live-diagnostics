# Getting started

This tutorial walks through using Model Live Diagnostics (MLD) to:

- Load live and reference model runs
- Plot model data across various axes and slices
- Compare live and reference model data
- Run in-built analysis recipes on live models

------------------

### 1. Start an ARE session

Start an [ARE JupyterLab session](https://are.nci.org.au/pun/sys/dashboard/batch_connect/sys/jupyter/ncigadi/session_contexts/new) using the ACCESS-NRI MED conda environment (`conda/access-med`), which has the `med_diagnostics` package pre-installed.
To follow this tutorial, you need to be a member of these NCI projects, and add them to the ARE **Storage** setting (e.g. `gdata/xp65+gdata/ik11`):

- `xp65`: For the ACCESS-NRI MED conda environment and the [ACCESS-NRI Intake Catalogue](https://github.com/ACCESS-NRI/access-nri-intake-catalog).
- `ik11`: For the ACCESS-OM2 reference model runs used in this tutorial.
- The project containing your model output, if you want to use it for this tutorial. (e.g. `gdata/<project>` or `scratch/<project>`).

### 2. Start a live model diagnostic session

In a new notebook, import the `med_diagnostics` package.

```python
import med_diagnostics
```

Start a session by running a cell with the following command:

```python
session = med_diagnostics.session.CreateModelDiagnosticsSession()
```

This starts the model diagnostics session, which initially should look like:

![Session start](../../assets/tutorials/tutorial_2_session_start.png)

Now we are ready to load our model data and begin analysing it.

### 3. Monitor your own run

In the start section, enter the path to your live model output, select its model type, and click <span style="color:green">"Start Session"</span>. If you want to use the model used in this tutorial, enter the model path below and select "OM2" from the model type dropdown.

```
/g/data/ik11/outputs/access-om2/1deg_jra55_iaf_omip2spunup_cycle41
```

![User session start](../../assets/tutorials/tutorial_3_session_start_user.png)

The start section collapses and four collapsible sections appear:

- **Load and plot user data** (Section 3)
- **Load and plot reference models** (Section 4)
- **Overlay user and reference models** (Section 5)
- **Run analysis recipes** (Section 6)

!!! tip
    This tutorial covers the sections in order, but once the catalogue is built you can use them in any order.

#### 3.1. Loading and plotting user data

i) The **Load and plot user data** section shows the <span style="color:orange">catalog</span>, <span style="color:lightblue">status</span> and <span style="color:darkred">warning</span> information boxes. While MLD builds an intake catalogue of your live model output, the session summary and the following <span style="color:lightblue">status</span> message are shown. Depending on the size of the output, this can take several minutes. A session summary is printed above the interface, including the Dask cluster address (e.g. /proxy/8787/status). Add this to the "Dask Dashboard URL" in the JupyterLab left panel to monitor data loading.

![Session summary](../../assets/tutorials/tutorial_3-1_session_summary.png)

ii) Once the catalogue is built, the <span style="color:lightblue">status</span> message updates and the <span style="color:orange">catalog</span> box shows the date and time of the last catalogue build.

![Status message update](../../assets/tutorials/tutorial_3-1_catalog_built.png)

iii) The dropdown lists every dataset in your model output. Select the dataset you want to monitor, choose how many years to load (see the tip below), and click "Load dataset".

![Available datasets dropdown](../../assets/tutorials/tutorial_3-1_dataset_dropdown.png)

!!! tip "Choosing how many years to load"
    Next to each dataset dropdown are the **Years to load** controls. Loading fewer years is the main way to keep load times and memory use down.

    - **Most recent**: load the last *N* years of output (the default, *N* = 10).
    - **First**: load the first *N* years of output.
    - **All years**: load every file in the dataset. The year box is disabled in this mode. This option may take significantly longer to load a dataset. 

    The text beside the button shows how many files and which years your selection will load, e.g. "Loads 10 of 120 files, 1991–2000". The user dataset is shared by all sections, so loading it in one section loads it (and its year selection) in the others too.

Once the dataset loads, the plotting controls appear. From here, you can:

- **Select a variable**: choose a model variable from the dropdown.
- **Choose a plot type**: Line, Heatmap or Animation. Datasets with fewer dimensions may only support line plots.
- **Toggle variable names**: use the "Display Variable Long Names" checkbox to show long or short names, if the defaults are unclear.

Then click the <span style="color:green">"Select variable and plot type"</span> button.

The axis options depend on the plot type. For a line plot, select the x-axis dimension (e.g. time); for an animated heatmap, assign dimensions to the X, Y and Z axes. Then click the <span style="color:green">"Select dimensions"</span> button.

If the variable has dimensions that aren't on an axis (e.g. ocean depth, or time), a slider appears for each so you can choose a slice. You can also type a value into the box under each slider. Depending on the dataset and plot type, there may be none. Choose your slices and click the <span style="color:green">"Plot data"</span> button to load the plot. 

![Plotting interface](../../assets/tutorials/tutorial_3-1_plot_controls.png)

![Generated plot](../../assets/tutorials/tutorial_3-1_plot.png)

Each plot has a <span style="color:darkred">"Remove Plot"</span> button beneath it, which removes that plot from the section.

!!! tip "Optional"
    Repeat this with as many datasets, variables and plot types as you like. To monitor a different dataset, select it and click "Load dataset" again.
    As your run writes new output, click <span style="color:green">"Refresh model data catalog"</span> to rebuild the catalogue, then reload your dataset to see the latest data.


### 4. Explore reference models

Reference models are existing ACCESS model runs of the selected type, found in the [ACCESS-NRI Intake Catalogue](https://github.com/ACCESS-NRI/access-nri-intake-catalog).

#### 4.1. Loading reference model data

i) The reference model dropdown lists the catalogue's runs of models related to the selected type (here, every `OM2` run). Click "Reference model information" to see a description of the selected model. Choose a reference model and click "Load reference model".

![Reference model dropdown](../../assets/tutorials/tutorial_4-1_ref_model_dropdown.png)

ii) Once the reference model loads, a second dropdown lists its datasets. Select the dataset you want to view and click "Load reference dataset".

![Reference dataset dropdown](../../assets/tutorials/tutorial_4-1_ref_dataset_dropdown.png)

#### 4.2. Plotting data

Plotting reference datasets follows the same steps outlined in section 3.1. 

![Reference data UI](../../assets/tutorials/tutorial_4-2_ref_plot_controls.png)

![Reference data plot](../../assets/tutorials/tutorial_4-2_ref_plot.png)

### 5. Comparing user and reference models
The **Overlay user and reference models** section compares your run with reference models, either as overlaid line plots or side-by-side heatmaps. It can also plot the difference between the user and reference datasets, to highlight where they differ.

i) Select the user dataset to compare in "Select user dataset", set the years to load, and click "Load dataset". If you already loaded a dataset in section 3, it is selected and loaded here automatically.

ii) Choose the variable to compare from the "Variable selection" dropdown.

iii) Select a reference model from the dropdown and click "Add reference model". If the reference model has a dataset matching your user dataset, it loads automatically; if not, the model is skipped. Repeat this to add as many reference models as you like, or click "Clear loaded data" to remove them all and start again. Then select a plot type (Line or Heatmap) and click "Select variable and plot type".

![Add reference model](../../assets/tutorials/tutorial_5_add_ref_model.png)

iv) Select the axes and choose an analysis type from the dropdown:

- **None (plot all loaded data)**: plots the datasets overlaid (or side by side for heatmaps).
- **Plot Difference (Ref. - User data)**: plots the difference between each reference dataset and the user dataset.
- **Plot All Data & Difference**: plots both the datasets and their differences.

Then click the <span style="color:green">"Select dimensions"</span> button.

![Analysis type dropdown](../../assets/tutorials/tutorial_5_analysis_type.png)

v) If the variable needs slicing, sliders appear as in section 3.2. For line plots, if the reference models cover a wider x-axis range than the user dataset (e.g. a longer time period), a "Choose how to constrain the x-axis bounds" dropdown also appears beside them:

- **Constrain to user dataset bounds**: zoom the x-axis to the range of the user dataset.
- **Constrain to min-max reference dataset bounds**: show the full range covered by all loaded datasets.

Choose your slices (and bounds, if asked) and click the <span style="color:green">"Plot data"</span> button to load the plots.

![Comparison heatmap](../../assets/tutorials/tutorial_5_comparison_heatmap.png)

![Comparison difference heatmap](../../assets/tutorials/tutorial_5_difference_heatmap.png)

### 6. Running analysis recipes
The **Run analysis recipes** section runs predefined analyses ("recipes") on your user dataset, such as the Niño 3.4 sea surface temperature anomaly (`recipe_sst_anomaly_nino34`) or a regional mean on the MOM5 grid (`recipe_regional_mean_mom5`). See [Built-in analysis recipes](built_in_recipes_tutorial.md) for what each one does and the options it takes. You can also write your own recipes; see [Adding custom analyses](adding_custom_analyses.md).

i) Select the dataset in "Select dataset to analyse", set the years to load, and click "Load dataset". If you already loaded a user dataset in section 4.1 or 4.2, it is selected here automatically.

ii) Choose a recipe from "Select analysis recipe" and click "Select recipe". A description of the recipe appears, along with inputs for its options (e.g. the variable or region to use).

![Analysis section](../../assets/tutorials/tutorial_6_analysis_section.png)

iii) Fill in the options and click "Plot data". As with the other sections, each plot has a "Remove Plot" button. To run the recipe again with different options, change them and click "Plot data" again; the new plot appears above the older ones. If a recipe fails, the error is shown in the <span style="color:darkred">warning</span> box.

![Analysis plot](../../assets/tutorials/tutorial_6_analysis_plot.png)

!!! tip "Running a suite of analyses"
    Some recipes are **suites**: one click of "Plot data" runs several analyses and adds one plot for each, in order. The status box then reads "Plots created". Each plot gets its own "Remove Plot" button, so you can remove the ones you don't need. Any recipe can be a suite, including your own (see [Running a suite of analyses](adding_custom_analyses.md#running-a-suite-of-analyses)).

### 7. End live model session

When you have finished, expand the **Start a model diagnostics session** section and click the <span style="color:darkred">"End Session"</span> button, or run:

```python
session.end_session()
```

This closes the Dask client and removes the session's sections, freeing up compute resources on Gadi. To start another session, enter a new path and model type and click <span style="color:green">"Start Session"</span>.

---

[Next: Built-in analysis recipes :material-arrow-right:](built_in_recipes_tutorial.md){ .md-button }
