# arbok_driver 🐍⚡️
[![Documentation Status](https://readthedocs.org/projects/arbok-driver/badge/?version=latest)](https://arbok-driver.readthedocs.io/en/latest/index.html)
[![PyPI](https://img.shields.io/pypi/v/arbok-driver.svg)](https://pypi.org/project/arbok-driver/)
[![License](https://img.shields.io/github/license/andncl/arbok_driver.svg)](LICENSE)
[![Coverage](https://codecov.io/gh/andncl/arbok_driver/graph/badge.svg)](https://codecov.io/gh/andncl/arbok_driver)
[![Python](https://img.shields.io/pypi/pyversions/arbok-driver.svg)](https://pypi.org/project/arbok-driver/)

A dynamically generated [QCoDeS](https://github.com/microsoft/Qcodes) instrument for your FPGA based measurements using the Quantum Machines [OPX+](https://www.quantum-machines.co/products/opx/)/[OPX1000](https://www.quantum-machines.co/products/opx1000/).

## Features 🛠️
- **Abstraction:** In contrast to traditional static QCoDeS instruments with a fixed set of parameters determined at driver design time, arbok is dynamically generated for the FPGA program itself each time a measurement is run. FPGA progam parameters such as wait times, voltages, and frequencies etc. are automatically exposed through the QCoDeS instrument, without the user needing to interact with or even see the underlying FPGA code.

- **Scalability:**
- **Modularity:**

 
## Installation 📲
[From pypi](https://pypi.org/project/arbok-driver/) install using pip in your environment:
```bash
pip install arbok-inspector
```
Even better if you are using uv, a uv.lock file is included!

## Tutorials 🎓

## Stripping jupyter notebooks 📒

We all love running measurements and analysis scripts from notebooks but keeping them up to date with version control can be a pain.
Differeing outputs, timestamps and massive binary data can make your diffs massive. We include git hooks that automatically clear the outputs of your notebook once you commit it. The **arbok_driver** is configured declaratively so dont worry you will reach the same state again once you re-run your notebook.

Install the git hook so that your notebooks are stripped before committing.
### To do this with Microsoft :
```
.\tools\git.hooks\setupMicrosoft.ps1
```
### To do this with Linux :
```
./tools/git.hooks/setupLinux.sh
```








