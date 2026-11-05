LATEXMK ?= latexmk
.DEFAULT_GOAL := pdf
.PHONY: pdf rebuild

pdf:
	$(LATEXMK) -pdf main.tex

rebuild:
	$(LATEXMK) -g -pdf main.tex
