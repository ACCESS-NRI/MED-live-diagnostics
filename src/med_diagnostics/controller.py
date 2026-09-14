import panel as pn
import matplotlib.pyplot as plt
import datetime

from med_diagnostics import data
from IPython.display import display
import hvplot.xarray  # type: ignore #For creating interactive plots
import xarray as xr


def update_textbox_text(textbox_obj, text):
    """
    Takes any Panel text object (e.g., pn.widgets.StaticText) and updates
    it with the defined text value.
    """
    textbox_obj.value = str(text)


def get_current_time():
    """
    Get current time.

    Returns
    ----------
    str
        Current time in "%Y-%m-%d %H:%M:%S" format.
    """

    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def round_slice_val(val):
    """
    Round numerical values to a maximum of 2 decimal places for display.

    Parameters
    ----------
    val : int, float, or str
        The value to be rounded.

    Returns
    -------
    str
        The rounded value as a string, or the original value as a string
        if it cannot be converted to a float.
    """

    try:
        return str(round(float(val), 2))
    except (ValueError, TypeError):
        return str(val)


def plot_dataset(dataset, dataset_name, variable, x_axis, chosen_slices, is_ref, model_name="User", plot_type = "Line", y_axis = None):
    """
    Plot 2D time-series from model data. Private.

    Parameters
    ----------
    variable : str
        Model data variable as selected from panel dropdown.
    Returns
    ----------
    self.fig : matplotlib.pyplot.figure()
    """
    # Plot primary (user) model data
    fig, ax = plt.subplots(figsize=[8, 4])

    # Slice the dataset if the user has selected any
    sliced_data = dataset.sel(**chosen_slices, method="nearest")

    # Plot all model variants if multiple exist
    if "member" in sliced_data.dims and not plot_type == "Heatmap":

        for mem in sliced_data.member.values:

            sliced_data[variable].sel(member=mem).plot(label=mem, x=x_axis, ax=ax)
    else:
        if plot_type == "Heatmap":
            sliced_data[variable].plot(x=x_axis, y=y_axis, ax=ax)
        else:
            sliced_data[variable].plot(x=x_axis, ax=ax)

    # Add the slice information to the title, if it is sliced data
    slice_str = ", ".join([f"{dim}: {round_slice_val(val)}" for dim, val in chosen_slices.items()])
    title_text = sliced_data[variable].attrs.get("long_name", variable)

    if is_ref:
        caption_text = "Model: " + model_name + "\nDataset: " + dataset_name
    else:
        caption_text = "User model \nDataset: " + dataset_name

    return apply_standard_plot_formatting(
        fig=fig,
        ax=ax,
        title_text=title_text,
        chosen_slices=chosen_slices,
        caption_text=caption_text,
    )


def apply_standard_plot_formatting(
    fig,
    ax,
    title_text,
    chosen_slices,
    caption_text,
    x_min=None,
    x_max=None,
    multiplot_legend=False,
):
    """
    Apply standard Matplotlib formatting, layout adjustments, and annotations to 1D plots.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The Matplotlib figure object to format.
    ax : matplotlib.axes.Axes
        The axis object associated with the plot.
    title_text : str
        The main title for the plot.
    chosen_slices : dict
        A dictionary mapping dimension names to their selected coordinate slice values.
    caption_text : str
        The base caption or metadata string to display beneath the plot.
    x_min : float, optional
        The lower limit for the x-axis. Defaults to None.
    x_max : float, optional
        The upper limit for the x-axis. Defaults to None.
    multiplot_legend : bool, optional
        If True, adjusts margins and positions the legend outside the plot area
        for multi-model comparisons. Defaults to False.

    Returns
    -------
    matplotlib.figure.Figure
        The formatted Matplotlib figure object.
    """

    slice_str = ", ".join([f"{dim}: {round_slice_val(val)}" for dim, val in chosen_slices.items()])
    if slice_str:
        caption_text += f"\nSliced by: {slice_str}"

    if x_min is not None and x_max is not None:
        ax.set_xlim(x_min, x_max)

    fig.tight_layout()
    ax.set_title(title_text, fontsize=14)
    fig.text(0.1, 0.01, caption_text, wrap=True, horizontalalignment="left", fontsize=10)

    if multiplot_legend:
        fig.subplots_adjust(bottom=0.15, right=0.7)
        ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
    else:
        fig.subplots_adjust(bottom=0.3)
        ax.legend()

    ax.grid()
    return fig


def variable_toggle_change(variable_toggle, variable_dropdown, dataset):
    """
    Toggle a variable selection dropdown between descriptive long names and short keys.

    Inspects the attributes of datasets variables, builds a lookup mapping of long
    names to standard keys, and updates the dropdown options and toggle button label
    based on the toggle state.

    Parameters
    ----------
    variable_toggle : panel.widgets.Toggle
        The toggle widget controlling the name display state.
    variable_dropdown : panel.widgets.Select or panel.widgets.AutocompleteInput
        The dropdown widget displaying variable options.
    dataset : xarray.Dataset
        The active dataset containing variables to inspect.

    Returns
    -------
    dict
        A mapping dictionary linking variable long names to their internal keys.
    """

    long_names = {}
    for var in dataset.keys():
        long_names[(dataset[var].attrs.get("long_name", var))] = var

    if variable_toggle.value:
        variable_dropdown.options = list(long_names.keys())
        variable_toggle.label = "Display Variable Short Names"
    else:
        variable_dropdown.options = list(dataset.keys())
        variable_toggle.label = "Display Variable Long Names"

    return long_names


def get_selected_variable(variable_toggle, variable_dropdown, long_names={}):
    """
    Resolve the internal dataset variable key regardless of the display toggle state.

    Parameters
    ----------
    variable_toggle : panel.widgets.Toggle
        The toggle widget indicating whether long names are currently active.
    variable_dropdown : panel.widgets.Select
        The dropdown widget containing the currently selected variable option.
    long_names : dict, optional
        A mapping dictionary linking long display names to internal keys. Defaults to {}.

    Returns
    -------
    str
        The resolved internal dataset variable key.
    """

    if variable_toggle.value and long_names:
        return long_names[variable_dropdown.value]
    return variable_dropdown.value


def add_to_dataset_dict(dataset_dict, model, catalog, data_to_load, user_data):
    """
    Load a dataset from an intake catalog, align its calendar with a reference user dataset, and store it.

    Parameters
    ----------
    dataset_dict : dict
        The target dictionary storing loaded datasets keyed by model name.
    model : str
        The dictionary key representing the model name.
    catalog : intake.catalog.Catalog
        The data catalog to query.
    data_to_load : dict
        Parameters or identifiers required by the data loader to retrieve the specific asset.
    user_data : xarray.Dataset
        The primary user dataset used as a reference benchmark for calendar alignment.

    Returns
    -------
    dict
        The updated dataset dictionary containing the newly loaded and calendar-aligned dataset.
    """

    dataset = data._build_data_object(catalog, data_to_load)

    # Align calendars to prevent crashes
    if "time" in user_data.coords and "time" in dataset.coords:
        # Extract the target calendar from the user dataset
        user_index = user_data.indexes.get("time")
        target_cal = user_index.calendar if isinstance(user_index, xr.CFTimeIndex) else "standard"

        # Extract the calendar from the newly loaded reference dataset
        ref_index = dataset.indexes.get("time")
        ref_cal = ref_index.calendar if isinstance(ref_index, xr.CFTimeIndex) else "standard"

        # Convert the reference dataset calendar if there is a mismatch
        if target_cal != ref_cal:
            dataset = dataset.convert_calendar(target_cal)

    dataset_dict.update({model: dataset})
    return dataset_dict


def get_metadata(catalog_metadata):
    """
    Format catalog metadata dictionary entries into an HTML string for UI panels.

    Parameters
    ----------
    catalog_metadata : dict or intake.catalog.base.Catalog
        A metadata dictionary or metadata container containing model attributes
        such as model name, description, resolution, and contact details.

    Returns
    -------
    str
        A formatted HTML string containing structured metadata fields.
    """

    return (
        '<div style="color: var(--jp-ui-font-color1);">'
        + "<b>Model information:</b><br>"
        + "<b>Model:   </b>"
        + str(catalog_metadata["model"])
        + "<br>"
        + "<b>Short description:   </b>"
        + str(catalog_metadata["description"])
        + "<br>"
        + "<b>Nominal resolution:   </b>"
        + str(catalog_metadata["nominal_resolution"])
        + "<br>"
        + "<b>Parent experiment:   </b>"
        + str(catalog_metadata["parent_experiment"])
        + "<br>"
        + "<b>Long description:   </b>"
        + str(catalog_metadata["long_description"])
        + "<br>"
        + "<b>Contact:   </b>"
        + str(catalog_metadata["contact"])
        + "<br>"
        + "<b>Email:   </b>"
        + str(catalog_metadata["email"])
        + "<br>"
    )


def check_plot_validity(dataset, variable, plot_type, x, y=None, z=None, has_slice_widgets=False):
    """
    Check if the plot configuration is valid and determine required slicing.

    Evaluates dataset dimensions, chosen axes, and plot types to verify
    validity, check for configuration errors, and identify any remaining
    dimensions that require user slicing.

    Parameters
    ----------
    dataset : xarray.Dataset
        The dataset containing the variable to plot.
    variable : str
        The target variable key within the dataset.
    plot_type : str
        The selected type of plot (e.g., "Line", "Heatmap", "Animation").
    x : str
        The primary axis selection.
    y : str, optional
        The secondary axis selection for multi-dimensional plots. Defaults to None.
    z : str, optional
        The tertiary (animation) axis selection. Defaults to None.
    has_slice_widgets : bool, optional
        Indicates whether slice widgets have already been initialized for this section.
        Defaults to False.

    Returns
    -------
    tuple of (bool, bool, bool, bool, list of str)
        A 5-tuple containing:
        - plot_valid : bool
          True if the configuration is valid and ready to plot.
        - requires_slice : bool
          True if unplotted dimensions require slicing widgets to be created.
        - invalid_heatmap_data : bool
          True if the plot type lacks sufficient dimensions or required axes.
        - same_axes_chosen : bool
          True if duplicate axes were selected.
        - remaining_dims : list of str
          List of unplotted dimensions remaining in the dataset.
    """

    plot_valid = True
    requires_slice = False
    invalid_heatmap_data = False
    same_axes_chosen = False

    heatmaps = ["Heatmap", "Heatmap (grid)"]

    if not x:
        plot_valid = False
        return plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, []

    # 1. Build chosen_axes first so we can filter dimensions
    if plot_type == "Animation":
        chosen_axes = (x, y, z)
    elif plot_type in heatmaps:
        chosen_axes = (x, y)
    elif plot_type == "Heatmap (grid)":
        chosen_axes = (x, y)
    else:
        chosen_axes = (x,)

    dim_sizes = dataset[variable].sizes
    viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != "nv"]
    remaining_dims = [dim for dim in viable_dims if dim not in chosen_axes]

    # If there are dimensions remaining and no slice widgets exist yet
    if len(remaining_dims) > 0 and not has_slice_widgets:
        plot_valid = False
        requires_slice = True

    # If the dataset lacks enough dimensions for the chosen plot type
    if (len(viable_dims) == 1 and plot_type in heatmaps) or (len(viable_dims) in (1, 2) and plot_type == "Animation"):
        plot_valid = False
        invalid_heatmap_data = True
    elif (plot_type in heatmaps and not y) or (plot_type == "Animation" and not (y and z)):
        plot_valid = False
        invalid_heatmap_data = True
    elif len(set(chosen_axes)) != len(chosen_axes):
        plot_valid = False
        same_axes_chosen = True

    return plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, remaining_dims

def plot_animation(dataset, dataset_name, variable, chosen_slices, x_axis, y_axis, z_axis, is_ref = False):
    """
    Generate an interactive animated 2D quadmesh plot with a scrubber widget.

    Parameters
    ----------
    dataset : xarray.Dataset
        The dataset containing the variable to plot.
    dataset_name : str
        The name of the dataset, used to populate the caption.
    variable : str
        The data variable to plot.
    chosen_slices : dict
        A dictionary of dimension-value pairs used to slice the dataset prior to plotting.
    x_axis : str
        The coordinate to use for the x-axis.
    y_axis : str
        The coordinate to use for the y-axis.
    z_axis : str
        The coordinate to animate over (used for the groupby scrubber widget).
    is_ref : bool, optional
        Flag indicating whether the dataset is a reference model. Defaults to False.

    Returns
    -------
    panel.Column
        A Panel column layout containing the interactive hvplot object and an HTML caption pane.
    """

    data = dataset.sel(**chosen_slices, method="nearest")
    plot_dataset = data[variable].load()

    # get the min and max variable values so that the heatmap is consistent for the whole animation
    vmin = float(plot_dataset.min())
    vmax = float(plot_dataset.max())

    # Assign coordinates if they are missing, necessary for SeaIce datasets
    if x_axis not in plot_dataset.coords:
        plot_dataset = plot_dataset.assign_coords({x_axis: range(plot_dataset.sizes[x_axis])})
    if y_axis not in plot_dataset.coords:
        plot_dataset = plot_dataset.assign_coords({y_axis: range(plot_dataset.sizes[y_axis])})

    plot = plot_dataset.hvplot.quadmesh(
        x=x_axis,
        y=y_axis,
        groupby=z_axis,
        dynamic=True,
        rasterize=True,
        widget_type="scrubber",
        widget_location="bottom",
        clim=(vmin, vmax),
        cmap="viridis",
        width=1200,
        height=600,
    )

    # Build caption string
    variable_text = plot_dataset.attrs.get("long_name", variable)
    slice_str = ", ".join([f"{dim}: {round_slice_val(val)}" for dim, val in chosen_slices.items()])
    caption_text = "Variable: " + variable_text + "<br>User model<br>Dataset: " + dataset_name
    if slice_str:
        caption_text += f"<br>Sliced by: {slice_str}"

    caption_pane = pn.pane.HTML(
        f"<div style='font-size: 12px; margin-left: 10%; margin-top: 10px;'>{caption_text}</div>"
    )
    # Return a Column with the plot on top and the caption underneath
    return pn.Column(pn.panel(plot), caption_pane)


def plot_multiplot_dataset(
    dataset,
    variable,
    ref_dict,
    chosen_slices,
    x_axis,
    x_min,
    x_max,
    plot_diff = False
):
    """
    Plot 2D time-series overlaying the user model and selected reference models. Private.

    Parameters
    ----------
    variable : str
        Model data variable as selected from panel dropdown.
    x_axis : str
        X-axis as selected from the panel dropdown.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The constructed figure containing the overlaid plots.
    """

    fig, ax = plt.subplots(figsize=[8, 4])

    # Slice user data
    sliced_user_data = dataset.sel(**chosen_slices, method="nearest")

    # Only plot the baseline user data as a black line if we are NOT doing a difference plot
    if not plot_diff:
        sliced_user_data[variable].plot(label="User dataset", x=x_axis, ax=ax, linewidth=2, color="black")

    # Loop through the dictionary adding each reference dataset
    for model_key, ref_dataset in ref_dict.items():

        # Apply slices if those dimensions exist in the reference dataset
        valid_slices = {dim: val for dim, val in chosen_slices.items() if dim in ref_dataset.dims}
        sliced_ref_data = ref_dataset.sel(**valid_slices, method="nearest")

        # Determine the data to plot based on the diff flag
        if plot_diff:
            plot_data = sliced_ref_data - sliced_user_data
        else:
            plot_data = sliced_ref_data

        # Plot all model variants if multiple exist
        if "member" in plot_data.dims:
            for mem in plot_data.member.values:
                plot_data[variable].sel(member=mem, method="nearest").plot(
                    label=f"{model_key} (mem: {mem})", x=x_axis, ax=ax
                )
        else:
            # Plot directly if no member dimension exists
            plot_data[variable].plot(label=model_key, x=x_axis, ax=ax)

    # Set title and add horizontal zero-line for difference plots
    base_title = sliced_user_data[variable].attrs.get("long_name", variable)
    if plot_diff:
        title_text = f"Δ {base_title} (Ref. - User data)"
        ax.axhline(0, color="k")  # horizontal line at 0
    else:
        title_text = base_title

    ax.set_xlim(x_min, x_max)

    return apply_standard_plot_formatting(
        fig=fig,
        ax=ax,
        title_text=title_text,
        chosen_slices=chosen_slices,
        caption_text="",
    )

def plot_multiplot_heatmap_dataset(dataset, variable, ref_dict, chosen_slices, x_axis, y_axis, plot_diff=False):
    # get the number of reference variables, to calculate the grid size
    num_refs = len(ref_dict)
    total_plots = 1 + num_refs

    # calculate grid dimensions
    ncols = 2 if total_plots > 1 else 1
    nrows = (total_plots + 1) // 2

    # Slice user data
    sliced_user_data = dataset.sel(**chosen_slices, method="nearest")

    # FIX: Ensure user data is 2D for heatmap plotting!
    if "member" in sliced_user_data.dims:
        sliced_user_data = sliced_user_data.isel(member=0)

    global_vmin = float(sliced_user_data[variable].min())
    global_vmax = float(sliced_user_data[variable].max())

    # Need to check min and max for given variable to keep colour consistent
    for ref_ds in ref_dict.values():
        valid_slices = {dim: val for dim, val in chosen_slices.items() if dim in ref_ds.dims}
        sliced_ref = ref_ds.sel(**valid_slices, method="nearest")

        # Ensure ref data is also 2D for the min/max calculation!
        if "member" in sliced_ref.dims:
            sliced_ref = sliced_ref.isel(member=0)

        # Calculate diff if needed
        plot_data = (sliced_ref - sliced_user_data) if plot_diff else sliced_ref

        # Calculate bounds using plot_data
        global_vmin = min(global_vmin, float(plot_data[variable].min()))
        global_vmax = max(global_vmax, float(plot_data[variable].max()))

    # Create grid
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=[6 * ncols, 4 * nrows])
    axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]

    # Plot User Data
    sliced_user_data[variable].plot(
        x=x_axis,
        y=y_axis,
        ax=axes_flat[0],
        vmin=global_vmin,
        vmax=global_vmax,
        cmap="viridis",
        cbar_kwargs={"label": variable},
    )

    # If the user data had members, note that we are only showing the first one
    user_member_title = f" (mem: {dataset.member.values[0]})" if "member" in dataset.dims else ""
    axes_flat[0].set_title(f"User Dataset{user_member_title}")

    ax = 1
    for model_key, dataset in ref_dict.items():
        valid_slices = {dim: val for dim, val in chosen_slices.items() if dim in dataset.dims}
        sliced_ref = dataset.sel(**valid_slices, method="nearest")

        plot_data = (sliced_ref - sliced_user_data) if plot_diff else sliced_ref
        title_prefix = "Δ " if plot_diff else ""

        # If the reference data has members, plot the first one to avoid issues
        member_title = ""
        if "member" in sliced_ref.dims:
            sliced_ref = sliced_ref.isel(member=0)
            member_title = f" (mem: {dataset.member.values[0]})"

        sliced_ref[variable].plot(
            x=x_axis,
            y=y_axis,
            ax=axes_flat[ax],
            vmin=global_vmin,
            vmax=global_vmax,
            cmap="viridis",
            cbar_kwargs={"label": variable},
        )
        axes_flat[ax].set_title(f"{title_prefix}{model_key}{member_title}")
        ax += 1

    # delete empty subplots remaining
    for i in range(total_plots, len(axes_flat)):
        fig.delaxes(axes_flat[i])

    # Add the slice information to the caption text, if it is sliced data
    slice_str = ", ".join(
        [f"{dim}: {round_slice_val(val)}" for dim, val in chosen_slices.items()]
    )
    if slice_str:
        fig.text(
            0.1,
            0.01,
            f"Sliced by: {slice_str}",
            wrap=True,
            horizontalalignment="left",
            fontsize=10,
        )
        fig.subplots_adjust(bottom=0.15, hspace=0.3)
    else:
        fig.subplots_adjust(hspace=0.3)

    return fig


def check_bounds(dataset, x_axis, ref_dict):
    """
    Calculate the absolute minimum and maximum x-axis bounds across all datasets.
    """
    # Safely extract pure Python scalars from Xarray DataArrays using .item()
    # This prevents 0D NumPy arrays from crashing Matplotlib's set_xlim
    dataset_min = dataset[x_axis].min().values[()]
    dataset_max = dataset[x_axis].max().values[()]

    global_min = dataset_min
    global_max = dataset_max
    bounds_widened = False

    # Helper to convert cftime objects into comparable chronological tuples
    def _to_time_tup(time_obj):
        obj = time_obj.item() if hasattr(time_obj, "item") else time_obj
        return (obj.year, obj.month, obj.day, obj.hour, obj.minute, obj.second)

    # Iterate through the reference datasets to find the absolute min and max
    for ref_ds in ref_dict.values():
        if x_axis in ref_ds:
            # Crucial: Apply .item() to reference bounds as well!
            ref_min = ref_ds[x_axis].min().item()
            ref_max = ref_ds[x_axis].max().item()

            try:
                # Attempt standard numerical or exact-calendar comparison first
                if ref_min < global_min:
                    global_min = ref_min
                    bounds_widened = True
                if ref_max > global_max:
                    global_max = ref_max
                    bounds_widened = True

            except TypeError:
                # Raised when cftime calendars clash, OR when comparing int/float with cftime.
                try:
                    # Fallback to tuple comparison for clashing calendars
                    if _to_time_tup(ref_min) < _to_time_tup(global_min):
                        global_min = ref_min
                        bounds_widened = True
                    if _to_time_tup(ref_max) > _to_time_tup(global_max):
                        global_max = ref_max
                        bounds_widened = True
                except AttributeError:
                    # Raised when trying to get .year from an int/float.
                    pass

    return bounds_widened, global_min, global_max, dataset_min, dataset_max
