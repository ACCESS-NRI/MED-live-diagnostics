# Diagnostics without the GUI

While the graphical interface provides a quick way to visualise your model runs, advanced users may wish to interact directly with the underlying data structures for custom analysis in their Jupyter Notebook, or switch from using the interface to using the API. 

### 1. Getting data out of a session

#### Retrieve the data catalogue
You can extract the active Intake-ESM datastore object directly from your session. 

- **Returns:** An Intake catalogue containing the user's model data.
- **Return type:** `intake-esm` datastore object.

```python
datastore = session.return_model_data_catalog()
datastore
```

![Data catalogue output](/assets/tutorials/AdvUsage_catalog_output.png){ width="70%" }

#### Retrieve a loaded dataset

You can extract the loaded dataset object directly from your session. 

- **Returns:** An `xarray` dataset containing the user's model data.
- **Return type:** `xarray` dataset. 

```python
dataset = session.return_loaded_dataset()
dataset
```

![Loaded dataset output](/assets/tutorials/AdvUsage_dataset_output.png){ width="80%" }

!!! warning "Load a dataset first"
    `return_loaded_dataset()` raises an `AttributeError` if no dataset has been loaded yet. Select a dataset and click "Load dataset" in the interface before calling it.

### 2. Using the API
Everything the interface does can also be done in code with `med_diagnostics.api`. This is useful for scripts, batch jobs, or notebooks where you want to save or customise plots yourself. No session is needed.

```python
from med_diagnostics import api
```

The API doesn't start a Dask client for you. Start one first so that catalogues build and datasets load in parallel:

```python
from distributed import Client

client = Client(threads_per_worker=1)
```

#### Load your model output
`api.build_catalog` builds a datastore of your run, the same way "Start Session" does. It is saved under `~/.med_diagnostics/catalogs` and reused next time if your output hasn't changed. A path that doesn't exist, or an unsupported model type, raises a `ValueError`.

```python
user_cat = api.build_catalog(
    "/g/data/ik11/outputs/access-om2/1deg_jra55_iaf_omip2spunup_cycle41", "OM2"
)
print(api.list_datasets(user_cat))  # dataset keys

key = "ocean.1yr.nv:2.st_edges_ocean:51.st_ocean:50.xt_ocean:360.yt_ocean:300.mean"
dataset = api.load_dataset(user_cat, key, years=5)
```

`years` loads only the most recent years of output (all years if left out). Set `from_start=True` to load the first years instead.

#### Plot a variable
`api.plot_data` picks the plot type from the axes you give it:

| Arguments | Plot |
| --- | --- |
| `x_axis` | Line plot (one line per ensemble member) |
| `x_axis`, `y_axis` | Heatmap |
| `x_axis`, `y_axis`, `animate_over` | Interactive Heatmap |

```python
fig = api.plot_data(
    dataset, "temp", x_axis="xt_ocean", y_axis="yt_ocean", slices={"st_ocean": 100}
)
```

`slices` picks the value of other dimensions to plot, using the nearest value. Dimensions you don't plot or slice use their first value. Use `dataset[variable].dims` to see which dimensions you can plot.

An interactive heatmap returns a Panel layout, so put it on the last line of its own cell:

```python
api.plot_data(dataset, "sst", x_axis="xt_ocean", y_axis="yt_ocean", animate_over="time")
```

!!! tip "Showing figures"
    Assign plots to a variable (`fig = ...`), otherwise they show twice in a notebook.

#### Compare with reference models
Load the ACCESS-NRI reference catalogue, pick a model, and add its datasets to a dictionary of references. Each reference is converted to your dataset's calendar so the two can be plotted together.

```python
ref_cat = api.load_reference_catalog("OM2")
print(api.list_datasets(ref_cat))  # reference model names

model = "1deg_jra55_iaf_omip2spunup_cycle40"  # the spin-up cycle before the user run
print(
    api.reference_metadata(ref_cat, model)
)  # description, contact, nominal_resolution, url, ...
print(api.list_datasets(ref_cat[model]))  # dataset keys for this model

# This model has the same yearly ocean dataset as the user run
references = api.add_reference("Cycle 40", ref_cat[model], key, dataset)

# Add a second model to the same dictionary
references = api.add_reference(
    "Cycle 42",
    ref_cat["1deg_jra55_iaf_omip2spunup_cycle42"],
    key,
    dataset,
    references=references,
)
```

The name you give each reference is used in the legend. A reference must have the variable you plot as well as the same key: some models share a key but hold different variables.

`api.plot_overlay` plots your dataset against the references. With only `x_axis` it overlays lines on one plot, and with `y_axis` as well it shows a grid of heatmaps on a shared colour scale.

```python
# SST over time in the central equatorial Pacific
fig = api.plot_overlay(
    dataset,
    "sst",
    references,
    x_axis="time",
    slices={"xt_ocean": -150, "yt_ocean": 0},
    constrain_to_user=True,
)
# Map of each reference minus the user SST
fig = api.plot_overlay(
    dataset, "sst", references, x_axis="xt_ocean", y_axis="yt_ocean", difference=True
)
```

`difference=True` plots each reference minus your data. For line plots, `constrain_to_user=True` limits the x-axis to the range of your data. Here the references cover 1958–2018 but only the last 5 years of the user run were loaded.

#### Run analysis recipes
The same recipes as the **Run analysis recipes** section are available. A recipe can be given as its function or by its label from `list_recipes`.

```python
print(list(api.list_recipes()))  # recipe labels
print(
    api.recipe_options("Niño 3.4 index for sea surface temperature", dataset)
)  # arguments and choices

figs = api.run_recipe(dataset, "Niño 3.4 index for sea surface temperature", var="sst")
```

`run_recipe` returns a list with one figure per result, since a [suite](adding_custom_analyses.md#running-a-suite-of-analyses) can make several plots. Custom recipes can be run directly, or registered with `api.register_analysis` (the same as `analysis.register_analysis`) so they appear in `list_recipes` and the interface. See [Adding custom analyses](adding_custom_analyses.md) for how to write one.

```python
def recipe_global_mean_temp(ds):
    variable = "temp"

    other_dims = [d for d in ds[variable].dims if d != "time"]
    return ds[variable].mean(other_dims)


figs = api.run_recipe(dataset, recipe_global_mean_temp)
api.register_analysis(
    recipe_global_mean_temp
)  # now listed as "Custom: recipe_global_mean_temp"
```

A recipe without a docstring is listed under its function name. With a docstring, its first paragraph is used instead.

See the [API reference](../api.md#med_diagnostics.api) for every function and its arguments.

---

[Next: Built-in recipes :material-arrow-right:](../built_in_recipes.md){ .md-button }
