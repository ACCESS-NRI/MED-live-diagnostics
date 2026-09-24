import esmvalcore.preprocessor
import iris
import matplotlib.pyplot as plt
import xarray as xr
from access_moppy import ACCESS_ESM_CMORiser
from access_moppy.atmosphere import Atmosphere_CMORiser
from ncdata.iris_xarray import cubes_from_xarray

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# model_type -> (moppy mapping file model_id, CV-valid source_id).
# moppy validates source_id against the CMIP6 CVs, which only list CM2, ESM1-5,
# OM2 and OM2-025, so the nearest one is used; it only ends up in the metadata.
ACCESS_MODEL_TYPES = {
    "ESM1.6": ("ACCESS-ESM1-6", "ACCESS-ESM1-5"),
    "CM3": ("ACCESS-CM3", "ACCESS-CM2"),
    "OM3": ("ACCESS-OM3", "ACCESS-CM2"),
    # No OM2 mapping file ships with moppy; ESM1.6's ocean is MOM5, as in OM2
    "OM2": ("ACCESS-ESM1-6", "ACCESS-OM2"),
}

# CMIP6 name -> MOM5 ocean_scalar variable. moppy's mappings derive these from
# gridded 3D fields, but MOM5 already writes them, in CMIP units.
MOM5_SCALARS = {
    "thetaoga": "temp_global_ave",
    "tosga": "temp_surface_ave",
    "soga": "salt_global_ave",
    "sosga": "salt_surface_ave",
    "masso": "total_mass_seawater",
    "volo": "total_volume_seawater",
}


def cmorise(
    dataset,
    model_type,
    compound_name,
    experiment_id="historical",
    variant_label="r1i1p1f1",
    grid_label="gn",
    activity_id="CMIP",
    parent_info=None,
    write_output=False,
    output_path=".",
    **cmoriser_kwargs,
):
    """
    CMORise one variable of an ACCESS model dataset with ``ACCESS_ESM_CMORiser``.

    Parameters
    ----------
    dataset : xr.Dataset
        Raw model output containing the variable's inputs.
    model_type : str
        One of ``ACCESS_MODEL_TYPES``, e.g. ``"OM2"``.
    compound_name : str
        CMIP6 ``table.variable`` to produce, e.g. ``"Omon.tos"``.
    experiment_id, variant_label, grid_label, activity_id : str
        CMIP metadata; must be valid CMIP6 CV entries.
    parent_info : dict, optional
        Parent experiment metadata. Defaults to moppy's piControl parent.
    write_output : bool
        Also write the CMORised NetCDF to ``output_path``.
    **cmoriser_kwargs
        Passed straight to ``ACCESS_ESM_CMORiser`` (e.g. ``enable_resampling``).

    Returns
    -------
    xr.Dataset
        The CMORised variable and its bounds.
    """
    model_id, source_id = ACCESS_MODEL_TYPES[model_type]
    cmor_name = compound_name.split(".")[1]
    scalar_var = MOM5_SCALARS.get(cmor_name)
    is_scalar = scalar_var in dataset and "scalar_axis" in dataset[scalar_var].dims
    if is_scalar:
        # moppy wants <dim>_bnds on a "bnds" dim; MOM5 writes time_bounds on nv
        renames = {"time_bounds": "time_bnds", "nv": "bnds"}
        bounds = [var for var in ("time_bounds", "time_bnds") if var in dataset]
        dataset = dataset[[scalar_var, *bounds]].squeeze("scalar_axis", drop=True)
        # Loaded because moppy recomputes lazy time_bnds (as NaT for these files);
        # a global timeseries is only a few KB
        dataset = dataset.rename(
            {k: v for k, v in renames.items() if k in dataset.variables}
        ).load()

    cmoriser = ACCESS_ESM_CMORiser(
        input_data=dataset,
        compound_name=compound_name,
        experiment_id=experiment_id,
        source_id=source_id,
        variant_label=variant_label,
        grid_label=grid_label,
        activity_id=activity_id,
        parent_info=parent_info,
        model_id=model_id,
        output_path=output_path,
        **cmoriser_kwargs,
    )

    if is_scalar:
        # A direct rename replaces moppy's gridded-mean mapping
        mapping = {
            cmor_name: {
                "dimensions": {"time": "time"},
                "units": cmoriser.vocab.variable["units"],
                "positive": None,
                "model_variables": [scalar_var],
                "calculation": {"type": "direct"},
            }
        }
        # Omon routes to the ocean CMORiser, which needs a horizontal grid; the
        # atmosphere one handles time-only variables
        cmoriser.cmoriser = Atmosphere_CMORiser(
            input_data=cmoriser.input_dataset,
            output_path=str(cmoriser.output_path),
            compound_name=cmoriser.cmip6_compound_name,
            vocab=cmoriser.vocab,
            variable_mapping=mapping,
            drs_root=cmoriser.drs_root,
        )

    with cmoriser:
        cmoriser.run(write_output=write_output)
        ds = cmoriser.to_dataset()

    # moppy keeps the raw inputs; drop them so only CMIP names remain
    return ds.drop_vars(
        [
            var
            for var in ds.data_vars
            if var in dataset and var != cmor_name and not var.endswith("_bnds")
        ]
    )


def to_cube(ds, var):
    """Convert one variable of any CMORised dataset to an iris cube safely."""

    # add latitude/longitude to coordinates ONLY if they exist
    coords_to_set = [
        c for c in ["latitude", "longitude", "lat", "lon"] if c in ds.data_vars
    ]
    if coords_to_set:
        ds = ds.set_coords(coords_to_set)

    # map bounds dynamically based on CMIP6 naming conventions
    bounds_mapping = {
        "latitude": "vertices_latitude",
        "longitude": "vertices_longitude",
        "lat": "lat_bnds",
        "lon": "lon_bnds",
        "time": "time_bnds",
    }

    # link bounds only if both the coordinate and bounds exist
    for coord, bounds in bounds_mapping.items():
        if (coord in ds and bounds in ds) and (
            "bounds" not in ds[coord].attrs and "bounds" not in ds[coord].encoding
        ):
            ds[coord].attrs["bounds"] = bounds

    # Convert
    return cubes_from_xarray(ds).extract_cube(iris.NameConstraint(var_name=var))


def extract_dataset(
    ds, var, start_longitude=190, end_longitude=240, start_latitude=-5, end_latitude=5
):
    cube = to_cube(ds, var)
    return xr.DataArray.from_iris(
        esmvalcore.preprocessor.extract_region(
            cube, start_longitude, end_longitude, start_latitude, end_latitude
        )
    ).to_dataset(name=var)


def area_statistics(ds, var, operator):
    cube = to_cube(ds, var)
    return xr.DataArray.from_iris(
        esmvalcore.preprocessor.area_statistics(cube, operator)
    ).to_dataset(name=var)


def analyse_and_plot(dataset: xr.Dataset, recipe_func, **recipe_kwargs) -> plt.Figure:
    """
    Executes a chosen recipe on the dataset and plots the result.
    **recipe_kwargs allows the user to pass specific arguments (like variable or depth) to the recipe.
    """
    # 1. Execute the chosen recipe function, unpacking any extra arguments
    result_data = recipe_func(dataset, **recipe_kwargs)

    # 2. Plotting logic
    fig, ax = plt.subplots(figsize=(10, 5))

    # If it's a 1D timeseries
    if len(result_data.dims) == 1:
        result_data.plot(ax=ax, linewidth=2)
    # If it's 2D (like a Hovmöller diagram or a Zonal Mean over Latitude)
    elif len(result_data.dims) == 2:
        result_data.plot(ax=ax, cmap="viridis")

    ax.set_title(result_data.name or "Diagnostic Output")
    plt.tight_layout()
    return fig
