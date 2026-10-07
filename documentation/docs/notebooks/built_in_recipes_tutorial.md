# Built-in Analysis Recipes

MLD comes with a set of built-in analysis recipes. They appear in the "Select analysis recipe" dropdown of the **Run analysis recipes** section for every user, without needing to be registered. This page describes what each recipe does, which data it expects, and the options it offers. For how to run a recipe, see [Running Analysis Recipes](getting_started_tutorial.md#34-running-analysis-recipes-optional) in the Getting started tutorial.

| Dropdown label | Function | Plots | Targets |
| :--- | :--- | :--- | :--- |
| Niño 3.4 index for sea surface temperature | `recipe_sst_anomaly_nino34` | 1 | Any grid with SST, a `time` dimension and latitude/longitude coordinates |
| Timeseries of a variable over a chosen region (Area-weighted mean). | `recipe_regional_mean_mom5` | 1 | MOM5 output (ACCESS-OM2, ACCESS-ESM1.6) |
| OM3 timeseries suite (OM3 variable names) | `recipe_om3_timeseries` | 1 per field found | ACCESS-OM3 output |
| OM3 timeseries suite (custom variable mapping) | `recipe_om3_timeseries_mapped` | 1 per field chosen | ACCESS ocean output on any grid |

All of these functions live in `med_diagnostics.recipes`, along with helpers you can reuse in your own recipes (see the [API reference](../../api/#med_diagnostics.recipes)).

!!! tip "Defaults and the loaded dataset"
    Each recipe's option dropdowns are filled in with its defaults (e.g. `tos`, `xt_ocean`) when these exist in the loaded dataset. If they don't, choose the matching variable or coordinate yourself before clicking "Plot data".

## Niño 3.4 index

**Dropdown label:** Niño 3.4 index for sea surface temperature (`recipe_sst_anomaly_nino34`)

Plots the Niño 3.4 index, the standard measure of the El Niño–Southern Oscillation (ENSO), from your sea surface temperature:

1. The SST is cut to the Niño 3.4 region (5°S–5°N, 170°W–120°W). Longitudes in either −180–180 or 0–360 are handled.
2. Monthly anomalies are taken from the dataset's own monthly climatology, then averaged over the region weighted by cos(latitude).
3. The anomalies are smoothed with a centred rolling mean of about 5 months (150 days, converted to timesteps from the data's own output frequency), then divided by the standard deviation of the unsmoothed anomalies.

The index is drawn in black with reference lines at 0 and ±0.4. Periods above +0.4 (El Niño) are shaded red and periods below −0.4 (La Niña) are shaded blue.

| Option | Default | Description |
| :--- | :--- | :--- |
| Select Variable | `tos` | Sea surface temperature variable |
| Select Longitude Dim | `xt_ocean` | Longitude coordinate (e.g. `xt_ocean` for MOM5, `lon` for CMORised output) |
| Select Latitude Dim | `yt_ocean` | Latitude coordinate (e.g. `yt_ocean` for MOM5, `lat` for CMORised output) |

Notes:

- The time dimension must be called `time`, and the latitude and longitude options must be the variable's 1D dimensions (as on MOM5's `xt_ocean`/`yt_ocean` grid or CMORised `lon`/`lat` output).
- The anomalies are taken from the climatology of the years you loaded, so load several years (ideally a few decades) for a meaningful index, and leave out any spin-up years with "Years to load".

## Regional mean timeseries

**Dropdown label:** Timeseries of a variable over a chosen region (Area-weighted mean). (`recipe_regional_mean_mom5`)

Plots the timeseries of any variable averaged over a predefined region, at a chosen depth. The region is cut out of the data, and the mean is weighted by cos(latitude). Optional overlays show a linear trend, the top and bottom 10% of values, and a reference line.

| Option | Default | Description |
| :--- | :--- | :--- |
| `variable` | `temp` | Variable to average |
| `region` | `tasmania` | Region to average over (see the list below) |
| `lon_dim` | `xt_ocean` | Longitude coordinate |
| `lat_dim` | `yt_ocean` | Latitude coordinate |
| `lvl_dim` | `st_ocean` | Depth coordinate. Ignored if the variable has no such dimension, so surface fields work with the default |
| `depth` (m) | `0.0` | Depth to plot. The nearest model level is used |
| `smooth_steps` | `1` | Centred rolling-mean window in timesteps (1 turns smoothing off) |
| `show_trend` | on | Overlay a least-squares linear trend (grey dotted line) |
| `show_percentiles` | on | Shade values above the 90th percentile (red) and below the 10th percentile (blue), with dashed lines at each percentile |
| `threshold` | blank | A value to draw as a red dashed horizontal line. Leave blank for none |

??? info "View the predefined regions"

    | Region | Latitude | Longitude |
    | :--- | :--- | :--- |
    | `nino12` | 10°S–0° | 90°W–80°W |
    | `nino3` | 5°S–5°N | 150°W–90°W |
    | `nino34` | 5°S–5°N | 170°W–120°W |
    | `nino4` | 5°S–5°N | 160°E–150°W (crosses the dateline) |
    | `iod_west` | 10°S–10°N | 50°E–70°E |
    | `iod_east` | 10°S–0° | 90°E–110°E |
    | `tna` (Tropical North Atlantic) | 5°N–25°N | 55°W–15°W |
    | `tsa` (Tropical South Atlantic) | 20°S–0° | 30°W–10°E |
    | `global` | 90°S–90°N | all |
    | `nh` (Northern Hemisphere) | 0°–90°N | all |
    | `sh` (Southern Hemisphere) | 90°S–0° | all |
    | `tropics` | 20°S–20°N | all |
    | `tasmania` | 44°S–39°S | 143°E–149°E |
    | `australia` | 44°S–10°S | 112°E–154°E |
    | `maritime_continent` | 10°S–10°N | 90°E–150°E |
    | `southern_ocean` | 90°S–50°S | all |
    | `arctic` | 66.5°N–90°N | all |
    | `antarctic` | 90°S–66.5°S | all |

    These are defined in `med_diagnostics.recipes.PREDEFINED_REGIONS`, and the `extract_region` helper can cut any of them (or your own `{"lat": (min, max), "lon": (west, east)}` box) out of a dataset in a custom recipe.

Notes:

- The recipe checks that the variable has the chosen latitude and longitude coordinates, and stops with an error if it doesn't. It is written for MOM5's 1D `xt_ocean`/`yt_ocean` grid; for other grids, write a custom recipe using `extract_region`.
- The time dimension must be called `time`.
- The trend and percentiles are calculated after smoothing, from the years you loaded.

## OM3 timeseries suites

Two built-in suites reproduce the timeseries plots from the [ACCESS-OM3 paper 1 figures](https://access-om3-paper-1.readthedocs.io/mc_25km_jra_iafwombatlite-test4-d28e0359-2026.07.000/experiments/MC_25km_jra_iaf%2Bwombatlite-test4-d28e0359/timeseries/). Each plot shows a global timeseries of your data with its rolling mean (thicker line), overlaid on the same timeseries from the paper's reference runs:

- Three ACCESS-OM3 25 km runs (`MC_25km_jra_iaf-1.0-beta-5165c0f8`, `MC_25km_jra_iaf+wombatlite-test3v2-00532b88` and `MC_25km_jra_iaf+wombatlite-test4-d28e0359`), which are not yet in the intake catalogue.
- The ACCESS-OM2 0.25° run `025deg_jra55_iaf_omip2_cycle1` from the ACCESS-NRI intake catalogue, for the fields OM2 also outputs (`soga`, `thetaoga`, `tosga` and `sosga`).

The suites cover 28 fields: global means of temperature and salinity (`thetaoga`, `soga`, `tosga`, `sosga`) and ocean mass (`masso`), the global maximum/minimum of surface fields (`tos_max`, `tos_min`, `sos_max`, `sos_min`, `zos_max`, `zos_min`, `speed_max`, `mlotst_max`), and global totals of salt and freshwater fluxes (e.g. `total_wfo`, `total_precip`, `total_friver`).

| Recipe | Use it when | Options |
| :--- | :--- | :--- |
| OM3 timeseries suite (OM3 variable names) | Your dataset uses the OM3 names above, e.g. ACCESS-OM3 output. Every field found in the dataset is plotted. | Time dimension; rolling-mean window (days, default 365) |
| OM3 timeseries suite (custom variable mapping) | Your dataset uses other names, e.g. ACCESS-OM2 (`temp_global_ave` for `thetaoga`) or another grid. | One dropdown per field to choose the variable that stands in for it (leave as None to skip it); time dimension; rolling-mean window |

??? info "View all 28 fields"

    Fields marked *max*/*min* plot the global maximum or minimum at each timestep. All others plot a volume-weighted global mean, using the dataset's `cell_measures` where available, otherwise cos(latitude) weighted by layer thickness.

    | OM3 name | Plot title | Reduction |
    | :--- | :--- | :--- |
    | `masso` | Mass of liquid ocean | mean |
    | `soga` | Global Mean Ocean Salinity | `salt_global_ave` | mean |
    | `thetaoga` | Global Mean Ocean Potential Temperature | `temp_global_ave` | mean |
    | `tosga` | Sea Surface Temperature | `temp_surface_ave` | mean |
    | `sosga` | Global Mean Sea Surface Salinity | `salt_surface_ave` | mean |
    | `speed_max` | Maximum Ocean Current Speed | max |
    | `mlotst_max` | Maximum Ocean Mixed Layer Thickness | max |
    | `tos_max` | Maximum Sea Surface Temperature | max |
    | `tos_min` | Minimum Sea Surface Temperature | min |
    | `sos_max` | Maximum Sea Surface Salinity | max |
    | `sos_min` | Minimum Sea Surface Salinity | min |
    | `zos_max` | Maximum Sea Surface Height | max |
    | `zos_min` | Minimum Sea Surface Height | min |
    | `total_salt_Flux_Added` | Total Salt Flux Added | mean |
    | `total_salt_Flux_In` | Total Salt Flux In | mean |
    | `total_salt_flux` | Total Salt Flux | mean |
    | `net_fresh_water_global_adjustment` | Net Fresh Water Global Adjustment | mean |
    | `salt_flux_global_restoring_adjustment` | Salt Flux Global Restoring Adjustment | mean |
    | `total_wfo` | Total Water Flux Into Ocean | mean |
    | `total_evs` | Total Evaporation | mean |
    | `total_fsitherm` | Total Thermodynamic Sea Ice Flux | mean |
    | `total_precip` | Total Precipitation | mean |
    | `total_prsn` | Total Snowfall | mean |
    | `total_lprec` | Total Liquid Precipitation | mean |
    | `total_ficeberg` | Total Iceberg Melt | mean |
    | `total_friver` | Total River Runoff | mean |
    | `total_net_massout` | Total Net Mass Out | mean |
    | `total_net_massin` | Total Net Mass In | mean |

Notes:

- These analyses can be quite slow to run, as they load a number of other reference datasets.
- The rolling mean is taken over the same number of days for your data and every reference run, whatever their output frequency.
- The analyses are primarily intended for scalar datasets. Gridded data also works, but the global mean (or max/min) must be calculated first, which takes much longer. Temperatures in Kelvin are converted to °C.
- The reference runs are read from `/g/data/ol01`, so your ARE session needs access to the `ol01` project (add `gdata/ol01` to its storage). If a reference field can't be found, a message such as `soga failed` is printed and the plot is drawn without it.

!!! tip "Writing your own recipes"
    You can add your own analyses to this section. See the [Adding custom analyses](adding_custom_analyses.md) tutorial. After registering a new recipe, click "Refresh analysis recipes" to add it to the dropdown.
