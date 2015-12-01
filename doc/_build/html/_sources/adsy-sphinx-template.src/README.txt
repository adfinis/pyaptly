==========================
The Ad-Sy Sphinx templates
==========================

This repository contains templates for the Sphinx-Doc system, both for HTML
and LaTeX output. To use it, you need a few steps to configure sphinx
correctly.

Initializing
============

To initialize a new sphinx-doc documentation, just run the `sphinx-quickstart`
command as usual. Alternatively, copy the files from the `example` folder into
the project folder and start customizing the `conf.py` files.

The following examples assume that you have added the
`adsy-sphinx-template.src` repository either as a submodule or as a regular
checkout in the root directory. In other words, your directory layout should
look like this:

* conf.py
* index.rst
* Makefile
* adsy-sphinx-template.src/

   - html/
   - latex/
   - README.rst (this file)


Configuring LaTeX
=================

To enable the Ad-Sy LaTeX template, add the following to the `conf.py` file:

.. code-block:: python

   latex_additional_files = [
       'adsy-sphinx-template.src/latex/logo.png',
       'adsy-sphinx-template.src/latex/sphinx.sty',
       'adsy-sphinx-template.src/latex/adsy.sty'
   ]


   latex_elements = {
       # The paper size ('letterpaper' or 'a4paper').
       'papersize': 'a4paper',

       # The font size ('10pt', '11pt' or '12pt').
       'pointsize': '10pt',

       # Additional stuff for the LaTeX preamble.
       'preamble' : r"""

           \usepackage{adsy}


           \renewcommand{\subtitle}{%s}

       """ % (project)

   }


Unfortunately, due to the way that Sphinx generates LaTeX, we need some
additional hackery to get it to work with our template: Replace the
`latexpdf` target in the Makefile with the following code to make it work
correctly:

.. code-block:: make

    latexpdf:
    	$(SPHINXBUILD) -b latex $(ALLSPHINXOPTS) $(BUILDDIR)/latex
    	sed -i 's/pdflatex/xelatex/g' $(BUILDDIR)/latex/Makefile
    	sed -i  '/^\\DeclareUnicodeCharacter/d' $(BUILDDIR)/latex/*.tex
    	sed -i  '/\\usepackage{hyperref}/d' $(BUILDDIR)/latex/sphinxmanual.cls
    	sed -i  '/\\usepackage\[Bjarne\]{fncychap}/d' $(BUILDDIR)/latex/*.tex

    	@echo "Running LaTeX files through pdflatex..."
    	$(MAKE) -C $(BUILDDIR)/latex all-pdf
    	@echo "pdflatex finished; the PDF files are in $(BUILDDIR)/latex."


Configuring HTML
================

To enable the Ad-Sy HTML template, add the following to the `conf.py` file:

.. code-block:: python

   # The theme to use for HTML and HTML Help pages.  See the documentation for
   # a list of builtin themes.
   html_theme = "adsy"
   #html_theme_options = {
   #    "rightsidebar": "true",
   #}

   # Theme options are theme-specific and customize the look and feel of a theme
   # further.  For a list of options available for each theme, see the
   # documentation.
   #html_theme_options = {}

   # Add any paths that contain custom themes here, relative to this directory.
   html_theme_path = [ 'adsy-sphinx-template.src/html' ]

