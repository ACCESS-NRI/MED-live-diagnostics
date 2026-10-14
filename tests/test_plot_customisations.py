import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from med_diagnostics import plot_customisations


def init_fig_ax_data():
    """Initialise a figure and axis for testing."""
    fig, ax = plt.subplots()

    data = xr.DataArray(
        np.arange(10.0),
        dims=["time"],
        coords={"time": np.arange(10)},
        attrs={"long_name": "long name"},
    )
    return fig, ax, data


def test_shade_top_10pct():
    """Test the threshold line, shading and legend of shade_top_10pct."""
    fig, ax, data = init_fig_ax_data()

    plot_customisations.shade_top_10pct(ax, data)

    # Threshold line sits at the 90th percentile of 0..9
    line = ax.lines[0]
    assert np.allclose(line.get_ydata(), 8.1)
    assert line.get_label() == "90th percentile"

    # Shading runs from the threshold up to the peak, only where data exceeds it
    assert len(ax.collections) == 1
    verts = np.concatenate([p.vertices for p in ax.collections[0].get_paths()])
    assert np.isclose(verts[:, 1].min(), 8.1)
    assert np.isclose(verts[:, 1].max(), 9.0)
    assert verts[:, 0].min() >= 8.0

    labels = [t.get_text() for t in ax.get_legend().get_texts()]
    assert labels == ["90th percentile", "Top 10%"]
    plt.close(fig)


def test_shade_bottom_10pct():
    """Test the threshold line, shading and legend of shade_bottom_10pct."""
    fig, ax, data = init_fig_ax_data()

    plot_customisations.shade_bottom_10pct(ax, data)

    # Threshold line sits at the 10th percentile of 0..9
    line = ax.lines[0]
    assert np.allclose(line.get_ydata(), 0.9)
    assert line.get_label() == "10th percentile"

    # Shading runs from the threshold down to the trough, only where data is below it
    assert len(ax.collections) == 1
    verts = np.concatenate([p.vertices for p in ax.collections[0].get_paths()])
    assert np.isclose(verts[:, 1].max(), 0.9)
    assert np.isclose(verts[:, 1].min(), 0.0)
    assert verts[:, 0].min() <= 2.0

    labels = [t.get_text() for t in ax.get_legend().get_texts()]
    assert labels == ["10th percentile", "Bottom 10%"]
    plt.close(fig)


def test_nino_fills():
    fig, ax, data = init_fig_ax_data()
    plot_customisations.nino_fills(ax, data - 4.5)  # -4.5 to 4.5 in steps of 1

    red, blue = ax.collections  # El Niño fill first, then La Niña

    # Colours
    assert mcolors.to_hex(red.get_facecolor()[0]) == "#ff0000"
    assert mcolors.to_hex(blue.get_facecolor()[0]) == "#0000ff"

    # Each fill is a polygon; its corner points are in .vertices as (x, y) rows
    red_xy = np.concatenate([p.vertices for p in red.get_paths()])
    blue_xy = np.concatenate([p.vertices for p in blue.get_paths()])

    # Red is shaded from the +0.4 line up to the data, blue from the data down to -0.4
    assert red_xy[:, 1].min() == 0.4
    assert red_xy[:, 1].max() == 4.5
    assert blue_xy[:, 1].max() == -0.4
    assert blue_xy[:, 1].min() == -4.5

    # Shading only where the data is past the threshold: it crosses +0.4 at t=4.9 and -0.4 at t=4.1
    assert red_xy[:, 0].min() == 4.9
    assert blue_xy[:, 0].max() == 4.1
    plt.close(fig)


def test_nino_reference_lines():
    fig, ax, data = init_fig_ax_data()
    plot_customisations.nino_reference_lines(ax, data)
    assert [line.get_ydata()[0] for line in ax.lines] == [0, 0.4, -0.4]
    plt.close(fig)


def test_timeseries_plot_kwargs():
    kwargs = plot_customisations.timeseries_plot_kwargs(
        xr.DataArray([1], name="sst"), "SST", "degC"
    )
    assert kwargs["title"] == "sst"
    assert kwargs["ax_kwargs"]["ylabel"] == "SST (degC)"


def test_add_trend():
    """Test the trend is fitted against time, skipping NaNs at the ends and mid-series.

    y = 2t + 5 has a non-zero intercept, so dropping it shows. The mid-series
    gap means fitting against position instead of time gives the wrong slope.
    """
    t = np.arange(10)
    y = 2.0 * t + 5
    y[[0, 4, 5, 9]] = np.nan
    data = xr.DataArray(y, coords={"time": t})
    fig, ax = plt.subplots()

    plot_customisations.add_trend(ax, data)

    kept = [1, 2, 3, 6, 7, 8]
    np.testing.assert_allclose(ax.lines[0].get_xdata(), kept)
    np.testing.assert_allclose(ax.lines[0].get_ydata(), 2.0 * np.array(kept) + 5)
    plt.close(fig)


def test_add_trend_on_cftime_axis():
    """Test the trend works on the cftime axes model output uses."""
    time = xr.date_range("2000-01-01", periods=5, freq="YS", use_cftime=True)
    data = xr.DataArray([1.0, 2.0, 3.0, 4.0, 5.0], coords={"time": time})
    fig, ax = plt.subplots()
    # Draw the data first, as the recipes do; this sets the axis up for cftime dates
    data.plot(ax=ax)

    plot_customisations.add_trend(ax, data)

    # Yearly steps of 365 or 366 days, so the line is straight to within a leap day
    np.testing.assert_allclose(ax.lines[1].get_ydata(), data.values, atol=0.01)
    plt.close(fig)


def test_add_threshold():
    fig, ax, _ = init_fig_ax_data()
    plot_customisations.add_threshold(ax, 5)
    assert ax.lines[0].get_ydata()[0] == 5
    plt.close(fig)


def test_add_rolling_mean():
    """Test that each smoothed value sits at the centre of its window.

    Curved data is used because on a straight line a window that isn't
    centred gives the same values, just shifted sideways.
    """
    t = np.arange(10)
    data = xr.DataArray(t**2.0, coords={"time": t})
    fig, ax = plt.subplots()
    ax.plot(data["time"], data)

    plot_customisations.add_rolling_mean(ax, data, 3)

    np.testing.assert_allclose(ax.lines[1].get_xdata(), t[1:-1])
    np.testing.assert_allclose(ax.lines[1].get_ydata(), t[1:-1] ** 2 + 2 / 3)
    assert ax.lines[1].get_color() == ax.lines[0].get_color()
    plt.close(fig)


def test_add_reference_timeseries():
    fig, ax, data = init_fig_ax_data()
    plot_customisations.add_reference_timeseries(ax, {"ref": (data, 3)})
    assert len(ax.lines) == 2
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["ref"]
    plt.close(fig)
