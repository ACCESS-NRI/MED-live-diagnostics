# Contributing code

Contributions to the code are welcome. If you would like to contribute, start by opening an [issue](https://github.com/ACCESS-NRI/MED-live-diagnostics/issues/new/choose) describing what you would like to change and why. Repository maintainers may discuss the issue with you before inviting you to submit a pull request.

## Submitting pull requests

1. Fork this repository.
2. Clone your fork locally, connect it to the upstream repository, and create a branch for your work. Include the issue number in the branch name when appropriate:

    ```bash
    git clone git@github.com:YOUR_GITHUB_USERNAME/MED-live-diagnostics.git
    cd MED-live-diagnostics
    git remote add upstream git@github.com:ACCESS-NRI/MED-live-diagnostics.git
    git checkout -b <issue#_description> main
    ```

    This example assumes that you have [SSH keys configured for GitHub](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent). If you do not, replace `git@github.com:` with `https://github.com/`.


3. Make your code changes and test them. The development tools are installed with [pixi](https://pixi.sh), so run the tests and linting through it:

    ```bash
    pixi run test-cov
    pixi run pre-commit run --all-files
    ```

4. Commit your edits, including docstrings, documentation updates, and unit tests. Please follow [numpydoc style](https://numpydoc.readthedocs.io/en/latest/format.html) for docstrings where possible.

5. Open a pull request against the `main` branch of the [MED-live-diagnostics repository](https://github.com/ACCESS-NRI/MED-live-diagnostics/pulls).
