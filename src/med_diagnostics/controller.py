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
