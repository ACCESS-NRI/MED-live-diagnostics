# Contributing documentation

Adding documentation is always helpful. This may include:

- Extending or clarifying existing documentation.
- Adding examples of Model Live Diagnostics being used for live monitoring or analysis.
- Improving docstrings, including adding examples.

The documentation is written in Markdown and built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/). Contributions should be submitted via pull requests to the [MED-live-diagnostics repository](https://github.com/ACCESS-NRI/MED-live-diagnostics).

## Preview the documentation locally

Install the documentation dependencies and start the local development server:

```bash
cd documentation
pip install -r requirements.txt
mkdocs serve
```

Build the static site with:

```bash
cd documentation
mkdocs build --strict
```
