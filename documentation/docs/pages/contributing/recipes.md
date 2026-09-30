# Contributing recipes

If you have written a custom analysis that would be useful to others, you can contribute it as a built-in recipe. Built-in recipes appear in the analysis dropdown for every user, without needing to be uploaded.

Before starting, read the [Adding custom analyses](../../notebooks/adding_custom_analyses.ipynb) tutorial. A built-in recipe follows exactly the same rules as a custom one.

## Before you start

Recipes are contributed through the same git workflow as any other code, which is described in full in [Contributing code](code.md). Follow it to set up your copy of the repository before writing your recipe:

1. Open an [issue](https://github.com/ACCESS-NRI/MED-live-diagnostics/issues/new/choose) describing the recipe and what it is for.
2. Fork the repository, clone your fork, and create a branch for your recipe from `main`:

    ```bash
    git clone git@github.com:YOUR_GITHUB_USERNAME/MED-live-diagnostics.git
    cd MED-live-diagnostics
    git remote add upstream git@github.com:ACCESS-NRI/MED-live-diagnostics.git
    git checkout -b <issue#_recipe_name> main
    ```

## From custom to built-in recipe

Built-in recipes live in `src/med_diagnostics/recipes.py`. To turn a custom recipe into a built-in one:

1. Add your function under the `# Recipes` section of `recipes.py`.
2. Name it with a `recipe_` prefix (e.g. `recipe_mixed_layer_depth`). MLD finds built-in recipes by this prefix.
3. Remove the `@analysis.upload_analysis` decorator. It is only needed for recipes defined in a notebook.

The first line of the docstring becomes the dropdown label (without the `Custom:` prefix), and the second paragraph is shown as the recipe's details.

## Requirements

On top of the [checklist](../../notebooks/adding_custom_analyses.ipynb#checklist) in the tutorial, a built-in recipe must:

- Give every argument a `"kind"` and a `"description"`. This is checked by `tests/test_recipes.py`.
- State in the docstring's second paragraph which model or grid it targets (e.g. `For MOM5 output (ACCESS-OM2, ACCESS-ESM1.6).`).
- Fail with a readable error on the wrong grid. You can write your own check, or use the `_require_coords` helper.
- Reuse the existing helpers where possible, such as `extract_region`, `PREDEFINED_REGIONS`, and the functions in `plot_customisations`. If you write a helper that other recipes could use, add it to the helpers section of `recipes.py` with a numpy-style docstring.
- Put any `customise` functions your recipe uses in `src/med_diagnostics/plot_customisations.py`, rather than defining them inside `recipes.py`. Where possible they should take `(ax, data)` like the existing functions there. If one needs extra settings (like `add_threshold`), wrap it in a `lambda` inside the recipe. Give each one a short docstring so it appears in the [API reference](../api.md).
- Call `.compute()` on the result before returning it if any `customise` function reads the data.

## Testing

`tests/test_recipes.py` automatically checks the annotations of every `recipe_*` function, so you do not need to register your recipe there. If your recipe or helper has logic that could break (e.g. region selection or time handling), add a test using a small synthetic `xarray.Dataset`.

Run the tests and linting before opening a pull request:

```bash
pixi run test-cov
pixi run pre-commit run --all-files
```

## Submitting

Once your recipe and any tests pass:

1. Commit your changes and push the branch to your fork:

    ```bash
    git add src/med_diagnostics/recipes.py tests/test_recipes.py
    git commit -m "Add <recipe name> recipe"
    git push origin <issue#_recipe_name>
    ```

2. Open a pull request against the `main` branch of the [MED-live-diagnostics repository](https://github.com/ACCESS-NRI/MED-live-diagnostics/pulls). In the description, link the issue and include which models or grids you tested the recipe on, plus a screenshot of its plot.

If `main` has moved on while you are working, update your branch with `git fetch upstream` followed by `git rebase upstream/main`.
