import json
from importlib.resources import files

import numpy as np
import xarray as xr
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

# moppy mapping component -> {frequency: CMIP6 table}. moppy's mappings don't
# say which table a variable belongs to, so this picks it.
REALM_TABLES = {
    "atmosphere": {"mon": "Amon", "day": "day"},
    "aerosol": {"mon": "AERmon", "day": "AERday"},
    "land": {"mon": "Lmon", "day": "Eday"},
    "landIce": {"mon": "LImon"},
    "ocean": {"mon": "Omon", "day": "Oday", "yr": "Oyr"},
    "oceanBgchem": {"mon": "Omon", "day": "Oday", "yr": "Oyr"},
    "sea_ice": {"mon": "SImon", "day": "SIday"},
}

# MOM5 ocean_scalar variable -> CMIP6 name. moppy's mappings derive these from
# gridded 3D fields, but MOM5 already writes them, in CMIP units.
MOM5_SCALARS = {
    "temp_global_ave": "thetaoga",
    "temp_surface_ave": "tosga",
    "salt_global_ave": "soga",
    "salt_surface_ave": "sosga",
    "total_mass_seawater": "masso",
    "total_volume_seawater": "volo",
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


def _compound_names(dataset, model_id, frequency):
    """Map each buildable ``"table.variable"`` to its MOM5 scalar input (or None)."""
    tables_dir = files("access_moppy") / "vocabularies/cmip6_cmor_tables/Tables"

    def table_for(component, cmor_name):
        table = REALM_TABLES.get(component, {}).get(frequency)
        if table is None:
            return None
        entries = json.loads((tables_dir / f"CMIP6_{table}.json").read_text())
        return table if cmor_name in entries["variable_entry"] else None

    if "scalar_axis" in dataset.dims:
        return {
            f"{table_for('ocean', cmor_name)}.{cmor_name}": raw_var
            for raw_var, cmor_name in MOM5_SCALARS.items()
            if raw_var in dataset
        }

    mapping_file = files("access_moppy.mappings") / f"{model_id}_mappings.json"
    mappings = json.loads(mapping_file.read_text())
    compound_names = {}
    for component, entries in mappings.items():
        if component not in REALM_TABLES:
            continue
        for cmor_name, entry in entries.items():
            table = table_for(component, cmor_name)
            if (
                table
                # Entries without inputs are fixed fields built from files
                # bundled with moppy, so they'd be added to every dataset
                and entry["model_variables"]
                and all(var in dataset for var in entry["model_variables"])
                # calculate_monthly_* (tasmax/tasmin) needs sub-monthly input, so
                # a monthly field would be relabelled as its own max/min
                and "calculate_monthly_" not in json.dumps(entry["calculation"])
            ):
                compound_names[f"{table}.{cmor_name}"] = None
    return compound_names


def cmorise_data(
    dataset,
    model_type,
    frequency="mon",
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
    CMORise every variable moppy can build from ``dataset`` and merge the results.

    Parameters
    ----------
    dataset : xr.Dataset
        Raw model output.
    model_type : str
        One of ``ACCESS_MODEL_TYPES``, e.g. ``"OM2"``.
    frequency : str
        ``"mon"``, ``"day"`` or ``"yr"``; picks each realm's CMIP6 table.
    experiment_id, variant_label, grid_label, activity_id : str
        CMIP metadata; must be valid CMIP6 CV entries.
    parent_info : dict, optional
        Parent experiment metadata. Defaults to moppy's piControl parent.
    write_output : bool
        Also write one CMORised NetCDF per variable to ``output_path``.
    **cmoriser_kwargs
        Passed straight to ``ACCESS_ESM_CMORiser`` (e.g. ``enable_resampling``).

    Returns
    -------
    xr.Dataset
        The CMORised variables, merged.
    """
    if model_type not in ACCESS_MODEL_TYPES:
        raise KeyError(
            f"Unknown model_type {model_type!r}. Expected one of {list(ACCESS_MODEL_TYPES)}."
        )
    model_id, source_id = ACCESS_MODEL_TYPES[model_type]
    compound_names = _compound_names(dataset, model_id, frequency)
    if not compound_names:
        raise ValueError(
            f"No {frequency} {model_type} mapping in moppy can be built from "
            f"{sorted(dataset.data_vars)}."
        )

    if "scalar_axis" in dataset.dims:
        # Every variable re-reads the source files otherwise; a timeseries is tiny
        dataset = dataset.load()
        if "time_bounds" in dataset.variables:
            # moppy looks for <dim>_bnds; MOM5 writes time_bounds
            dataset = dataset.rename({"time_bounds": "time_bnds"})

    cmorised = []
    for compound_name, scalar_var in compound_names.items():
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
        cmor_name = compound_name.split(".")[1]

        if scalar_var:
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
        cmorised.append(
            ds.drop_vars(
                [
                    var
                    for var in ds.data_vars
                    if var in dataset and var != cmor_name and not var.endswith("_bnds")
                ]
            )
        )

    # Only per-variable attrs (variable_id, tracking_id) conflict; drop them
    return xr.merge(cmorised, combine_attrs="drop_conflicts")


def add_function(func):
    print("add function to UI dropdown options.")
