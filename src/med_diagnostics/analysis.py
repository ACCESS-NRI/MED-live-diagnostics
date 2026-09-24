import numpy as np
from access_moppy import ACCESS_ESM_CMORiser
from access_moppy.ocean import Ocean_CMORiser

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


# ---------------------------------------------------------------------------
# CMORisation
# ---------------------------------------------------------------------------


class _ScalarOceanCMORiser(Ocean_CMORiser):
    """``Ocean_CMORiser`` for global-mean timeseries, which have no horizontal grid."""

    def infer_grid_type(self):
        return None, None

    def _get_dim_rename(self):
        return {}

    def select_and_process_variables(self):
        super().select_and_process_variables()
        if "scalar_axis" in self.ds.dims:
            self.ds = self.ds.squeeze("scalar_axis", drop=True)

    def update_attributes(self):
        # Ocean_CMORiser.update_attributes minus the supergrid lat/lon/vertices
        self.ds.attrs = {
            k: v
            for k, v in self.vocab.get_required_global_attributes().items()
            if v not in (None, "")
        }
        if "nv" in self.ds.dims:
            self.ds = self.ds.rename_dims({"nv": "bnds"}).rename_vars({"nv": "bnds"})
            self.ds["bnds"].attrs.update(
                {"long_name": "vertex number of the bounds", "units": "1"}
            )
        cmor_attrs = self.vocab.variable
        self.ds[self.cmor_name].attrs.update(
            {k: v for k, v in cmor_attrs.items() if v not in (None, "")}
        )
        var_type = cmor_attrs.get("type", "double")
        self.ds[self.cmor_name] = self.ds[self.cmor_name].astype(
            self.type_mapping.get(var_type, np.float64)
        )
        if "time" in self.ds.dims:
            self._check_calendar("time")

    def write(self):
        # moppy's chunked writer hands dask datetime64 time_bnds to netCDF4
        # unencoded ("cannot include dtype 'M'"); a timeseries is tiny, so load it
        self.ds = self.ds.load()
        super().write()


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
    if is_scalar and "time_bounds" in dataset.variables:
        # moppy looks for <dim>_bnds; MOM5 writes time_bounds
        dataset = dataset.rename({"time_bounds": "time_bnds"})

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
        cmoriser.cmoriser = _ScalarOceanCMORiser(
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


def add_function(func):
    print("add function to UI dropdown options.")
