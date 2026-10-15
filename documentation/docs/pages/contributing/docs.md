# Contributing documentation

Adding documentation is always helpful. This may include:

- Extending or clarifying existing documentation.
- Adding examples of Model Live Diagnostics being used for live monitoring or analysis.
- Improving docstrings, including adding examples.

The documentation is written in Markdown and built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/). Contributions should be submitted via pull requests to the [MED-live-diagnostics repository](https://github.com/ACCESS-NRI/MED-live-diagnostics).

## Preview the documentation locally

The documentation dependencies are installed with [pixi](https://pixi.sh). From the root of the repository, start a pixi shell and the local development server:

```bash
pixi shell
cd documentation
mkdocs serve
```

To build the static site, the `resolve-absolute-urls` plugin also needs a site URL, so set `READTHEDOCS_CANONICAL_URL` (any URL works locally):

```bash
pixi shell
cd documentation
READTHEDOCS_CANONICAL_URL=http://localhost/en/latest/ mkdocs build --strict
```

---

[Next: Feature requests and bug reports :material-arrow-right:](issues.md){ .md-button }
