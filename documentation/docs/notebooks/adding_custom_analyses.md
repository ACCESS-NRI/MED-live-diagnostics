# Adding Custom Analyses

Learn how to create and integrate custom analyses into the Model Live Diagnostics (MLD) package. By the end of this tutorial, you will know how to implement a custom analysis that automatically generates interactive UI controls based on user selection. Any analysis that can be computed with `xarray` and plotted via `matplotlib.pyplot` can be integrated into the analysis section.

### Prerequisites
Before starting, ensure you have:

* Started an MLD session in your current notebook or kernel (your custom recipes must be written in this same environment)

* Loaded a catalogue and dataset.

* Add the following imports to the top of a cell in your notebook:

```python
from med_diagnostics import analysis
import xarray as xr
```

For setup guidance, refer to the [Getting Started Tutorial](../getting_started_tutorial/).

---
## How the analysis section works
### Analysis Interface

The **Analysis** section provides a dropdown menu of predefined analyses (and user-defined analyses once they are added!). Selecting an analysis dynamically populates the interface with the required input widgets. 

<img src="/assets/notebooks/Analysis_section.png" alt="Model Live Diagnostics Analysis Section Interface" style="width: 100%; height: auto;">

## Building a custom analysis
The MLD package is designed to require minimal modifications to a typical analysis written for an `xarray.Dataset`. To add a custom analysis to the current MLD session, define a function that takes an `xarray.Dataset` as input, and returns an `xr.DataArray` as output, and register it in the session using `analysis.register_analysis(your_defined_function)`.

### The Minimum Recipe

If your analysis hardcodes specific variables or dimensions and you are happy with the default plotting style, your recipe can be a simple, standard Python function. 

```python
def recipe_global_mean_temp(ds):
    variable = "temp"

    other_dims = [d for d in ds[variable].dims if d != "time"]
    return ds[variable].mean(other_dims)


analysis.register_analysis(recipe_global_mean_temp)
```

Once your function is defined, click the **Refresh analysis recipes** button in the UI. The analysis status textbox will update to read: `"Analysis status >> Recipes refreshed (n custom)."`. 

Your new analysis will now appear in the dropdown menu, as shown below:

<img src="/assets/notebooks/Analysis_minimal_recipe_load.png" alt="Model Live Diagnostics custom analysis loaded" style="width: 80%; height: auto;">

Click **Select recipe** and then **Plot data**. The analysis will run and display using MLD's default plot settings.

<img src="/assets/notebooks/Analysis_minimal_recipe_plot.png" alt="Model Live Diagnostics custom analysis plot output" style="width: 100%; height: auto;">

!!! tip "Re-registering Recipes"
    Recipes are stored by function name. If you edit the cell and run it again, the new version replaces the old one. Click **Refresh analysis recipes** again to pick up the change.


### Building a Recipe That Takes Arguments

Let's build on the minimum recipe. What if we want to generalise it so we can easily select *any* variable or dimension to average? 

To do this, we define the function arguments using `typing.Annotated`. MLD reads these annotations to automatically understand what type of data the function expects. 

#### Defining arguments
Each argument after `ds` must be declared like this:
```python
name: Annotated[<python type>, {<metadata>}] = <default>
```

??? info "View metadata keys configuration"

    | Key | Required? | Effect |
    | :--- | :--- | :--- |
    | `"kind"` | Recommended | Chooses the widget (see the table below). If you leave it out, you get a plain text box and your recipe receives a string. |
    | `"name"` | Recommended | The label shown on the widget (e.g., `"Select Depth Slice"`). If you leave it out, the label defaults to the argument name (e.g., `lvl_dim`). |
    | `"description"` | Recommended | Shown as the widget's tooltip. *(Note: Checkboxes cannot display tooltips).* |
    | `"units"` | Optional | Appended to the widget label (e.g., `Select Depth Slice (m)`). |
    | `"choices"` | Only for `"kind": "choice"` | The list of options for the dropdown menu. |

!!! tip "UI Labels vs. Code Variables"

    `"name"` only changes what is displayed in the UI. The value is always passed to your recipe under the **argument name**, so `var: Annotated[float, {"name": "Variable", ...}]` still arrives as `var=...`

??? info "View supported `kind` values and widgets"

    | `"kind"` | Widget | Options come from | Your recipe receives |
    | :--- | :--- | :--- | :--- |
    | `"data variable"` | Dropdown | `ds.data_vars` (the variables in the loaded dataset) | `str` |
    | `"dimension"` | Dropdown | The dataset's coordinates and dimensions | `str` (or `None`) |
    | `"choice"` | Dropdown | Your `"choices"` list | Whatever the chosen item is |
    | `"float"` | Number box | — | `float` |
    | `"int"` | Whole-number box | — | `int` |
    | `"bool"` | Checkbox | — | `bool` |
    | `"str"` | Text box | — | `str` |


For example, a complete argument definition to generate a UI widget for selecting a dimension would look like this:

```python
from typing import Annotated

dim: Annotated[
    str,
    {
        "kind": "dimension",
        "name": "Select Dimension",
        "description": "Dimension to display on the x-axis, remaining dims are averaged",
    },
] = "time"
```

#### Function declaration
Here is the minimum recipe, refactored to accept any variable or dimension:

```python
from typing import Annotated


def recipe_global_mean_dynamic(
    ds: xr.Dataset,
    variable: Annotated[
        str,
        {
            "kind": "data variable",
            "name": "Select Variable",
            "description": "Variable to plot in this analysis",
        },
    ] = "temp",
    dim: Annotated[
        str,
        {
            "kind": "dimension",
            "name": "Select Dimension",
            "description": "Dimension to display on the x-axis, remaining dims averaged",
        },
    ] = "time",
) -> xr.DataArray:
    """
    Unweighted mean of any given variable along any given dimension.

    Works on any grid with a dimension and a variable.
    """

    other_dims = [d for d in ds[variable].dims if d != dim]
    return ds[variable].mean(other_dims)


analysis.register_analysis(recipe_global_mean_dynamic)
```

!!! tip "Naming your analysis with a docstring"

    Docstrings are optional, but MLD uses one if it's there:

    - The **first paragraph** becomes the dropdown label, shown as `Custom: <first paragraph>`. Without a docstring, the function name is used instead.
    - The **second paragraph** (after a blank line) is shown under the dropdown when the analysis is selected.

When you choose your new analysis using the **Recipe** dropdown, the UI will automatically generate widgets based on the `Annotated` definitions you provided for each argument. If your specified `<default>` values exist within the loaded dataset, the widgets will auto-populate with them. You can freely change these selections using the generated dropdown menus. 

Now, rather than being restricted to just a timeseries, this single function allows us to plot the average of *any* variable along *any* dimension. For example:

<img src="/assets/notebooks/Analysis_widgets_created.png" alt="Model Live Diagnostics custom analysis with dynamically generated UI widgets" style="width: 100%; height: auto;">

Click **Plot data** to view the resulting analysis:

<img src="/assets/notebooks/Analysis_widget_recipe_plot.png" alt="Plot output from the dynamically generated custom analysis" style="width: 100%; height: auto;">

??? info "View a complete example using every widget kind"

    If you want to see how every single widget type is declared in practice, you can reference this template:

    ```python
    from typing import Annotated, Literal


    def recipe_every_kind(
        ds: xr.Dataset,
        variable: Annotated[
            str, {"kind": "data variable", "description": "Variable to analyse"}
        ] = "temp",
        lon_dim: Annotated[
            str, {"kind": "dimension", "description": "Longitude coordinate"}
        ] = "xt_ocean",
        lvl_dim: Annotated[
            str | None, {"kind": "dimension", "description": "Depth coordinate, if any"}
        ] = None,
        stat: Annotated[
            str,
            {
                "kind": "choice",
                "choices": ["mean", "max", "min"],
                "description": "Statistic",
            },
        ] = "mean",
        season: Annotated[
            Literal["DJF", "MAM", "JJA", "SON"], {"kind": "choice", "description": "Season"}
        ] = "DJF",
        depth: Annotated[
            float, {"kind": "float", "units": "m", "description": "Nearest level is used"}
        ] = 0.0,
        window: Annotated[
            int, {"kind": "int", "description": "Rolling window in timesteps"}
        ] = 5,
        detrend: Annotated[
            bool, {"kind": "bool", "description": "Remove linear trend"}
        ] = False,
        label: Annotated[str, {"kind": "str", "description": "Extra title text"}] = "",
    ):
        """Shows one argument of every kind."""

        # ... Rest of your analysis logic ...
        return ds[variable]


    analysis.register_analysis(recipe_every_kind)
    ```
    This function generates the following fully populated interface:

    <img src="/assets/notebooks/Analysis_every_widget.png" alt="Model Live Diagnostics UI showing every available widget type" style="width: 100%; height: auto;">

### Customising the plot

#### Using plot_kwargs

You can ensure the plot is created exactly how you want by adding a `plot_kwargs` dictionary to your return statement. To use this feature, your function must return a two-item tuple: `(DataArray, plot_kwargs)`.

When MLD receives this dictionary, it looks for four specific keys to configure the figure and axes. Any other keys you include are passed directly to the underlying `xarray.plot()` method.

| Key | Expected Type | Effect |
| :--- | :--- | :--- |
| `"figsize"` | `tuple` | Sets the dimensions of the figure (defaults to `(6, 4)`). |
| `"title"` | `str` | Sets the plot title (defaults to the `DataArray` name). |
| `"ax_kwargs"` | `dict` | Passed to `ax.set()` to modify axis properties (e.g., `xlabel`, `ylim`, `yscale`). |
| `"customise"` | `callable` or `list` | A function (or list of functions) that accepts `(ax, data)`. These run last, allowing you to add complex matplotlib features. |

Here is an example of a recipe returning custom plot settings:

```python
from typing import Annotated


def recipe_custom_plot(
    ds: xr.Dataset, variable: Annotated[str, {"kind": "data variable"}] = "temp"
) -> tuple[xr.DataArray, dict]:
    """An example of customising a 2D heatmap plot output."""

    # Average over all non-spatial dimensions to guarantee a 2D heatmap
    dims_to_average = ds[variable].dims[:-2]
    data = ds[variable].mean(dim=dims_to_average)

    # Define custom plot settings
    plot_kwargs = {
        "figsize": (10, 6),
        "title": f"Time-Averaged Heatmap: {variable}",
        "ax_kwargs": {"xlabel": "Longitude", "ylabel": "Latitude"},
        "cmap": "magma",
        "cbar_kwargs": {"label": "Temperature (K)"},
    }

    return data, plot_kwargs


analysis.register_analysis(recipe_custom_plot)
```

And the resultant plot:

<img src="/assets/notebooks/Analysis_custom_plot_kwargs.png" alt="Model Live Diagnostics plot with custom formatting applied" style="width: 100%; height: auto;">

#### Advanced plot customisation

While `plot_kwargs` handles standard `xarray` plotting arguments, you may want to add features like shaded bands, reference lines, annotations, a second axis, or a custom legend. You can achieve this by passing custom Matplotlib functions to the `"customise"` key in your `plot_kwargs` dictionary.

Any function you pass to `"customise"` must accept exactly two positional arguments:
1. `ax`: The `matplotlib.axes.Axes` object MLD generated for the plot (note: `ax.figure` accesses the whole Figure).
2. `data`: The exact `xarray.DataArray` returned by your recipe.

They run in list order, after `ax_kwargs`, so they can override anything.

!!! tip "Compute your data once"

    The loaded dataset is lazy (backed by Dask), so your recipe's result is only calculated when it is used. If your `customise` functions also read `data` (e.g., to fit a trend line), call `.compute()` on the result before returning it. The calculation then runs once, rather than once for the plot and again for every customise function.

!!! tip "Draw extra lines with `ax.plot`, not `DataArray.plot`"

    To add another line inside a `customise` function (e.g., a rolling mean), use Matplotlib's `ax.plot(data[dim], data)` rather than `data.plot(ax=ax)`. `xarray`'s `.plot()` resets the axes title and labels, so it overwrites the `title` and `ax_kwargs` MLD has already applied. `ax.plot` leaves them alone.

The following example defines a custom function that draws a bounding box with an annotated arrow, and appends it to the base heatmap:

```python
from typing import Annotated

import xarray as xr
from matplotlib import patches

from med_diagnostics import analysis


def draw_custom_box(ax, plot_data):
    box_lon = -215.0
    box_lat = -43.8
    box_width = 4.0
    box_height = 3.3

    # Draw box
    custom_box = patches.Rectangle(
        (box_lon, box_lat),
        box_width,
        box_height,
        linewidth=2,
        edgecolor="red",
        facecolor="none",
        zorder=10,
    )
    ax.add_patch(custom_box)

    ax.annotate(
        "You can add anything\nusing 'customise' in\nplot_kwargs",
        xy=(box_lon + box_width, box_lat + (box_height / 2)),
        xytext=(box_lon + box_width + 20, box_lat + (box_height / 2) + 30),
        arrowprops={
            "facecolor": "black",
            "edgecolor": "black",
            "arrowstyle": "->",
            "lw": 2,
        },
        color="black",
        fontweight="black",
        zorder=10,
    )


def recipe_add_box(
    ds: xr.Dataset,
    variable: Annotated[str, {"kind": "data variable"}] = "temp",
) -> tuple[xr.DataArray, dict]:
    """A heatmap demonstrating how to add matplotlib annotations."""

    dims_to_average = ds[variable].dims[:-2]
    data = ds[variable].mean(dim=dims_to_average)

    # Define custom plot settings
    plot_kwargs = {
        "figsize": (8, 5),
        "title": f"Heatmap with Custom Annotation: {variable}",
        "ax_kwargs": {"xlabel": "Longitude", "ylabel": "Latitude"},
        "cmap": "magma",
        "cbar_kwargs": {"label": "Temperature (K)"},
        "customise": [draw_custom_box],
    }

    return data, plot_kwargs


analysis.register_analysis(recipe_add_box)
```


The resultant plot from adding this customisation: 

<img src="/assets/notebooks/Analysis_customise_plot.png" alt="Heatmap with a red bounding box and a custom text annotation pointing to it" style="width: 100%; height: auto;">

#### Ready-made customisations

MLD provides several built-in customisation functions for common meteorological and oceanographic visualisations in the `med_diagnostics.plot_customisations` module. These will be updated as the package is developed, and full details can be found in the [API Reference](../../api/#med_diagnostics.plot_customisations).

#### Passing extra arguments to a customise function

Because MLD strictly calls your function with exactly two arguments—`func(ax, data)`—you cannot pass additional keyword arguments directly through the MLD pipeline. 

If your custom function requires external settings (like a specific threshold value or a colour string), you must fix those arguments in advance using a `lambda` function:

```python
from typing import Annotated


def recipe_timeseries_threshold(
    ds: xr.Dataset,
    variable: Annotated[str, {"kind": "data variable"}] = "temp",
    threshold: Annotated[
        float, {"kind": "float", "description": "Draw a horizontal line at this value"}
    ] = 20.0,
) -> tuple[xr.DataArray, dict]:
    """Unweighted global mean timeseries with a threshold line."""
    other_dims = [d for d in ds[variable].dims if d != "time"]
    data = ds[variable].mean(other_dims)

    plot_kwargs = {
        "customise": [
            # `add_threshold` takes (ax, value), so the lambda passes the threshold from the widget
            lambda ax, data: plot_customisations.add_threshold(ax, value=threshold),
        ]
    }
    return data, plot_kwargs


analysis.register_analysis(recipe_timeseries_threshold)
```


??? info "View how to plot secondary axes and custom plot types"

    #### Full control: Secondary axes and custom plot types

    Because the `ax` object you receive represents the entire plot, a `customise` function can do absolutely anything Matplotlib is capable of doing. 

    **Adding secondary axes or moving legends:**
    You can easily inject secondary axes (e.g., converting Celsius to Fahrenheit) or restructure the plot layout:
    ```python
    def twin_axis_in_fahrenheit(ax, data):
        """Add a right-hand axis in °F."""
        ax.secondary_yaxis(
            "right", functions=(lambda c: c * 9 / 5 + 32, lambda f: (f - 32) * 5 / 9)
        ).set_ylabel("°F")


    def legend_outside(ax, data):
        """Move the legend outside the axes."""
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
        ax.figure.tight_layout()
    ```

    **Replacing the default plot entirely:**
    By default, MLD always draws `data.plot(...)` first. If you want a plot type that `xarray` does not natively produce (such as a custom bar chart or specialized scatter plot), your `customise` function can clear the axes and draw its own.

    *Important:* Calling `ax.clear()` also removes the title and `ax_kwargs` that MLD already applied, so you must explicitly set them again inside your custom function:
    ```python
    def bar_chart(ax, data):
        """Replace the default xarray plot with a Matplotlib bar chart."""
        
        # 1. Erase the default xarray plot MLD just drew
        ax.clear()
        
        # 2. Draw your custom plot
        ax.bar(data["time"].dt.year, data.values, color="tab:blue")
        
        # 3. Re-apply essential formatting that was cleared
        ax.set(title=data.name, xlabel="Year")
    ```
    

## Checklist

Use the checklist below to help register a new recipe to MLD:

- <input type="checkbox"> The first argument is the dataset (`ds: xr.Dataset`).
- <input type="checkbox"> Every other argument is `Annotated[type, {"kind": ...}]` with one of `"data variable"`, `"dimension"`, `"choice"`, `"float"`, `"int"`, `"bool"`, or `"str"`.
- <input type="checkbox"> Every other argument has a default value.
- <input type="checkbox"> `"choice"` arguments include a `"choices"` list in the metadata dictionary (or use a `Literal[...]` type).
- <input type="checkbox"> Optional dimensions are typed `str | None` with a default of `None`.
- <input type="checkbox"> The docstring's first line states what the recipe computes, and its second paragraph details which grid or models it targets.
- <input type="checkbox"> The function returns either a `DataArray`, or a tuple of `(DataArray, plot_kwargs)`.
- <input type="checkbox"> You have clicked **Refresh analysis recipes** in the UI after registering or updating your function.

## Contributing a recipe

Because custom recipes integrate seamlessly into the MLD pipeline, they are perfectly structured to be included as inbuilt recipes. If you have created an analysis that would be useful to others, you can submit it to the core repository, making it available for others to use.

For full details on how to format, test, and submit your code via a pull request, please see the [Contributing Recipes](../../contributing/recipes/) guide.
