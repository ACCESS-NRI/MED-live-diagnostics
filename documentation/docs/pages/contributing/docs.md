# Contributing documentation

Adding documentation is always helpful. This may include:

- Extending or clarifying existing documentation.
- Adding examples of Model Live Diagnostics being used for live monitoring or analysis.
- Improving docstrings, including adding examples.

The documentation is written in Markdown and built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/). Contributions should be submitted via pull requests to the [MED-live-diagnostics repository](https://github.com/ACCESS-NRI/MED-live-diagnostics).

## Preview the documentation locally

Install the documentation dependencies into a Python environment of your choice (e.g. venv or conda). From the root of the repository:

```bash
pip install -r documentation/requirements.txt
```

!!! tip "Using pixi"
    The repository also includes a [pixi](https://pixi.sh) workspace with these dependencies. If you use pixi, run `pixi shell` from the root of the repository instead of installing them yourself.

Then start the local development server:

```bash
cd documentation
mkdocs serve
```

To build the static site, the `resolve-absolute-urls` plugin also needs a site URL, so set `READTHEDOCS_CANONICAL_URL` (any URL works locally):

```bash
cd documentation
READTHEDOCS_CANONICAL_URL=http://localhost/en/latest/ mkdocs build --strict
```

