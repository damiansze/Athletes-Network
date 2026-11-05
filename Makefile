.DEFAULT_GOAL := pdf
.PHONY: pdf rebuild

pdf rebuild:
	$(MAKE) -C Report $@
