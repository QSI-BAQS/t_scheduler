from tests.test_static_buffer import StaticBufferTest

combine_template = r"""
%!TEX options=--shell-escape
\documentclass[multi=page]{standalone}
\usepackage{tikz}
\setlength{\parindent}{0cm}
\setlength{\parskip}{1em}
\def\offset{0.1}
\begin{document}
\foreach \i in {1, 2, ..., 97} {
\begin{page}
    \includegraphics{\i}
\end{page}
}
\end{document}
"""

animate_template = r"""
%!TEX options=--shell-escape
\documentclass[multi=page]{standalone}
\usepackage{tikz}
\usepackage{animate}
\setlength{\parindent}{0cm}
\setlength{\parskip}{1em}
\def\offset{0.1}
\begin{document}
\begin{page}
    \animategraphics[autoplay,loop]{7}{combine}{1}{%s}
\end{page}
\end{document}
"""

funcs = [
    # StaticBufferTest.test_end_to_end_inject_vertical,
    # StaticBufferTest.test_end_to_end_backprop_vertical,
    # StaticBufferTest.test_end_to_end_2,
    # StaticBufferTest.test_vertical_toffoli,
    # StaticBufferTest.test_tree_qft,
    # StaticBufferTest.test_flat_naive_qft,
    # StaticBufferTest.test_litinski_5x3_qft,
    # StaticBufferTest.test_litinski_6x3_qft,
    StaticBufferTest.test_litinski_6x3_buffered_qft,
]


if __name__ == '__main__':
    import subprocess
    import shutil
    import os
    import sys
    import re
    
    if not os.path.isdir('tikz_output'):
        os.mkdir('tikz_output')
    if len(sys.argv) > 1:
        try:
            os.remove('check.out')
        except: pass
        try:
            shutil.rmtree('out')
        except: pass
        os.mkdir('out')
        StaticBufferTest().__getattribute__(sys.argv[1])(True) # type: ignore
        exit(0)

    for func in funcs:
        try:
            shutil.rmtree('out')
        except: pass
        os.mkdir('out')
        func(None, True)  # type: ignore

        command = ['powershell', '-executionpolicy',
                   'bypass', '-File', './compile_tikz.ps1']
        result = subprocess.run(
            command, stdout=sys.stdout, stderr=subprocess.PIPE)

        if result.returncode != 0:
            raise Exception('Tex compile failed!')

        # Pattern to match files like <num>.pdf
        pattern = re.compile(r"(\d+)\.pdf")

        max_frame = max(int(match.group(1)) for match in (
            pattern.match(filename) for filename in os.listdir('out')) if match)

        with open('out/combine.tex', 'w') as f:
            print(combine_template.replace("%s", str(max_frame)), file=f)

        with open('out/animate.tex', 'w') as f:
            print(animate_template.replace("%s", str(max_frame)), file=f)

        os.chdir('out')

        command = "pdflatex -interaction=nonstopmode combine.tex".split()
        result = subprocess.run(
            command, stdout=None, stderr=None)

        if result.returncode != 0:
            raise Exception('Tex combine compile failed!')
        
        command = "pdflatex -interaction=nonstopmode animate.tex".split()
        result = subprocess.run(
            command, stdout=None, stderr=None)

        if result.returncode != 0:
            raise Exception('Tex animate compile failed!')
        
        command = "pdflatex -interaction=nonstopmode animate.tex".split()
        result = subprocess.run(
            command, stdout=None, stderr=None)

        if result.returncode != 0:
            raise Exception('Tex animate recompile failed!')
        
        shutil.move('animate.pdf', f"../tikz_output/{func.__name__}.pdf")
        os.chdir('..')
        shutil.rmtree('out')
