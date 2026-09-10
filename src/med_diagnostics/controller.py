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

def plot_dataset(dataset, dataset_name, variable, x_axis, chosen_slices, is_ref, model_name = "User"):
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
    if "member" in sliced_data.dims:

        for mem in sliced_data.member.values:

            sliced_data[variable].sel(member=mem).plot(label=mem, x=x_axis, ax=ax)
    else:
        # Plot directly if no member dimension exists
        sliced_data[variable].plot(x=x_axis, ax=ax)

    # Add the slice information to the title, if it is sliced data
    slice_str = ", ".join(
        [
            f"{dim}: {round_slice_val(val)}"
            for dim, val in chosen_slices.items()
        ]
    )
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
        caption_text=caption_text
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
    """Applies standard Matplotlib formatting to 1D plots."""

    slice_str = ", ".join(
        [f"{dim}: {round_slice_val(val)}" for dim, val in chosen_slices.items()]
    )
    if slice_str:
        caption_text += f"\nSliced by: {slice_str}"

    if x_min is not None and x_max is not None:
        ax.set_xlim(x_min, x_max)

    fig.tight_layout()
    ax.set_title(title_text, fontsize=14)
    fig.text(
        0.1, 0.01, caption_text, wrap=True, horizontalalignment="left", fontsize=10
    )

    if multiplot_legend:
        fig.subplots_adjust(bottom=0.15, right=0.7)
        ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
    else:
        fig.subplots_adjust(bottom=0.3)
        ax.legend()

    ax.grid()
    plt.close(fig)
    return fig

def variable_toggle_change(variable_toggle, variable_dropdown, dataset):
    """Toggles the given variable dropdown options between short names and long name."""
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


def get_selected_variable(
    variable_toggle,
    variable_dropdown,
    long_names={}
):
    """Returns the internal dataset variable key regardless of display toggle state."""

    if variable_toggle.value and long_names:
        return long_names[variable_dropdown.value]
    return variable_dropdown.value


def add_to_dataset_dict(dataset_dict, model, catalog, data_to_load, user_data):
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
