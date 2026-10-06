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
    plot_customisations.nino_fills(ax, data - 4.5)
    assert len(ax.collections) == 2
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
    fig, ax, data = init_fig_ax_data()
    plot_customisations.add_trend(ax, data)
    # Data is already a straight line, so the trend should match it
    assert np.allclose(ax.lines[0].get_ydata(), data.values)
    plt.close(fig)


def test_add_threshold():
    fig, ax, _ = init_fig_ax_data()
    plot_customisations.add_threshold(ax, 5)
    assert ax.lines[0].get_ydata()[0] == 5
    plt.close(fig)


def test_add_rolling_mean():
    fig, ax, data = init_fig_ax_data()
    ax.plot(data["time"], data)
    plot_customisations.add_rolling_mean(ax, data, 3)
    # Centred mean of a straight line is unchanged, minus the NaN ends
    assert np.allclose(ax.lines[1].get_ydata(), data.values[1:-1])
    assert ax.lines[1].get_color() == ax.lines[0].get_color()
    plt.close(fig)


def test_add_reference_timeseries():
    fig, ax, data = init_fig_ax_data()
    plot_customisations.add_reference_timeseries(ax, {"ref": (data, 3)})
    assert len(ax.lines) == 2
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["ref"]
    plt.close(fig)
