# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD  ?= sphinx-build
SOURCEDIR    = source
BUILDDIR     = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Custom targets / Alvos personalizados
html-pt:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html-pt" -D language=pt_BR

html-en:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html-en" -D language=en

deploy-gh-pages:
	cd $(BUILDDIR)/html && git init && git add -A && git commit -m "docs: deploy" && git push -f https://github.com/Colombiano/Alakoro_FiberSense.git HEAD:gh-pages
