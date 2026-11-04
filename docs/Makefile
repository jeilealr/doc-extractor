# Build the documentation locally:  make -C docs html   then open docs/_build/html/index.html
SPHINXOPTS    ?= -W --keep-going
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = _build

.PHONY: help html clean livehtml
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

html:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
	@echo "Open $(CURDIR)/$(BUILDDIR)/html/index.html"

clean:
	rm -rf "$(BUILDDIR)" "$(SOURCEDIR)/_generated" "$(SOURCEDIR)/reference/generated"
