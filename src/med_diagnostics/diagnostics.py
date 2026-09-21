# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""This is a placeholder for diagnostic recipes / scripting"""

import matplotlib.pyplot as plt
import numpy as np


def nino34(dataset, lon_dim, lat_dim):
    """Returns dataset selected for the Niño 3.4 region"""
    nino34_ds = dataset.sel({lat_dim: slice(-5, 5), lon_dim: slice(190, 240)})
    return nino34_ds


def calc_anomolies(dataset, lat_dim, lon_dim):
    # Calculate anomalies from the monthly climatology
    gb = dataset.sst.groupby("time.month")
    sst_nino34_anom = gb - gb.mean(dim="time")

    # Create weights based on the cosine of the latitude
    weights = np.cos(np.deg2rad(dataset.lat))
    weights.name = "weights"

    # Apply the latitude weights and calculate the spatial mean
    index_nino34 = sst_nino34_anom.weighted(weights).mean(dim=[lat_dim, lon_dim])

    return index_nino34


def sst_anomaly_nino34(dataset, model_type):
    if model_type == "OM2":  # TODO fix and replace so not checking on string
        lon_dim = "xt_ocean"
        lat_dim = "yt_ocean"

    nino34_ds = nino34(dataset, lon_dim, lat_dim)
    anomalies = calc_anomolies(nino34_ds, lat_dim, lon_dim)
    anomolies_rolling_mean = anomalies.rolling(time=5, center=True).mean()
    std_dev = nino34_ds.sst.std()
    normalized_index_nino34_rolling_mean = anomolies_rolling_mean / std_dev
    # Compute the data into memory first
    index_plot = normalized_index_nino34_rolling_mean.compute()

    # Extract the raw NumPy arrays
    time_vals = index_plot.time.values
    y_vals = index_plot.values

    plt.figure(figsize=(12, 6))

    # Red fill for El Niño
    plt.fill_between(
        time_vals,
        y_vals,
        0.4,
        where=(y_vals >= 0.4),  # Matplotlib's boolean mask
        interpolate=True,  # Smooths the fill precisely to the intersection
        color="red",
        alpha=0.9,
    )

    # Blue fill for La Niña
    plt.fill_between(
        time_vals,
        y_vals,
        -0.4,
        where=(y_vals <= -0.4),
        interpolate=True,
        color="blue",
        alpha=0.9,
    )

    index_plot.plot(color="black")
    plt.axhline(0, color="black", lw=0.5)
    plt.axhline(0.4, color="black", linewidth=0.5, linestyle="dotted")
    plt.axhline(-0.4, color="black", linewidth=0.5, linestyle="dotted")
    plt.title("Niño 3.4 Index")
    plt.ylabel("SST Anomaly (°C)")
