$pdf_mode = 1;
$out_dir = 'build';
$pdflatex = 'pdflatex -interaction=nonstopmode -halt-on-error -file-line-error %O %S';
@default_files = ('main.tex');
use File::Path qw(make_path);
make_path("$out_dir/sections");
