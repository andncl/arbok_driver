# arbok_driver
QCoDeS compatible driver for the OPX+ from Quantum Machines
Arbok is taylored for routines using the Quantum Machines OPX(+) quantum control hardware.

## Installation 
To install the arbok python module locally follow the steps below

### 1) Clone github repository
```bash
git clone https://github.com/andncl/arbok_driver.git
```

### 2) Prepare conda environment

```bash
conda create --name <your_env_name>
conda activate <your_env_name>
conda install pip
```

### 3) Go to repo folder and install local arbok module

```bash
pip install -e .
```
**Do not forget the dot after '-e' **. Arbok should now install 
all its requirements automatically. If you need additional
packages, install them in your new environment called <your_env_name>

### Optional) Adding your environment to ipykernel

I recommend running measurements from jupyter lab, which is automatically
installed when executing 3). To pick the environment you just created within
the jupyter lab application, add it to the ipython kernel

```bash
python -m ipykernel install --name <your_env_name>
```
