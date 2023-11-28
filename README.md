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

### Optional 1) Adding your environment to ipykernel

I recommend running measurements from jupyter lab, which is automatically
installed when executing 3). To pick the environment you just created within
the jupyter lab application, add it to the ipython kernel

```bash
python -m ipykernel install --name <your_env_name>
```
### Optional 2) Live plotting and data inspection with plottr
 Data inslection and live plotting can be done with the `plottr-inpectr` module. To launch it open a terminal and activate your conda environment...
 ```bash
conda activate <your-env-name>
```
... and launch plottr

```bash
plottr-inspectr --dbpath <path-to-your-database>
```
The data inspector is now running independently of all measurement while beiong connected to the selected database. Select auto-update intervals to have new measurements displayed in real time

### Optional 3) Launch jupyter-lab to run measurements

Jupyter notebooks are a very convenient way of cinducting measurements. Code cells can be run one after another data analysis can be done concurrently to measurements. Keeping measurements in notbooks also guaratees a clear separation between the underlying code base and the configuration files of devices and sequences.

Again activate your conda environment and launch `jupyterlab`

```bash
jupyter lab
```

## Todos:
- [ ] validators in custom parameter classes for times (4ns -> 1 qm-cycle)
- [ ] change the way to create sweeps!
    - [ ] sset list of dicts -> list entry per axis, dict entry per param
    - [ ] sweeps should be properties with setters for save measurement management
- [ ] TESTS!
    - [ ] issue: stubbing OPX/ errors raised by instrument
