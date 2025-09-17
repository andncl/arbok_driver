# arbok_driver
QCoDeS compatible driver for the OPX+ from Quantum Machines
Arbok is taylored for routines using the Quantum Machines OPX(+) quantum control hardware.

## Installation
Installation via the [latest pip release](https://pypi.org/project/arbok-driver/) :

```bash
pip install arbok-driver
```
To install the arbok python package locally follow the steps below:

### 1) Clone github repository
```bash
git clone https://github.com/andncl/arbok_driver.git
```

### 2) Prepare conda environment
We create an empty conda environment to avoid interference with other python packages and to manage package dependencies for measurements. Remember to fix the python version as shown below when creating the environment, since some of the modules are not yet compatible with the latest 3.12.
```bash
conda create --name <your_env_name> python=3.12
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

### 4) Install git hooks
Install the git hook so that your notebooks are stripped before committing.
### To do this with Microsoft :
```
.\tools\git.hooks\setupMicrosoft.ps1
```
### To do this with Linux :
```
./tools/git.hooks/setupLinux.sh
```


### Optional 1) Adding your environment to ipykernel

I recommend running measurements from jupyter lab, which is automatically
installed when executing 3). To pick the environment you just created within
the jupyter lab application, add it to the ipython kernel.

```bash
python -m ipykernel install --user --name <your_env_name>
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

## Tutorial: Launch jupyter-lab to run measurements

Jupyter notebooks are a very convenient way of cinducting measurements. Code cells can be run one after another data analysis can be done concurrently to measurements. Keeping measurements in notbooks also guaratees a clear separation between the underlying code base and the configuration files of devices and sequences.

Again activate your conda environment and launch `jupyterlab`

For example to run the first tutorial:
```bash
jupyter lab docs/1_parameterizing_sequences.ipynb
```
## Re-launching an existing arbok session
If all running applications have been closed for example when the hosting PC is being restarted, a previously run arbok session can be easily restarted in a few steps.

### 1) Launching the jupyter notebook
Activate your conda install environment that you created initally. If you are unsure what the name of your environment is type `conda env list`. After that launch jupyter lab as shown below. To simplyfy navigation, launch jupyter in the directory where your notebooks are saved.
```bash
conda activate <your-env-name>
jupyter lab
```
### 2) Launching plottr-inspectr
Exactly as described above!




