---
# Use plain text in the title; do not use backticks for code formatting.
title: 'Model-Live Diagnostics: A Python package for monitoring live climate-model output'
tags:
  - Python
  - name: Theo A. Ellingsen
    orcid: 0000-0002-1839-5392
    affiliation: "1, 2"
  - name: Lachlan Whyborn
    orcid: 0000-0000-0000-0000
    affiliation: 1
  - name: Charles Turner
    orcid: 0000-0000-0000-0000
    affiliation: 1
  - name: Mike Tetley
    orcid: 0000-0000-0000-0000
    corresponding: true
    affiliation: 1
affiliations:
 - name: ACCESS-NRI, Australian National University, Canberra, Australia
   index: 1
 - name: University of Tasmania, Hobart, Australia
   index: 2
date: x/x/x 
bibliography: paper.bib

---

# Summary
Climate model simulations can run for days to months on high-performance computing systems and produce large volumes of output. This makes it both vital and difficult to check whether a simulation is behaving as expected while it is still running. Model Live Diagnostics (MLD) is a Python package that addresses this by providing interactive tools for inspecting model output during a run. It allows researchers and model developers to monitor, evaluate and troubleshoot simulations as they progress, so that problems are identified earlier, less compute time is wasted, and model development is more efficient.

MLD can be installed with pip or conda and provides a graphical interface, built with Panel [@panel], that runs in Jupyter notebooks. It is available in the Australian Research Environment (ARE) on Gadi, the supercomputer operated by Australia's National Computational Infrastructure (NCI).



# Statement of need

# State of the field                                                                                                                  


# Software design


# Research impact statement

# Citations

Citations to entries in paper.bib should be in
[rMarkdown](http://rmarkdown.rstudio.com/authoring_bibliographies_and_citations.html)
format.

If you want to cite a software repository URL (e.g. something on GitHub without a preferred
citation) then you can do it with the example BibTeX entry below for @fidgit.

For a quick reference, the following citation commands can be used:
- `@author:2001`  ->  "Author et al. (2001)"
- `[@author:2001]` -> "(Author et al., 2001)"
- `[@author1:2001; @author2:2001]` -> "(Author1 et al., 2001; Author2 et al., 2002)"

# Figures

Figures can be included like this:
![Caption for example figure.\label{fig:example}](figure.png)
and referenced from text using \autoref{fig:example}.

Figure sizes can be customized by adding an optional second parameter:
![Caption for example figure.](figure.png){ width=20% }

# AI usage disclosure

Generative AI tools were used during the development of MLD. Claude Code (Anthropic), using the Claude Sonnet 5.5 and Claude Opus 5.5 models, was used to help extend and improve the existing test suite, assist with debugging, review code, draft and edit documentation, and edit the language of this paper. GitHub Copilot was used for automated pull-request review, and some of its suggestions were applied. All design and architectural decisions were made by the authors, and all AI-assisted changes were reviewed by the authors.


# Acknowledgements

# References
