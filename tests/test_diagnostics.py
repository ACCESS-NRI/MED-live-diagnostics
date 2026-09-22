import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from med_diagnostics import diagnostics


def _seasonal_dataset(
    periods=48, lat=None, lon=None, freq="MS", use_cftime=False, calendar="standard"
):
    """Build a dataset whose SST is a perfectly repeating seasonal cycle.

    Spatially uniform (broadcast across lat/lon) so any change after
    climatology-removal can only come from a deliberately injected anomaly,
    not from the base state or spatial structure.
    """
    lat = np.array([-5.0, 0.0, 5.0]) if lat is None else lat
    lon = np.array([200.0, 210.0, 220.0]) if lon is None else lon
    time = xr.date_range(
        "2000-01-01",
        periods=periods,
        freq=freq,
        calendar=calendar,
        use_cftime=use_cftime,
    )
    month = xr.DataArray(time, dims="time").dt.month.values
    seasonal = 20 + 3 * np.sin(2 * np.pi * month / 12)
    data = (
        np.broadcast_to(seasonal[:, None, None], (periods, len(lat), len(lon)))
        .astype(float)
        .copy()
    )
    ds = xr.Dataset(
        {"sst": (["time", "lat", "lon"], data)},
        coords={"time": time, "lat": lat, "lon": lon},
    )
    return ds


# --------------------------------------------------------------------------
# extract_region
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lon_values, expected_min, expected_max",
    [
        # Standard 0-360 ocean convention (e.g. ACCESS xt_ocean on many grids)
        (np.arange(0, 360, 5), 190, 240),
        # Standard -180/180 atmos convention
        (np.arange(-180, 180, 5), -170, -120),
        # Real ACCESS-OM2 tripolar-grid offset convention (-279.5 to 79.5):
        # regression case for the longitude-convention auto-detection bug -
        # a hardcoded convention silently mis-selects on this kind of grid.
        (np.arange(-279.5, 80, 1.0), -170, -120),
    ],
)
def test_extract_region_detects_longitude_convention(
    lon_values, expected_min, expected_max
):
    """extract_region() must auto-detect 0-360 vs -180/180 longitude conventions.

    A hardcoded convention gives an empty or wrong selection on the other
    grid type (this was a real bug: the function used to hardcode one
    convention, breaking depending on which model's grid was passed in).
    """
    lat = np.linspace(-20, 20, 21)
    ds = xr.Dataset(
        {"sst": (["lat", "lon"], np.zeros((len(lat), len(lon_values))))},
        coords={"lat": lat, "lon": lon_values},
    )

    result = diagnostics.extract_region(ds, "nino34", "lon", "lat")

    assert result.lon.size > 0, "no longitude points selected for the Niño 3.4 box"
    assert result.lon.min() >= expected_min
    assert result.lon.max() <= expected_max


def test_extract_region_selects_latitude_band():
    """extract_region() must restrict latitude to a predefined region's band regardless of grid extent."""
    lat = np.linspace(-20, 20, 41)
    lon = np.arange(0, 360, 5)
    ds = xr.Dataset(
        {"sst": (["lat", "lon"], np.zeros((len(lat), len(lon))))},
        coords={"lat": lat, "lon": lon},
    )

    result = diagnostics.extract_region(ds, "nino34", "lon", "lat")

    assert result.lat.min() >= -5
    assert result.lat.max() <= 5


def test_extract_region_case_insensitive_string_lookup():
    """Predefined region names should match regardless of case, since callers may pass either."""
    lat = np.linspace(-20, 20, 21)
    lon = np.arange(0, 360, 5)
    ds = xr.Dataset(
        {"sst": (["lat", "lon"], np.zeros((len(lat), len(lon))))},
        coords={"lat": lat, "lon": lon},
    )

    result = diagnostics.extract_region(ds, "NINO34", "lon", "lat")

    assert result.lon.size > 0


def test_extract_region_unknown_string_raises_value_error():
    """An unrecognized region name must fail loudly with the available options, not silently return empty data."""
    ds = xr.Dataset(
        {"sst": (["lat", "lon"], np.zeros((3, 3)))},
        coords={"lat": [0, 1, 2], "lon": [0, 1, 2]},
    )

    with pytest.raises(ValueError, match="not found"):
        diagnostics.extract_region(ds, "not_a_real_region", "lon", "lat")


def test_extract_region_invalid_type_raises_type_error():
    """A region that's neither a known string nor a lat/lon dict must raise TypeError, not fail deeper inside .sel()."""
    ds = xr.Dataset(
        {"sst": (["lat", "lon"], np.zeros((3, 3)))},
        coords={"lat": [0, 1, 2], "lon": [0, 1, 2]},
    )

    with pytest.raises(TypeError):
        diagnostics.extract_region(ds, ["not", "a", "dict"], "lon", "lat")


def test_extract_region_accepts_custom_dict_bounds():
    """A dict with 'lat'/'lon' tuples must bypass PREDEFINED_REGIONS and use the given bounds directly.

    This is the main new capability: extract_region() no longer only works
    for the hardcoded Nino 3.4 box, it accepts an arbitrary custom region.
    """
    lat = np.linspace(-20, 20, 41)
    lon = np.arange(0, 360, 5)
    ds = xr.Dataset(
        {"sst": (["lat", "lon"], np.zeros((len(lat), len(lon))))},
        coords={"lat": lat, "lon": lon},
    )
    custom_region = {"lat": (-10, 10), "lon": (100, 120)}

    result = diagnostics.extract_region(ds, custom_region, "lon", "lat")

    assert result.lat.min() >= -10
    assert result.lat.max() <= 10
    assert result.lon.min() >= 100
    assert result.lon.max() <= 120


def test_extract_region_custom_dict_handles_0_360_conversion():
    """A custom dict given in -180/180 bounds must still be converted onto a 0-360 grid.

    The longitude-convention auto-detection happens after the region lookup,
    so it must apply equally to caller-supplied dicts, not just predefined
    regions.
    """
    lat = np.linspace(-20, 20, 9)
    lon = np.arange(0, 360, 5)
    ds = xr.Dataset(
        {"sst": (["lat", "lon"], np.zeros((len(lat), len(lon))))},
        coords={"lat": lat, "lon": lon},
    )
    custom_region = {"lat": (-5, 5), "lon": (-170, -120)}  # nino34-equivalent bounds

    result = diagnostics.extract_region(ds, custom_region, "lon", "lat")

    assert result.lon.size > 0
    assert result.lon.min() >= 190
    assert result.lon.max() <= 240


def test_extract_region_handles_custom_dimension_names():
    """lon_dim/lat_dim overrides must be honored, e.g. ocean grids using xt_ocean/yt_ocean."""
    lat = np.linspace(-20, 20, 21)
    lon = np.arange(0, 360, 5)
    ds = xr.Dataset(
        {"sst": (["yt_ocean", "xt_ocean"], np.zeros((len(lat), len(lon))))},
        coords={"yt_ocean": lat, "xt_ocean": lon},
    )

    result = diagnostics.extract_region(
        ds, "nino34", lon_dim="xt_ocean", lat_dim="yt_ocean"
    )

    assert result.xt_ocean.size > 0
    assert result.yt_ocean.min() >= -5
    assert result.yt_ocean.max() <= 5


def test_extract_region_tasmania_no_wraparound_needed():
    """A second predefined region (tasmania) confirms lookup isn't hardcoded to nino34.

    tasmania's bounds sit entirely within 0-180, so this also sanity-checks
    that the 0-360 conversion doesn't corrupt a region that never needed it.
    """
    lat = np.linspace(-50, -30, 21)
    lon = np.arange(0, 360, 2)
    ds = xr.Dataset(
        {"sst": (["lat", "lon"], np.zeros((len(lat), len(lon))))},
        coords={"lat": lat, "lon": lon},
    )

    result = diagnostics.extract_region(ds, "tasmania", "lon", "lat")

    assert result.lon.min() >= 143
    assert result.lon.max() <= 149
    assert result.lat.min() >= -44
    assert result.lat.max() <= -39


# --------------------------------------------------------------------------
# select_extra_dims
# --------------------------------------------------------------------------


def test_select_extra_dims_noop_when_nothing_extra():
    """With no dims beyond exclude_dims, the data should pass through unchanged."""
    da = xr.DataArray(
        np.arange(6).reshape(2, 3),
        dims=["time", "lat"],
        coords={"time": [0, 1], "lat": [0, 1, 2]},
    )

    result = diagnostics.select_extra_dims(da, exclude_dims={"time", "lat"})

    xr.testing.assert_identical(result, da)


def test_select_extra_dims_numeric_defaults_to_nearest_zero():
    """A numeric extra dim (e.g. ocean depth) with no override should pick the level nearest 0 (surface)."""
    depth = np.array([5.0, 15.0, 25.0])
    da = xr.DataArray(
        np.array([10.0, 20.0, 30.0]),
        dims=["st_ocean"],
        coords={"st_ocean": depth},
    )

    result = diagnostics.select_extra_dims(da, exclude_dims=set())

    assert result.item() == 10.0  # depth=5.0 is nearest to 0
    assert "st_ocean" not in result.dims


def test_select_extra_dims_numeric_explicit_override():
    """An explicit extra_dim_selectors value should be used instead of the nearest-0 default."""
    depth = np.array([5.0, 15.0, 25.0])
    da = xr.DataArray(
        np.array([10.0, 20.0, 30.0]),
        dims=["st_ocean"],
        coords={"st_ocean": depth},
    )

    result = diagnostics.select_extra_dims(
        da, exclude_dims=set(), extra_dim_selectors={"st_ocean": 25.0}
    )

    assert result.item() == 30.0


def test_select_extra_dims_non_numeric_defaults_to_first_index():
    """Regression test for TypeError: ufunc 'isfinite' not supported...

    A non-numeric extra dim (e.g. string ensemble member IDs like
    "r1i1p1f1") must NOT go through .sel(..., method="nearest") - pandas'
    nearest-value indexer calls isfinite on the index to compare distances,
    which crashes on object/string dtype. Non-numeric dims must fall back to
    taking the first entry instead, matching controller.py's own
    .isel(member=0) convention.
    """
    members = np.array(["r1i1p1f1", "r2i1p1f1"])
    da = xr.DataArray(
        np.array([1.0, 2.0]),
        dims=["member"],
        coords={"member": members},
    )

    result = diagnostics.select_extra_dims(da, exclude_dims=set())

    assert result.item() == 1.0
    assert "member" not in result.dims


def test_select_extra_dims_non_numeric_explicit_override():
    """An explicit label for a non-numeric extra dim should be matched exactly."""
    members = np.array(["r1i1p1f1", "r2i1p1f1"])
    da = xr.DataArray(
        np.array([1.0, 2.0]),
        dims=["member"],
        coords={"member": members},
    )

    result = diagnostics.select_extra_dims(
        da, exclude_dims=set(), extra_dim_selectors={"member": "r2i1p1f1"}
    )

    assert result.item() == 2.0


# --------------------------------------------------------------------------
# calc_anomolies
# --------------------------------------------------------------------------


def test_calc_anomolies_isolates_injected_anomaly_from_seasonal_cycle():
    """The monthly climatology should fully absorb a perfectly repeating seasonal cycle.

    Data is spatially uniform and exactly periodic, so any residual after
    climatology-removal can only come from a deliberately injected anomaly.
    With only n_years samples per calendar month, the bump also nudges that
    month's own climatology (it's the mean of n_years values, one of which
    is bumped), so the bumped timestep shows bump*(n-1)/n and every OTHER
    occurrence of that same calendar month leaks -bump/n; every other
    calendar month is untouched. This directly validates the
    climatology-removal math, not just "it runs".
    """
    periods = 48
    n_years = periods // 12
    ds = _seasonal_dataset(periods=periods)
    bump_index = 25
    bump_value = 2.0
    ds["sst"].values[bump_index] += bump_value

    result = diagnostics.calc_anomolies(ds, "lon", "lat", "sst").compute()

    same_month = (np.arange(periods) % 12) == (bump_index % 12)
    other_same_month = same_month.copy()
    other_same_month[bump_index] = False
    different_month = ~same_month

    assert np.isclose(
        result.values[bump_index], bump_value * (n_years - 1) / n_years, atol=1e-8
    )
    assert np.allclose(
        result.values[other_same_month], -bump_value / n_years, atol=1e-8
    )
    assert np.allclose(result.values[different_month], 0, atol=1e-8)


def test_calc_anomolies_applies_latitude_weighting():
    """The spatial mean must be cosine-latitude-weighted, not a plain average.

    Injects an anomaly at only one of two latitudes with very different
    cos(lat) weights (0 vs 60 degrees) and checks the result matches the
    weighted combination, not a naive 50/50 average. Climatology is computed
    per lat/lon point before the spatial mean, so with n_years=2 samples per
    calendar month, the bumped lat's own anomaly is diluted by (n-1)/n
    before weighting is applied (see the climatology-leakage test above).
    """
    periods = 24
    n_years = periods // 12
    time = pd.date_range("2000-01-01", periods=periods, freq="MS")
    lat = np.array([0.0, 60.0])
    lon = np.array([200.0])
    seasonal = 20 + 3 * np.sin(2 * np.pi * time.month.values / 12)
    data = (
        np.broadcast_to(seasonal[:, None, None], (periods, 2, 1)).astype(float).copy()
    )

    bump_index = 5
    bump_value = 4.0
    data[bump_index, 0, 0] += bump_value  # only lat=0.0 gets the bump

    ds = xr.Dataset(
        {"sst": (["time", "lat", "lon"], data)},
        coords={"time": time, "lat": lat, "lon": lon},
    )

    result = diagnostics.calc_anomolies(ds, "lon", "lat", "sst").compute()

    w0, w1 = np.cos(np.deg2rad(0.0)), np.cos(np.deg2rad(60.0))
    diluted_bump = bump_value * (n_years - 1) / n_years
    expected_bump = diluted_bump * w0 / (w0 + w1)
    unweighted_bump = diluted_bump / 2

    assert np.isclose(result.values[bump_index], expected_bump, atol=1e-6)
    assert not np.isclose(result.values[bump_index], unweighted_bump, atol=1e-6)


def test_calc_anomolies_collapses_extra_dim_before_anomaly():
    """An extra dim (e.g. depth) must be resolved before the anomaly calc, not left dangling.

    Without select_extra_dims being applied first, the weighted spatial mean
    would leave the extra dim in the output instead of collapsing to a
    single surface-level time series.
    """
    depth = np.array([5.0, 50.0])
    time = pd.date_range("2000-01-01", periods=24, freq="MS")
    lat = np.array([-5.0, 0.0, 5.0])
    lon = np.array([200.0, 210.0])
    seasonal = 20 + 3 * np.sin(2 * np.pi * time.month.values / 12)
    data = np.zeros((24, len(depth), len(lat), len(lon)))
    data[:, 0, :, :] = seasonal[:, None, None]  # surface follows the cycle
    data[:, 1, :, :] = 999.0  # deep level is a wildly different constant

    ds = xr.Dataset(
        {"temp": (["time", "st_ocean", "lat", "lon"], data)},
        coords={"time": time, "st_ocean": depth, "lat": lat, "lon": lon},
    )

    result = diagnostics.calc_anomolies(ds, "lon", "lat", "temp").compute()

    assert "st_ocean" not in result.dims
    assert np.allclose(
        result.values, 0, atol=1e-8
    )  # surface level has no injected anomaly


# --------------------------------------------------------------------------
# rolling_window_size
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "freq, periods, expected_window",
    [
        ("MS", 240, 5),  # monthly, 20y: matches the original hardcoded 5-month window
        ("D", 3650, 150),  # daily, 10y: ~5 months expressed in days
        ("YS", 30, 1),  # yearly, 30y: 5-month smoothing doesn't apply to annual data
    ],
)
def test_rolling_window_size_is_frequency_aware(freq, periods, expected_window):
    """The rolling window should target ~5 real-world months regardless of the data's native cadence.

    A hardcoded window of 5 timesteps is correct only for monthly data; for
    daily data it was a near-no-op 5-day smoothing instead of ~5 months.
    """
    time = xr.date_range(
        "2000-01-01", periods=periods, freq=freq, calendar="standard", use_cftime=False
    )
    da = xr.DataArray(np.arange(periods), dims="time", coords={"time": time})

    assert diagnostics.rolling_window_size(da["time"]) == expected_window


def test_rolling_window_size_clamped_to_record_length():
    """Regression test for ValueError: Moving window (=5) must between 1 and 4, inclusive.

    bottleneck's move_mean (used by xarray's .rolling().mean() when
    bottleneck is installed, e.g. on Gadi) raises a hard error when the
    window exceeds the record length, rather than silently NaN-padding.
    This guards against that by clamping the window to len(time).
    """
    time = xr.date_range(
        "2000-01-01", periods=4, freq="YS", calendar="standard", use_cftime=False
    )
    da = xr.DataArray(np.arange(4), dims="time", coords={"time": time})

    window = diagnostics.rolling_window_size(da["time"])

    assert 1 <= window <= 4


def test_rolling_window_size_single_timestep():
    """A single-timestep record can't have a rolling window > 1 - must not divide by zero or crash."""
    time = xr.date_range(
        "2000-01-01", periods=1, freq="MS", calendar="standard", use_cftime=False
    )
    da = xr.DataArray(np.arange(1), dims="time", coords={"time": time})

    assert diagnostics.rolling_window_size(da["time"]) == 1


def test_rolling_window_size_handles_cftime_diffs():
    """cftime timestep diffs are datetime.timedelta objects (object dtype), not numpy timedelta64.

    Must be handled without crashing, since every dataset this repo loads
    uses use_cftime=True.
    """
    time = xr.date_range(
        "1900-01-16", periods=240, freq="MS", calendar="julian", use_cftime=True
    )
    da = xr.DataArray(np.arange(240), dims="time", coords={"time": time})

    assert diagnostics.rolling_window_size(da["time"]) == 5


# --------------------------------------------------------------------------
# sst_anomaly_nino34 (integration)
# --------------------------------------------------------------------------


def test_sst_anomaly_nino34_returns_figure():
    """The function must return a matplotlib Figure (not None) so callers like ui.py can embed it."""
    ds = _seasonal_dataset(periods=36, lon=np.arange(0, 360, 5))

    fig = diagnostics.sst_anomaly_nino34(ds, "lon", "lat", "sst")

    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_sst_anomaly_nino34_cftime_time_axis_does_not_crash():
    """Regression test for TypeError: ufunc 'isfinite' not supported... during plotting.

    Every dataset this repo loads uses use_cftime=True (real dates can be
    outside pandas' Timestamp range). matplotlib can't plot cftime dates
    without nc_time_axis's unit converter registered - this must not crash
    regardless of which matplotlib call (fill_between, plot, ...) touches
    the time axis first.
    """
    ds = _seasonal_dataset(
        periods=120,
        lon=np.arange(0, 360, 5),
        freq="MS",
        use_cftime=True,
        calendar="julian",
    )

    fig = diagnostics.sst_anomaly_nino34(ds, "lon", "lat", "sst")

    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_sst_anomaly_nino34_non_numeric_member_dim_does_not_crash():
    """Regression test: a string-labeled member dim must not crash select_extra_dims."""
    ds = _seasonal_dataset(periods=36, lon=np.arange(0, 360, 5))
    ds = xr.concat(
        [ds.assign_coords(member=m) for m in ["r1i1p1f1", "r2i1p1f1"]], dim="member"
    )

    fig = diagnostics.sst_anomaly_nino34(ds, "lon", "lat", "sst")

    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_sst_anomaly_nino34_short_yearly_record_does_not_crash():
    """Regression test for the bottleneck window-length ValueError on short/yearly records."""
    ds = _seasonal_dataset(periods=4, lon=np.arange(0, 360, 5), freq="YS")

    fig = diagnostics.sst_anomaly_nino34(ds, "lon", "lat", "sst")

    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_sst_anomaly_nino34_small_dask_chunks_do_not_crash():
    """Regression test for ValueError: Moving window (=5) must between 1 and 4, inclusive.

    This is a DIFFERENT root cause than the short-record case above: with a
    long record (240 months, window=5 is valid for the total length) but
    small per-file dask chunks along time (e.g. 4 months/chunk, matching how
    real ACCESS catalogs chunk per file), bottleneck's move_mean validates
    the window against each CHUNK's length, not the total record length, and
    raises the exact same error. Only reproduces with bottleneck actually
    installed (it's on Gadi; xarray silently NaN-pads without it). Guards
    against rechunking the post-spatial-mean time series to a single chunk
    before rolling.
    """
    ds = _seasonal_dataset(periods=240, lon=np.arange(0, 360, 5), freq="MS")
    ds = ds.chunk({"time": 4})

    fig = diagnostics.sst_anomaly_nino34(ds, "lon", "lat", "sst")

    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_sst_anomaly_nino34_extra_dim_selector_overrides_default_depth():
    """extra_dim_selectors should reach through to select_extra_dims and change which level is used."""
    depth = np.array([5.0, 50.0])
    time = pd.date_range("2000-01-01", periods=36, freq="MS")
    lat = np.linspace(-20, 20, 9)
    lon = np.arange(0, 360, 5)
    seasonal = 20 + 3 * np.sin(2 * np.pi * time.month.values / 12)
    data = np.zeros((36, len(depth), len(lat), len(lon)))
    data[:, 0, :, :] = seasonal[:, None, None]
    data[:, 1, :, :] = (
        seasonal[:, None, None] + 500.0
    )  # deep level offset by a huge constant

    ds = xr.Dataset(
        {"temp": (["time", "st_ocean", "lat", "lon"], data)},
        coords={"time": time, "st_ocean": depth, "lat": lat, "lon": lon},
    )

    fig_surface = diagnostics.sst_anomaly_nino34(ds, "lon", "lat", "temp")
    fig_deep = diagnostics.sst_anomaly_nino34(
        ds, "lon", "lat", "temp", extra_dim_selectors={"st_ocean": 50.0}
    )

    # Both should succeed and produce a normalized index; since the deep
    # level's anomaly shape is identical (just offset by a constant, which
    # the anomaly/climatology step removes), the two should agree closely -
    # proving the override actually reached the surface-vs-deep selection.
    y_surface = fig_surface.axes[0].lines[0].get_ydata()
    y_deep = fig_deep.axes[0].lines[0].get_ydata()
    assert np.allclose(y_surface, y_deep, atol=1e-6, equal_nan=True)

    plt.close(fig_surface)
    plt.close(fig_deep)


def test_sst_anomaly_nino34_start_date_trims_record_before_computation():
    """start_date must drop pre-cutoff timesteps before any computation, not just crop the plot.

    Guards against spinup-year drift skewing the climatology/anomaly/std
    for the entire record, not just what's visually displayed.
    """
    ds = _seasonal_dataset(periods=60, lon=np.arange(0, 360, 5), freq="MS")
    # Inject a large drift only in the first 24 months (simulated spinup)
    ds["sst"].values[:24] += np.linspace(10, 0, 24)[:, None, None]

    fig_full = diagnostics.sst_anomaly_nino34(ds, "lon", "lat", "sst")
    fig_trimmed = diagnostics.sst_anomaly_nino34(
        ds, "lon", "lat", "sst", start_date="2002-01-01"
    )

    x_full = fig_full.axes[0].lines[0].get_xdata()
    x_trimmed = fig_trimmed.axes[0].lines[0].get_xdata()

    assert len(x_trimmed) < len(x_full)
    assert pd.Timestamp(x_trimmed[0]).year >= 2002

    plt.close(fig_full)
    plt.close(fig_trimmed)


class _FakeMatchedCatalog:
    def __init__(self, keys):
        self._keys = keys

    def keys(self):
        return self._keys


class _FakeModel:
    """Stand-in for the esm_datastore returned by `.search(name=...).to_source()`.

    Maps a (realm, frequency, variables) query to whichever key(s) a real
    catalog search would return, so tests can control that without a real
    intake-esm/access_nri_intake catalog.
    """

    def __init__(self, keys_by_query):
        self._keys_by_query = keys_by_query

    def search(self, **kwargs):
        query = (
            kwargs.get("realm"),
            kwargs.get("frequency"),
            tuple(kwargs.get("variable", ())),
        )
        return _FakeMatchedCatalog(self._keys_by_query.get(query, []))

    def keys(self):
        return sorted({k for keys in self._keys_by_query.values() for k in keys})


def test_load_default_om3_reference_datasets_looks_up_experiment_by_name_directly(
    monkeypatch,
):
    """The KeyError Theo hit wasn't caused by an unstable key string - he
    confirmed 'ocean.1mon.nv:2.scalar_axis:1' is a genuine file_id when the
    experiment is looked up directly via `intake.cat.access_nri[name]`. It
    was caused by the old code going through
    `_load_access_nri_catalog("OM2", filter=True).search(name=name).to_source()`,
    which pre-filters the metacatalog by a `model=".*OM2.*"` regex before
    searching by name - a filter that can silently narrow the datastore
    returned for that name. The fix must look up each reference experiment
    directly by name via data._load_access_nri_experiment (no model-type
    pre-filter), never via data._load_access_nri_catalog.
    """
    ds = xr.Dataset({"masso": ("time", [1.0, 2.0])}, coords={"time": [0, 1]})
    query = ("ocean", "1mon", tuple(diagnostics.OM3_GLOBAL_SCALARS))
    fake_model = _FakeModel({query: ["key_a"]})

    calls = []
    monkeypatch.setattr(
        diagnostics.data,
        "_load_access_nri_experiment",
        lambda name: (calls.append(name), fake_model)[1],
    )
    monkeypatch.setattr(
        diagnostics.data,
        "_load_access_nri_catalog",
        lambda *a, **k: pytest.fail(
            "load_default_om3_reference_datasets must not pre-filter by "
            "model type via _load_access_nri_catalog"
        ),
    )
    monkeypatch.setattr(
        diagnostics.data, "_build_data_object", lambda model_cat, key: ds
    )

    refs = diagnostics.load_default_om3_reference_datasets()

    name = diagnostics.DEFAULT_OM3_TIMESERIES_REFERENCES[0]
    assert calls == [name]
    assert set(refs[name].data_vars) == {"masso"}


def test_load_default_om3_reference_datasets_merges_split_keys(monkeypatch):
    """OM3_GLOBAL_SCALARS variables can legitimately be split across more
    than one intake-esm key for a given realm/frequency (e.g. because they
    don't all share the same "extra" dims). The fix searches by
    realm/frequency/variable rather than assuming one fixed key string, and
    must merge whatever key(s) that search returns.
    """
    ds_masso = xr.Dataset({"masso": ("time", [1.0, 2.0])}, coords={"time": [0, 1]})
    ds_tosga = xr.Dataset({"tosga": ("time", [3.0, 4.0])}, coords={"time": [0, 1]})

    query = ("ocean", "1mon", tuple(diagnostics.OM3_GLOBAL_SCALARS))
    fake_model = _FakeModel({query: ["key_a", "key_b"]})

    monkeypatch.setattr(
        diagnostics.data, "_load_access_nri_experiment", lambda name: fake_model
    )
    monkeypatch.setattr(
        diagnostics.data,
        "_build_data_object",
        lambda model_cat, key: {"key_a": ds_masso, "key_b": ds_tosga}[key],
    )

    refs = diagnostics.load_default_om3_reference_datasets()

    name = diagnostics.DEFAULT_OM3_TIMESERIES_REFERENCES[0]
    assert set(refs[name].data_vars) == {"masso", "tosga"}


def test_load_default_om3_reference_datasets_raises_informative_error_when_no_match(
    monkeypatch,
):
    """No matching realm/frequency/variable combination should raise a clear
    KeyError up front, rather than letting a stale/hardcoded key string fail
    deep inside intake-esm with no indication of what was actually searched
    for.
    """
    fake_model = _FakeModel({})
    monkeypatch.setattr(
        diagnostics.data, "_load_access_nri_experiment", lambda name: fake_model
    )

    with pytest.raises(KeyError, match="No catalog entries"):
        diagnostics.load_default_om3_reference_datasets()
