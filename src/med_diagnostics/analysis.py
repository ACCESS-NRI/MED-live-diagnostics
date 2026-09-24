import numpy as np
from access_moppy import ACCESS_ESM_CMORiser
from access_moppy.ocean import Ocean_CMORiser, Ocean_CMORiser_OM3
from access_moppy.utilities import _model_mapping_file_exists

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# model_type -> (moppy mapping file model_id, CV-valid source_id).
# moppy validates source_id against the CMIP6 CVs, which have no CM3/OM3/ESM1.6
# entries, so the closest registered ACCESS model is used. The source_id only
# ends up in the output metadata; the mapping file drives the actual conversion.
ACCESS_MODEL_TYPES = {
    "ACCESS-ESM1.6": ("ACCESS-ESM1.6", "ACCESS-ESM1-5"),
    "ACCESS-CM3": ("ACCESS-CM3", "ACCESS-CM2"),
    "ACCESS-OM3": ("ACCESS-OM3", "ACCESS-CM2"),
    # No OM2 mapping file ships with moppy; ESM1.6's ocean is MOM5, as in OM2
    "ACCESS-OM2": ("ACCESS-ESM1.6", "ACCESS-OM2"),
}


# Models whose ocean is MOM6 on a C-grid, needing moppy's OM3 ocean CMORiser
MOM6_MODEL_TYPES = {"ACCESS-OM3", "ACCESS-CM3"}
OCEAN_TABLES = {"Oyr", "Oday", "Omon", "Ofx"}

# CMIP6 name -> MOM5 variable in the ``ocean_scalar`` output (dims time, scalar_axis).
# moppy's own mappings for these derive the global mean from gridded 3D fields,
# but MOM5 already writes it, in CMIP units, so a direct rename is enough.
MOM5_SCALAR_VARIABLES = {
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


def _mom5_scalar_mapping(cmor_name, units):
    """Build a moppy mapping entry that renames a MOM5 scalar onto ``cmor_name``."""
    return {
        cmor_name: {
            "dimensions": {"time": "time"},
            "units": units,
            "positive": None,
            "model_variables": [MOM5_SCALAR_VARIABLES[cmor_name]],
            "calculation": {"type": "direct"},
        }
    }


def _normalise_model_type(model_type):
    """Map loose spellings (``"om3"``, ``"ESM1-6"``) onto ``ACCESS_MODEL_TYPES`` keys."""
    key = model_type.strip().upper().replace("_", "-")
    if not key.startswith("ACCESS-"):
        key = f"ACCESS-{key}"
    key = key.replace("ESM1-6", "ESM1.6")
    if key not in ACCESS_MODEL_TYPES:
        raise ValueError(
            f"Unknown model_type {model_type!r}. "
            f"Expected one of {sorted(ACCESS_MODEL_TYPES)}."
        )
    return key


def _mapping_model_id(model_id):
    """Return the ``model_id`` spelling whose mapping file this moppy version ships."""
    # moppy >1.2.6 renamed ACCESS-ESM1.6_mappings.json to ACCESS-ESM1-6_mappings.json
    for candidate in (model_id, model_id.replace(".", "-")):
        if _model_mapping_file_exists(candidate):
            return candidate
    return model_id


def cmorise_data(
    dataset,
    compound_name,
    model_type,
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
    dataset : xr.Dataset, xr.DataArray, str or list of str
        Raw model output, in memory or as NetCDF path(s).
    compound_name : str
        CMIP6 ``table.variable`` to produce, e.g. ``"Amon.tas"`` or ``"Omon.tos"``.
    model_type : str
        One of ``ACCESS_MODEL_TYPES`` (loose spellings like ``"om3"`` are accepted).
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
        The CMORised dataset.
    """
    model_type = _normalise_model_type(model_type)
    model_id, source_id = ACCESS_MODEL_TYPES[model_type]
    model_id = _mapping_model_id(model_id)

    cmor_name = compound_name.split(".")[-1]
    is_mom5_scalar = (
        model_type not in MOM6_MODEL_TYPES
        and cmor_name in MOM5_SCALAR_VARIABLES
        and "scalar_axis" in getattr(dataset, "dims", ())
    )
    if is_mom5_scalar and "time_bounds" in dataset.variables:
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

    # moppy only picks its MOM6 ocean CMORiser when source_id == "ACCESS-OM3"
    # (invalid in the CMIP6 CVs) or model_id == "ACCESS-CM3". OM3 therefore lands
    # on the MOM5/B-grid CMORiser, so swap in the C-grid one with the same inputs.
    table = cmoriser.cmip6_compound_name.split(".")[0]
    if model_type in MOM6_MODEL_TYPES and table in OCEAN_TABLES:
        cmoriser.cmoriser = Ocean_CMORiser_OM3(
            input_data=(
                cmoriser.input_dataset
                if cmoriser.input_is_xarray
                else cmoriser.input_paths
            ),
            output_path=str(cmoriser.output_path),
            compound_name=cmoriser.cmip6_compound_name,
            vocab=cmoriser.vocab,
            variable_mapping=cmoriser.variable_mapping.to_dict(),
            drs_root=cmoriser.drs_root,
        )
    elif is_mom5_scalar:
        cmoriser.cmoriser = _ScalarOceanCMORiser(
            input_data=cmoriser.input_dataset,
            output_path=str(cmoriser.output_path),
            compound_name=cmoriser.cmip6_compound_name,
            vocab=cmoriser.vocab,
            variable_mapping=_mom5_scalar_mapping(
                cmor_name, cmoriser.vocab.variable["units"]
            ),
            drs_root=cmoriser.drs_root,
        )

    with cmoriser:
        cmoriser.run(write_output=write_output)
        return cmoriser.to_dataset()


def add_function(func):
    print("add function to UI dropdown options.")
