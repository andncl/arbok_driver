# arbok-driver 🐍⚡️
[![Documentation Status](https://readthedocs.org/projects/arbok-driver/badge/?version=latest)](https://arbok-driver.readthedocs.io/en/latest/index.html)
[![PyPI](https://img.shields.io/pypi/v/arbok-driver.svg)](https://pypi.org/project/arbok-driver/)
[![License](https://img.shields.io/github/license/andncl/arbok_driver.svg)](LICENSE)
[![Coverage](https://codecov.io/gh/andncl/arbok_driver/graph/badge.svg)](https://codecov.io/gh/andncl/arbok_driver)
[![Python](https://img.shields.io/pypi/pyversions/arbok-driver.svg)](https://pypi.org/project/arbok-driver/)

A dynamically generated [QCoDeS](https://github.com/microsoft/Qcodes) instrument for your FPGA based measurements using the Quantum Machines [OPX+](https://www.quantum-machines.co/products/opx/)/[OPX1000](https://www.quantum-machines.co/products/opx1000/).

---

## Installation 📲
[From pypi](https://pypi.org/project/arbok-driver/) install using pip in your environment:
```bash
pip install arbok-inspector
```
Even better if you are using uv, a uv.lock file is included!

---

## Features 🛠️
- <u>**Abstraction:**</u> In contrast to traditional static QCoDeS instruments with a fixed set of parameters determined at driver design time, arbok is dynamically generated for the FPGA program itself each time a measurement is run. FPGA progam parameters such as wait times, voltages, and frequencies etc. are automatically exposed through the QCoDeS instrument, without the user needing to interact with or even see the underlying FPGA code.

- <u>**Modularity:**</u> Measurements are generated from logical blocks of instructions called `SubSequence` and `ReadSequence` whose order can be arranged freely. Those sequences can be nested arbitrarily deep to reach the desired complexity without repeating yourself (imagine a nested dict).
  
- <u>**Scalability:**</u> Arbok strictly separates the qualitative design of FPGA instructions in `SubSequence` and `ReadSequence` and their quantitative configuration (through python dicts), ensuring reproducibility. Sequences are written in a fully parameterized way, giving user access to every aspect of the measurement. This approach allows us to grow our quantum chips without re-writing any FPGA sequences by just scaling the configuration we are using, while still exposing every single sub-parameter of the device.

- <u>**Compatibility:**</u> At the end of the day, the arbok-driver is still a QCoDeS instrument, giving you all the features you know from running measurements on regular hardware. It slots right into your existing stack and allows you to sweep hardware parameters as well as FPGA instructions.

- <u>**Auto-tuning:**</u> All parameters can be defined as undetermined variables and updated by the user in real time without needing to re-compile the FPGA program for each set of parameters. This is particularly interesting for adaptive calibrations, machine learning or qubit benchmarking. 

- <u>**Asynchronicity:**</u> Support for asynchronously running sequences like qubit state heralding or live qubit feedback (e.g Larmor, Rabi)

---

## Tutorials 🎓

The tutorial series introduces the core concepts of the *arbok* framework, guiding you from running basic measurements to building modular, scalable, and automated experiments.

- [Tutorial 0: **Getting started**](docs/0_Measurement_example.ipynb)   
>Set up your environment, initialise your device, and run a first measurement using existing sequences.

- [Tutorial 1: **Parameterising sequences**](docs/1_parameterizing_sequences.ipynb)  
>Learn how FPGA program parameters (e.g. voltages, timings, frequencies) are exposed through the QCoDeS interface and how to configure them dynamically.

- [Tutorial 2: **Readout sequences**](docs/2_Readout_sequences.ipynb)  
>Understand how to use and compose `ReadSequence`s to extract measurement results in a structured and reusable way.

- [Tutorial 3: **Experiments**](docs/3_Experiments.ipynb)   
>Build higher-level experiment abstractions to repeatedly run and organise complex measurement routines.

- [Tutorial 4: **Tuning interface**](docs/4_Tuning_interface.ipynb)
>Implement automated tuning and calibration routines using the `GenericTuningInterface`, enabling adaptive and scalable workflows without recompilation of FPGA instructions

Together, these tutorials demonstrate how *arbok* enables:
- Modular composition of measurements from reusable building blocks  
- Full parameter control without modifying FPGA/qua code  
- Seamless scaling from small devices to larger quantum systems  
- Fast iteration through dynamic reloading with `Ekans`  

---

## Stripping jupyter notebooks 📒

We all love running measurements and analysis scripts from notebooks but keeping them up to date with version control can be a pain.
Differeing outputs, timestamps and massive binary data can make your diffs massive. We include git hooks that automatically clear the outputs of your notebook once you commit it. The **arbok_driver** is configured declaratively so dont worry you will reach the same state again once you re-run your notebook.

Install the git hook so that your notebooks are stripped before committing.
### Microsoft :
```
.\tools\git.hooks\setupMicrosoft.ps1
```
### Linux :
```
./tools/git.hooks/setupLinux.sh
```












