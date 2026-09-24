import json
import warnings
from functools import lru_cache
from importlib.resources import files

import numpy as np
import pandas as pd
import xarray as xr
from access_moppy import ACCESS_ESM_CMORiser
from access_moppy.ocean import Ocean_CMORiser, Ocean_CMORiser_OM3

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# model_type -> (moppy mapping file model_id, CV-valid source_id).
# moppy validates source_id against the CMIP6 CVs, which have no CM3/OM3/ESM1.6
# entries, so the closest registered ACCESS model is used. The source_id only
# ends up in the output metadata; the mapping file drives the actual conversion.
ACCESS_MODEL_TYPES = {
    "ACCESS-ESM1.6": ("ACCESS-ESM1-6", "ACCESS-ESM1-5"),
    "ACCESS-CM3": ("ACCESS-CM3", "ACCESS-CM2"),
    "ACCESS-OM3": ("ACCESS-OM3", "ACCESS-CM2"),
    # No OM2 mapping file ships with moppy; ESM1.6's ocean is MOM5, as in OM2
    "ACCESS-OM2": ("ACCESS-ESM1-6", "ACCESS-OM2"),
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

# moppy mapping component -> {CMIP frequency: CMIP6 tables to look in, in order}.
# Only tables moppy's driver can dispatch are listed.
REALM_TABLES = {
    "atmosphere": {
        "mon": ["Amon", "Emon", "CFmon", "AERmon"],
        "day": ["day", "Eday", "CFday", "AERday"],
        "6hr": ["6hrPlev"],
        "3hr": ["3hr"],
        "1hr": ["E1hr"],
    },
    "aerosol": {"mon": ["AERmon"], "day": ["AERday"]},
    "land": {"mon": ["Lmon", "Emon"], "day": ["Eday"]},
    "landIce": {"mon": ["LImon"]},
    "ocean": {"mon": ["Omon"], "day": ["Oday"], "yr": ["Oyr"]},
    "oceanBgchem": {"mon": ["Omon"], "day": ["Oday"], "yr": ["Oyr"]},
    "sea_ice": {"mon": ["SImon"], "day": ["SIday"]},
}

# (CMIP frequency, largest median time step in days that still counts as it)
FREQUENCY_MAX_DAYS = [
    ("1hr", 0.05),
    ("3hr", 0.15),
    ("6hr", 0.3),
    ("day", 1.5),
    ("mon", 40),
    ("yr", 400),
]


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


def _infer_frequency(dataset):
    """Return the CMIP frequency (``"mon"``, ``"day"``, ...) of ``dataset.time``."""
    if "time" not in dataset.dims or dataset.sizes["time"] < 2:
        return None
    # Median spacing, since month lengths vary and cftime breaks xr.infer_freq
    step = pd.to_timedelta(np.diff(dataset["time"].values)).median().total_seconds()
    for frequency, max_days in FREQUENCY_MAX_DAYS:
        if step / 86400 <= max_days:
            return frequency
    return None


@lru_cache
def _cmip6_table_variables(table):
    """Return the variable names defined in CMIP6 table ``table``."""
    path = files("access_moppy") / "vocabularies/cmip6_cmor_tables/Tables"
    return set(json.loads((path / f"CMIP6_{table}.json").read_text())["variable_entry"])


def _find_compound_names(dataset, model_id, is_mom5_scalar):
    """List every CMIP6 ``table.variable`` that can be built from ``dataset``."""
    frequency = _infer_frequency(dataset)
    if is_mom5_scalar:
        candidates = [
            ("ocean", cmor_name)
            for cmor_name, var in MOM5_SCALAR_VARIABLES.items()
            if var in dataset.variables
        ]
    else:
        mapping_file = files("access_moppy.mappings") / f"{model_id}_mappings.json"
        mappings = json.loads(mapping_file.read_text())
        candidates = [
            (component, cmor_name)
            for component, entries in mappings.items()
            if component in REALM_TABLES
            for cmor_name, entry in entries.items()
            # Entries without model_variables are fixed fields built from files
            # bundled with moppy, so they'd match every dataset
            if entry["model_variables"]
            and all(var in dataset.variables for var in entry["model_variables"])
            # calculate_monthly_* (tasmax/tasmin) needs sub-monthly input, so a
            # monthly field would be relabelled as its own max/min
            and '"calculate_monthly_' not in json.dumps(entry["calculation"])
        ]

    compound_names = []
    for component, cmor_name in candidates:
        tables = REALM_TABLES[component].get(frequency, [])
        table = next(
            (t for t in tables if cmor_name in _cmip6_table_variables(t)), None
        )
        if table:
            compound_names.append(f"{table}.{cmor_name}")
    return compound_names


def _cmorise_variable(
    dataset,
    compound_name,
    model_type,
    model_id,
    source_id,
    is_mom5_scalar,
    write_output,
    **kwargs,
):
    """CMORise one ``table.variable`` with ``ACCESS_ESM_CMORiser``."""
    cmoriser = ACCESS_ESM_CMORiser(
        input_data=dataset,
        compound_name=compound_name,
        source_id=source_id,
        model_id=model_id,
        **kwargs,
    )

    # moppy only picks its MOM6 ocean CMORiser when source_id == "ACCESS-OM3"
    # (invalid in the CMIP6 CVs) or model_id == "ACCESS-CM3". OM3 therefore lands
    # on the MOM5/B-grid CMORiser, so swap in the C-grid one with the same inputs.
    table, cmor_name = cmoriser.cmip6_compound_name.split(".")
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
    elif is_mom5_scalar and cmor_name in MOM5_SCALAR_VARIABLES:
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
        cmorised = cmoriser.to_dataset()
    # Newer moppy keeps the raw model inputs; drop them so only CMIP names remain
    leftovers = [
        var
        for var in cmorised.data_vars
        if var in dataset.data_vars and var != cmor_name and not var.endswith("_bnds")
    ]
    return cmorised.drop_vars(leftovers)


def cmorise_data(
    dataset,
    model_type,
    compound_names=None,
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
    CMORise an ACCESS model dataset into one dataset of CMIP6 variables.

    Parameters
    ----------
    dataset : xr.Dataset
        Raw model output.
    model_type : str
        One of ``ACCESS_MODEL_TYPES`` (loose spellings like ``"om3"`` are accepted).
    compound_names : str or list of str, optional
        CMIP6 ``table.variable`` names to produce, e.g. ``"Omon.tos"``. Defaults
        to every variable moppy can build from ``dataset``.
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
    model_id, source_id = ACCESS_MODEL_TYPES[model_type]

    is_mom5_scalar = (
        model_type not in MOM6_MODEL_TYPES and "scalar_axis" in dataset.dims
    )
    if is_mom5_scalar:
        # Every variable re-reads the source files otherwise; a timeseries is tiny
        dataset = dataset.load()
        if "time_bounds" in dataset.variables:
            # moppy looks for <dim>_bnds; MOM5 writes time_bounds
            dataset = dataset.rename({"time_bounds": "time_bnds"})

    discover = compound_names is None
    if discover:
        compound_names = _find_compound_names(dataset, model_id, is_mom5_scalar)
        if not compound_names:
            raise ValueError(
                f"No CMIP6 variables in the {model_type} mapping can be built "
                f"from this dataset's variables: {sorted(dataset.data_vars)}."
            )
    elif isinstance(compound_names, str):
        compound_names = [compound_names]

    kwargs = dict(
        experiment_id=experiment_id,
        variant_label=variant_label,
        grid_label=grid_label,
        activity_id=activity_id,
        parent_info=parent_info,
        output_path=output_path,
        **cmoriser_kwargs,
    )
    cmorised, failed = [], {}
    for compound_name in compound_names:
        try:
            cmorised.append(
                _cmorise_variable(
                    dataset,
                    compound_name,
                    model_type,
                    model_id,
                    source_id,
                    is_mom5_scalar,
                    write_output,
                    **kwargs,
                )
            )
        except Exception as err:
            # Names asked for explicitly must succeed; discovered ones are best effort
            if not discover:
                raise
            failed[compound_name] = f"{type(err).__name__}: {err}"
    if failed:
        warnings.warn(f"Could not CMORise {failed}", stacklevel=2)
    if not cmorised:
        raise RuntimeError(f"Every variable failed to CMORise: {failed}")

    try:
        # Only per-variable attrs (variable_id, tracking_id) conflict; drop them
        return xr.merge(cmorised, combine_attrs="drop_conflicts")
    except xr.MergeError as err:
        raise ValueError(
            "CMORised variables have conflicting coordinates (e.g. T- and U-grid "
            "ocean variables); pass compound_names for one grid at a time."
        ) from err


def add_function(func):
    print("add function to UI dropdown options.")
