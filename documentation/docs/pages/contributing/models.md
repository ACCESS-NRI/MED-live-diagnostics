# Adding support for a new model type

The model type chosen in the **Select model type** dropdown when starting a session controls two things:

- **How the live model output is catalogued.** MLD builds an intake-esm datastore of your run with one of the [ACCESS-NRI Intake Catalog](https://github.com/ACCESS-NRI/access-nri-intake-catalog) datastore builders.
- **Which reference models are offered.** The ACCESS-NRI Intake Catalog is searched for experiments of the same model.

Adding a new model type means wiring up both, then testing and documenting it.

## Before you start

Model types are contributed through the same git workflow as any other code, which is described in full in [Contributing code](code.md). Open an [issue](https://github.com/ACCESS-NRI/MED-live-diagnostics/issues/new/choose) for the new model type, then fork the repository and create a branch from `main`.

MLD doesn't read model output itself, so the model needs a datastore builder in `access_nri_intake.source.builders` (e.g. `AccessOm3Builder`, `Mom6Builder`). If there isn't one yet, it has to be added to [access-nri-intake-catalog](https://github.com/ACCESS-NRI/access-nri-intake-catalog) first. Check that the builder works on some real output of the model before going further, e.g.:

```python
import os
from access_nri_intake.experiment import use_datastore
from access_nri_intake.source.builders import NewModelBuilder

use_datastore(
    experiment_dir="path/to/model/output",
    catalog_dir=os.getcwd(),
    builder=NewModelBuilder,
    datastore_name="test_catalog",
    description="Test catalog",
)
```

## 1. Map the model type to its builder

In `src/med_diagnostics/data.py`, `_build_new_catalog()` matches the model type to a builder:

1. Import the builder at the top of `data.py`.
2. Add a `case` to the `match model_type:` statement. Use a short lowercase name without punctuation, matching the existing ones (`cm2`, `om3`, `esm16`, `mom6`). The session lowercases `model_type`, so it can be passed in any case.
3. If the builder takes an `ensemble` argument (as the CM and ESM builders do), add it to the list that sets `{"ensemble": False}`. A live run is a single experiment, not an ensemble.

```python
match model_type:
    ...
    case "newmodel":
        model_type_builder = NewModelBuilder
```

Then add the model type to the `options` of `model_type_dropdown` in `UserInterface.__init__()` in `src/med_diagnostics/ui.py`, so users can select it when starting a session.

## 2. Check the reference models

`_load_access_nri_catalog()` in `data.py` filters the ACCESS-NRI Intake Catalog to the exact model names listed for the model type in `CATALOG_MODEL_NAMES`, at the top of `data.py`:

```python
CATALOG_MODEL_NAMES = {
    ...
    "esm15": ["ACCESS-ESM1-5"],
    "newmodel": ["ACCESS-NEWMODEL"],
}
```

Add an entry for the new model type, listing the names its reference runs have in the catalog's `model` column. To see the names in the catalog:

```python
import intake

intake.cat.access_nri.df["model"].unique()
```

The names are matched exactly, so similar names (e.g. `GFDL-CM3` for `CM3`) are not picked up. A model type can list related models too: `om3` lists the ACCESS-OM2 and MOM6 runs, as there are no ACCESS-OM3 runs in the catalog yet. If there are no suitable runs, use an empty list; the reference model sections will be empty, but the user data and analysis sections still work.

## 3. Test it

1. In `tests/test_data.py`, add the new model type to:
    - the `parametrize` list of `test_build_new_catalog_valid_models`, with its builder and expected `builder_kwargs`,
    - the `parametrize` list of `test_load_access_nri_catalog_finds_only_its_models`, with the catalog models it should find (adding its names to `CATALOG_MODELS` if they aren't there),
    - the list in `test_every_model_type_has_catalog_names`.
2. Run the tests (see [Contributing code](code.md)).
3. Start a session on real output of the model in ARE and check that the catalogue builds, datasets load and plot (including the **Years to load** options), reference models are listed, and the built-in recipes you'd expect to work on it do.

## 4. Document it

Add the new model type everywhere the supported model types are listed:

- the `model_type` docstrings in `session.py` and `data.py`
- the supported models sentence in "What does this package do?" on the [home page](../index.md)

If built-in recipes support the new model, say so in their **Targets** column and notes in [Built-in analysis recipes](../tutorials/built_in_recipes_tutorial.md).

Then open a pull request as described in [Contributing code](code.md).
