.DEFAULT_GOAL := pdf
.PHONY: pdf rebuild

# Einstellungen für latexmk stehen in Report/.latexmkrc.
pdf:
	cd Report && latexmk

rebuild:
	cd Report && latexmk -g
