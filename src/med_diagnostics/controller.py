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

    #self.figure_exists = True
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

    # Add details of slice to caption, if the data is sliced
    if slice_str:
        caption_text += f"\nSliced by: {slice_str}"

    fig.tight_layout()
    ax.set_title(title_text, fontsize=14)
    fig.text(
        0.1, 0.01, caption_text, wrap=True, horizontalalignment="left", fontsize=10
    )
    fig.subplots_adjust(bottom=0.3)

    ax.grid()
    ax.legend()

    plt.close(fig)

    return fig
