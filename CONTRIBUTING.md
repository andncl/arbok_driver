# Project Guide — arbok-driver

A comprehensive guide to the **arbok-driver** codebase for new developers and AI agents.

---

## What is arbok-driver?

A dynamically generated [QCoDeS](https://github.com/microsoft/Qcodes) instrument driver for FPGA-based quantum measurements. Originally built for Quantum Machines [OPX+](https://www.quantum-machines.co/products/opx/) / [OPX1000](https://www.quantum-machines.co/products/opx1000/), it now supports **swappable hardware backends** (QUA, simulation, and future: QBLOX, Keysight).

It abstracts FPGA programs into modular, composable building blocks whose parameters are automatically exposed through the QCoDeS instrument interface. A hardware-agnostic `arbok.*` API layer lets you write sequences once and run them on any supported backend. This enables scalable quantum dot experiments without touching vendor-specific FPGA code.

**Author:** Andreas Nickl  
**Python:** 3.12, 3.13  
**Package:** [PyPI](https://pypi.org/project/arbok-driver/) · [Docs](https://arbok-driver.readthedocs.io/en/latest/)  
**Repository:** https://github.com/andncl/arbok_driver

---

## Quick Start

```bash
# Install from PyPI
pip install arbok-driver

# Or for development (using uv)
uv sync --all-extras
```

Run tests:
```bash
pytest --cov=arbok_driver
```

---

## Directory Structure

```
arbok_driver/                         # Root of the repository
├── arbok_driver/                     # Source package
│   ├── __init__.py                   # Public API exports
│   ├── arbok_driver.py               # ArbokDriver (top-level QCoDeS Instrument)
│   ├── measurement.py                # Measurement (orchestrates sweeps + acquisition)
│   ├── sequence_base.py              # SequenceBase (base class for all sequences)
│   ├── sub_sequence.py               # SubSequence (logical block of QUA instructions)
│   ├── read_sequence.py              # ReadSequence (sequence with readout operations)
│   ├── experiment.py                 # Experiment (abstract experiment workflow)
│   ├── device.py                     # Device (physical device representation)
│   ├── ekans.py                      # Ekans (dynamic module hot-reloading)
│   ├── generic_tuning_interface.py   # GenericTuningInterface (ML-based tuning)
│   ├── abstract_readout.py           # AbstractReadout (base for readout logic)
│   ├── signal.py                     # Signal (voltage signal from OPX element)
│   ├── sweep.py                      # Sweep (parameter sweep + waveform caching)
│   ├── parameter_class.py            # ParameterClass (frozen dataclass base)
│   ├── parameter_types.py            # Typed parameters: Voltage, Time, Amplitude, etc.
│   ├── path_finders.py               # Helpers to locate gettables/signals in the tree
│   ├── sqlalchemy_classes.py         # ORM models (SqlRun, SqlExperiment, SqlDevice)
│   ├── utils.py                      # Plotting utilities (matplotlib + plotly)
│   │
│   ├── backend.py                    # Backend ABC (hardware abstraction interface)
│   │
│   ├── backends/                     # Concrete backend implementations
│   │   ├── qua_backend.py            # QuaBackend (Quantum Machines OPX)
│   │   └── sim_backend.py            # SimBackend (waveform simulation at 1 GS/s)
│   │
│   ├── arbok/                        # Hardware-agnostic operation API
│   │   ├── __init__.py               # Public exports for `arbok.*` operations
│   │   ├── play.py                   # play(), ramp() (deprecated), PulseGenerator
│   │   ├── reset_sticky_elements.py  # reset_sticky_elements()
│   │   ├── context.py                # Thread-local active backend management
│   │   └── operations.py             # play_pulse, wait, align, measure, assign, control flow
│   │
│   ├── parameters/                   # Parameter classes
│   │   ├── sequence_parameter.py     # SequenceParameter (QCoDeS + hw_var/qua variable)
│   │   ├── gettable_parameter.py     # GettableParameter (scalar measurement result)
│   │   ├── gettable_parameter_base.py# GettableParameterBase (base with setpoints)
│   │   └── gettable_parameter_multi.py# GettableParameterMulti (array results)
│   │
│   ├── measurement_runners/          # Measurement execution strategies
│   │   ├── measurement_runner_base.py# MeasurementRunnerBase (ABC with progress)
│   │   ├── native_measurement_runner.py  # Streams to xarray/zarr/PostgreSQL
│   │   └── qcodes_measurement_runner.py  # Uses QCoDeS native dataset
│   │
│   └── examples/                     # Bundled reference implementations
│       ├── sequences/                # 14 SubSequence examples
│       ├── readout_classes/          # 4 AbstractReadout examples
│       ├── experiments/              # 2 Experiment examples
│       └── configurations/           # Hardware + sequence configs
│           ├── hardware/             # OPX1000 and divider configs
│           └── sequence/             # Parameter configs for sequences
│
├── tests/                            # Test suite (pytest)
│   ├── conftest.py                   # Shared fixtures
│   ├── helpers.py                    # Test utilities
│   ├── test_*.py                     # Unit tests per module
│   ├── arbok/                        # Tests for arbok/ subpackage
│   └── examples/                     # Integration tests for examples
│
├── docs/                             # Sphinx documentation + Jupyter tutorials
│   ├── conf.py                       # Sphinx config
│   ├── *.ipynb                       # Tutorials 0-6 + Developer Guides
│   ├── configurations/               # Tutorial-specific configs
│   ├── qua_programs/                 # Standalone QUA programs (for reference)
│   └── figures/                      # Diagrams and icons
│
├── tools/                            # Git hooks for notebook stripping
├── .github/workflows/                # CI/CD (tests + PyPI release)
├── pyproject.toml                    # Build config (setuptools + setuptools-scm)
├── uv.lock                           # Dependency lockfile
└── .readthedocs.yaml                 # ReadTheDocs build config
```

---

## Architecture Overview

### Core Concept: The Sequence Tree

The central abstraction is a **tree of sequences** that composes a QUA program:

```
ArbokDriver (QCoDeS Instrument)
└── Measurement (top-level sequence container)
    ├── SubSequence "init" (e.g. state initialization)
    │   └── SubSequence "ramp_to_point" (nested)
    ├── SubSequence "control" (e.g. gate pulse)
    └── ReadSequence "read" (readout + data extraction)
        ├── Signal "sensor_1"
        │   └── AbstractReadout "dc_average" → GettableParameter
        └── Signal "sensor_2"
            └── AbstractReadout "threshold" → GettableParameter
```

Each node in this tree contributes QUA code through lifecycle hooks. The program is assembled by recursively calling these hooks from root to leaves.

### Class Hierarchy

```
QCoDeS Instrument
└── ArbokDriver                     # Manages backend + OPX connection, holds Device
    ├── Backend (ABC)               # Hardware abstraction interface
    │   ├── QuaBackend              # Quantum Machines OPX (default)
    │   └── SimBackend              # Waveform simulation
    └── Measurement (SequenceBase)  # Orchestrates sweeps, compiles QUA program
        └── SubSequence (SequenceBase)  # Logical block of FPGA instructions
            └── ReadSequence (SubSequence)  # Extends with signals + readouts

SequenceBase (InstrumentModule, ABC)  # Base: parameter management, code composition
```

### Data Flow

```
1. User defines Device (hardware config) + Experiment (sequence ordering)
2. ArbokDriver.create_measurement_from_experiment() builds the sequence tree
3. User sets sweeps via measurement.set_sweeps({param: array, ...})
4. User registers gettables via measurement.register_gettables()
5. measurement.run_measurement() → compiles QUA → executes on OPX → streams results
6. Results returned as xarray.Dataset
```

---

## Key Classes in Detail

### `Device` (`device.py`)

Represents the physical quantum device. Holds three configuration dicts:

| Config | Purpose |
|--------|---------|
| `opx_config` | Quantum Machines hardware configuration (elements, pulses, waveforms) |
| `divider_config` | Voltage divider ratios per element (scales parameter values) |
| `master_config` | Universal parameters and default sequence configs for the device |

The `elements` list (gate names like `P1`, `J1`, etc.) is extracted from the OPX config.

### `ArbokDriver` (`arbok_driver.py`)

Top-level QCoDeS `Instrument`. Responsibilities:
- Manages the OPX connection (`connect_opx`, `reconnect_opx`, `run`)
- Holds the active **Backend** instance (defaults to `QuaBackend`)
- Holds measurements and device reference
- Provides database/MinIO connectivity for the native runner
- Creates measurements from experiments

Accepts an optional `backend` parameter to swap hardware implementations:
```python
driver = ArbokDriver("sim", backend=SimBackend())
```

### `Measurement` (`measurement.py`)

The root of a sequence tree. Inherits `SequenceBase` but is NOT a `SubSequence` — it's the container. Responsibilities:
- Holds sweeps (`set_sweeps`), gettables (`register_gettables`)
- Compiles and runs the QUA program (`compile_qua_and_run`, `run_measurement`)
- Manages input streams for real-time parameter updates
- Fetches results from the OPX
- Provides `MeasurementRunner` instances (QCoDeS or native backend)

### `SequenceBase` (`sequence_base.py`)

Abstract base extending QCoDeS `InstrumentModule`. Every sequence node inherits this. Provides:
- **Parameter management:** `add_qc_params_from_config()` creates `SequenceParameter` instances from config dicts
- **FPGA lifecycle hooks:** `fpga_declare()`, `fpga_before_sequence()`, `fpga_sequence()`, `fpga_after_sequence()`, `fpga_stream()` (with `qua_*` legacy aliases)
- **Backend context:** `get_qua_program()` sets the active backend before compilation
- **Recursive composition:** Automatically calls child hooks in order
- **Sweep generation:** `recursive_sweep_generation()` creates nested QUA loops
- **Simulation:** `simulate()`, `get_qua_program()`

### `SubSequence` (`sub_sequence.py`)

Concrete sequence node. Key additions over SequenceBase:
- **`PARAMETER_CLASS`:** Every SubSequence must declare a frozen dataclass specifying which parameters it needs (enforced by `__init_subclass__`)
- **`arbok_params`:** Instance of PARAMETER_CLASS populated with actual SequenceParameter references at construction time
- **`fpga_sequence()`:** Override this to write hardware-agnostic code using `arbok.*` operations and `self.arbok_params`
- **`qua_sequence()`:** Legacy hook for QUA-specific code (still supported, falls back when no `fpga_*` override exists)
- **Dual dispatch:** `_dispatch_fpga_sequence()` checks if `fpga_sequence()` is overridden first; if not, falls back to `qua_sequence()` (QuaBackend only)

### `ReadSequence` (`read_sequence.py`)

A SubSequence that also declares **Signals** and **Readout Groups**:
- **Signals:** Named voltage channels being measured (e.g. `sensor_1`)
- **Readout groups:** Collections of `AbstractReadout` instances that process signals
- Produces `GettableParameter` instances registered on the parent `Measurement`

### `AbstractReadout` (`abstract_readout.py`)

Base class for readout logic. Subclasses implement `qua_measure()` which contains the QUA instructions to acquire data. The base class handles:
- QUA variable/stream declaration
- Saving measured values to streams
- Creating `GettableParameter` or `GettableParameterMulti` instances

Example implementations: `DcAverage`, `DcChoppedReadout`, `Difference`, `Threshold`

### `Experiment` (`experiment.py`)

Abstract class that defines experiment workflows — the order of sequences and their configurations. Implement the `sequences_config` property to return a dict describing which SubSequences to use and in what order.

### `Sweep` (`sweep.py`)

Manages one axis of a parameter sweep. Handles:
- QUA loop generation (for-each over setpoints)
- Snake scan support (alternating sweep direction)
- Waveform caching (pre-compiling discrete waveforms for faster execution)

### `Ekans` (`ekans.py`)

Dynamic reloadable package view. Enables hot-reloading of Python modules during development — change a sequence class on disk, call `ekans.reload_modules()`, and the new code is available without restarting the kernel.

### `GenericTuningInterface` (`generic_tuning_interface.py`)

ML-based parameter optimization interface. Uses:
- Latin hypercube sampling for initial parameter space exploration
- Pluggable `CostFunction` protocol for evaluating measurement results
- Real-time parameter updates via input streams (no recompilation)

---

## Parameter System

### Configuration Format

Parameters are defined in config dicts passed to sequences:

```python
config = {
    "parameters": {
        "amplitude": {"type": Amplitude, "value": 1.5},
        "t_wait": {"type": Time, "value": 100},           # in FPGA cycles (×4ns)
        "v_target": {
            "type": Voltage,
            "elements": {"P1": 0.1, "P2": -0.2}           # per-element definition
        },
    }
}
```

### Parameter Types (`parameter_types.py`)

| Type | QUA var type | Unit | Purpose |
|------|-------------|------|---------|
| `Voltage` | `qua.fixed` | V | Gate voltages |
| `Time` | `int` | s (input in cycles) | Wait times, pulse durations |
| `Amplitude` | `qua.fixed` | — | Pulse amplitude scaling |
| `Int` | `int` | # | Counters, indices |
| `Frequency` | `int` | Hz | RF/IF frequencies |
| `Boolean` | `bool` | — | Flags |
| `Radian` / `Pi` | `qua.fixed` | pi | Phase angles |
| `String` | `str` | — | Element names, labels |
| `List` | — | — | Lists of values |

### ParameterMap

When a parameter is defined with `"elements": {...}`, a `ParameterMap` is created — a frozen mapping from element names to individual `SequenceParameter` instances. This enables per-gate voltage control while sweeping them together.

### ParameterClass

Every `SubSequence` declares a `PARAMETER_CLASS` — a frozen `@dataclass` listing the parameters it needs:

```python
@dataclass(frozen=True)
class MySequenceParams(ParameterClass):
    v_target: ParameterMap[str, Voltage]  # per-element voltages
    t_wait: Time                          # a single time parameter
    amplitude: Amplitude
```

At construction, `map_arbok_params()` resolves field names to actual `SequenceParameter` instances from the config and stores them in `self.arbok_params`.

---

## Writing a SubSequence

Minimal example using the hardware-agnostic API:

```python
from dataclasses import dataclass
from arbok_driver import arbok, ParameterClass, SubSequence
from arbok_driver.parameter_types import Amplitude, Time, String

@dataclass(frozen=True)
class SquarePulseParameters(ParameterClass):
    amplitude: Amplitude
    element: String
    t_ramp: Time
    t_square_pulse: Time

class SquarePulse(SubSequence):
    PARAMETER_CLASS = SquarePulseParameters
    arbok_params: SquarePulseParameters

    def fpga_sequence(self):
        """Hardware-agnostic code executed in the inner measurement loop."""
        arbok.align()
        arbok.play_pulse(
            'ramp',
            self.arbok_params.element.hw_var,
            amplitude=self.arbok_params.amplitude.hw_var,
            duration=self.arbok_params.t_ramp.hw_var,
        )
        arbok.wait(
            self.arbok_params.t_square_pulse.hw_var,
            self.arbok_params.element.hw_var
        )
```

The `.hw_var` property on each parameter returns its hardware variable (QUA variable when using QuaBackend, Python value when using SimBackend). The legacy `.qua` accessor is still available as an alias.

### Legacy QUA-specific pattern (still supported)

```python
from qm import qua

class SquarePulse(SubSequence):
    def qua_sequence(self):
        """QUA-specific code — only works with QuaBackend."""
        qua.align()
        qua.play(
            pulse='ramp' * qua.amp(self.arbok_params.amplitude.qua),
            element=self.arbok_params.element.qua,
            duration=self.arbok_params.t_ramp.qua
        )
```

If both `fpga_sequence()` and `qua_sequence()` are defined, `fpga_sequence()` takes priority.

---

## Writing a ReadSequence Config

```python
from arbok_driver.examples.readout_classes import DcAverage

read_config = {
    "sequence": MyReadSequence,
    "signals": ["sensor_1", "sensor_2"],
    "readout_groups": {
        "dc": {
            "avg_s1": {
                "readout_class": DcAverage,
                "signal": "sensor_1",
                "kwargs": {"qua_element": "readout_element_1"},
                "parameters": {}
            }
        }
    }
}
```

---

## Writing an Experiment

```python
from arbok_driver import Experiment

class RabiExperiment(Experiment):
    _name = "rabi"

    def __init__(self, rabi_config=None):
        super().__init__(
            init="default_init",      # use device default
            control=rabi_config,       # custom config dict
            read="default_read",       # use device default
        )

    @property
    def sequences_config(self) -> dict:
        return {
            "init": self.configs.get("init", {}),
            "control": self.configs.get("control", {}),
            "read": self.configs.get("read", {}),
        }
```

---

## Running a Measurement (Typical Workflow)

```python
import numpy as np
from arbok_driver import ArbokDriver, Device, Measurement

# 1. Create device from configs
device = Device("my_device", opx_config, divider_config, master_config)

# 2. Create driver
driver = ArbokDriver("opx_driver", device)
driver.connect_opx("192.168.1.100")

# 3. Create measurement from experiment
measurement = driver.create_measurement_from_experiment(my_experiment)

# 4. Set sweeps
measurement.set_sweeps(
    {measurement.init.v_target_P1: np.linspace(-0.5, 0.5, 100)},   # outer
    {measurement.init.v_target_P2: np.linspace(-0.3, 0.3, 50)},    # inner
)

# 5. Register what to measure
measurement.register_gettables(keywords=["sensor"])

# 6. Run
dataset = measurement.run_measurement()
```

---

## Hardware-Agnostic Operations (`arbok_driver.arbok`)

The `arbok` subpackage provides the **hardware-agnostic API** for writing sequences. All operations dispatch to whichever backend is currently active (set automatically during program compilation).

### High-Level Operations (ParameterMap-based)

| Function | Purpose |
|----------|---------|
| `play(elements, target, operation, ...)` | Play a pulse on elements with waveform caching support |
| `ramp(...)` | **Deprecated** alias for `play()` |
| `reset_sticky_elements(elements)` | Ramp sticky elements back to zero |

### Low-Level Operations (dispatched to backend)

| Function | Purpose |
|----------|---------|
| `play_pulse(operation, element, amplitude, duration)` | Play a single pulse on one element |
| `wait(duration, *elements)` | Wait clock cycles on elements |
| `align(*elements)` | Synchronize elements |
| `measure(operation, element, *outputs)` | Perform a measurement |
| `integration_full(weights, output_var)` | Create integration output spec |
| `frame_rotation(angle, element)` | Rotate element frame (fraction of 2pi) |
| `ramp_to_zero(element)` | Ramp sticky element to zero |
| `declare(type, value, size)` | Declare a hardware variable |
| `declare_stream()` | Declare a data stream |
| `assign(variable, value)` | Assign to a hardware variable |
| `save(variable, stream)` | Save variable to stream |
| `amp(value)` | Create amplitude modifier |

### Control Flow (context managers)

| Function | Purpose |
|----------|---------|
| `for_loop(variable, init, condition, update)` | Hardware for-loop |
| `while_loop(condition)` | Hardware while-loop |
| `if_block(condition)` | Hardware if-branch |
| `else_block()` | Hardware else-branch |
| `switch_block(variable, unsafe)` | Hardware switch statement |
| `case_block(value)` | Case within a switch |

### Arithmetic / Type Helpers

| Function | Purpose |
|----------|---------|
| `cast_mul_int_by_fixed(int_val, fixed_val)` | Multiply int by fixed-point |
| `cast_mul_fixed_by_int(fixed_val, int_val)` | Multiply fixed-point by int |
| `get_fixed_type()` | Get the backend's fixed-point type |

**Waveform caching:** When `operation` is a callable `PulseGenerator`, discrete waveforms are pre-computed and baked into the OPX config at compile time. During sweeps, the OPX switches between pre-computed waveforms instead of computing amplitudes at runtime — dramatically faster for large sweeps.

---

## Backend System

### Architecture

```
arbok_driver.backend.Backend (ABC)
├── arbok_driver.backends.QuaBackend    # Quantum Machines OPX (default)
└── arbok_driver.backends.SimBackend    # Waveform simulation
```

The active backend is set as a thread-local context during QUA program compilation. All `arbok.*` operations dispatch to the active backend.

### QuaBackend (default)

Wraps all `qm.qua.*` calls. This is the default backend — existing code works unchanged.

### SimBackend

Interprets operations directly in Python and accumulates waveform samples at 1 GS/s per element. Useful for verifying pulse shapes without hardware.

```python
from arbok_driver import ArbokDriver, SimBackend

driver = ArbokDriver("sim", backend=SimBackend())
# ... build measurement ...
waveforms = driver.backend.get_waveforms()  # dict[str, NDArray]
```

### Adding a New Backend

Subclass `Backend` and implement all abstract methods. See `qua_backend.py` for reference.

---

## Measurement Runners

Two backends for data acquisition:

| Runner | Storage | Use Case |
|--------|---------|----------|
| `QCodesMeasurementRunner` | QCoDeS SQLite database | Standard lab use, QCoDeS ecosystem |
| `NativeMeasurementRunner` | PostgreSQL + MinIO (zarr) | High-throughput, remote storage, large datasets |

Both handle the outer sweep loop (hardware parameters), progress tracking, and data reshaping.

---

## Test Infrastructure

- **Framework:** pytest with coverage (`pytest-cov`)
- **Fixtures:** `tests/conftest.py` provides `dummy_device`, `arbok_driver`, `mock_measurement`, and example subsequences
- **Mock mode:** Set `driver.is_mock = True` to run without hardware (simulates data acquisition)
- **CI:** GitHub Actions runs on every push/PR, uploads coverage to Codecov

Running tests:
```bash
pytest                         # all tests
pytest tests/test_sweep.py     # single file
pytest --cov=arbok_driver      # with coverage
```

---

## CI/CD

| Workflow | Trigger | Action |
|----------|---------|--------|
| `tests.yml` | push, PR | Run pytest + upload coverage to Codecov |
| `pypi_release_auto_and_manual.yml` | GitHub release / manual | Build + publish to PyPI |

Versioning uses `setuptools-scm` (post-release scheme from git tags).

---

## Documentation

Built with Sphinx + `myst-nb` (renders Jupyter notebooks as documentation pages).

**Tutorials (progressive learning path):**

| # | Topic | Key Concepts |
|---|-------|--------------|
| 0 | Getting Started | Environment, Device, first measurement |
| 1 | Parameterizing Sequences | Config dicts, SequenceParameter, parameter types |
| 2 | Readout Sequences | Signals, AbstractReadout, GettableParameter |
| 3 | Experiments | Experiment class, sequence ordering, device defaults |
| 4 | Tuning Interface | GenericTuningInterface, cost functions, input streams |
| 5 | Ekans | Hot-reloading modules, dynamic iteration |
| 6 | Asynchronous Control | Heralded init, step requirements, repeat-until-success |

**Developer Guides:**

| # | Topic |
|---|-------|
| DG1 | Writing SubSequences from scratch |
| DG2 | Writing readout classes and ReadSequences |

Build docs locally:
```bash
cd docs
sphinx-build -b html . _build/html
```

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `qcodes` | Instrument framework (Parameter, InstrumentModule, datasets) |
| `qm-qua` | Quantum Machines QUA language SDK |
| `qualang_tools` | QM utility library |
| `anytree` | Tree structures (sequence nesting visualization) |
| `numpy` | Numeric arrays and sweeps |
| `xarray` / `zarr` | Multi-dimensional labeled data / chunked storage |
| `SQLAlchemy` / `psycopg2` | ORM + PostgreSQL for run metadata |
| `minio` / `s3fs` | S3-compatible object storage for measurement data |
| `rich` | Progress bars and terminal formatting |
| `scipy` | Scientific computing (tuning interface sampling) |

---

## Conventions and Patterns

### Naming
- **Elements:** Physical gate names from OPX config (e.g. `P1`, `J1`, `B1`)
- **Parameters with elements:** Named `{param_name}_{element}` (e.g. `v_target_P1`)
- **Nested paths:** Double-underscore separated (e.g. `measurement__init__v_target_P1`)

### FPGA Lifecycle Hooks (execution order)

The primary hooks use the `fpga_` prefix. The `qua_` prefix variants are deprecated aliases
that still work with QuaBackend.

| # | fpga_* (preferred) | qua_* (legacy) | Purpose |
|---|-------------------|----------------|---------|
| 1 | `fpga_declare()` | `qua_declare()` | Declare hardware variables |
| 2 | — | `qua_before_sweep()` | Before sweep loops (input stream handling) |
| 3 | *Sweep loops begin (recursive)* | | |
| 4 | `fpga_before_sequence()` | `qua_before_sequence()` | Before each inner iteration |
| 5 | `fpga_sequence()` | `qua_sequence()` | The actual pulse sequence |
| 6 | `fpga_after_sequence()` | `qua_after_sequence()` | After each inner iteration |
| 7 | *Sweep loops end* | | |
| 8 | `fpga_stream()` | `qua_stream()` | Stream processing definitions |

The dispatch system checks: if `fpga_*` is overridden, use it. Otherwise fall back to `qua_*`
(QuaBackend only — other backends raise `NotImplementedError` if only `qua_*` is defined).

### Config Dict Shape (for subsequences)
```python
{
    "sequence": SquarePulse,             # SubSequence class to instantiate
    "parameters": {                       # Parameters to create on the instance
        "param_name": {
            "type": Voltage,              # Parameter type class
            "value": 0.1,                 # Initial value (or "elements" for per-gate)
        }
    },
    "kwargs": {}                          # Extra kwargs passed to constructor
}
```

### Adding Nested Subsequences
```python
{
    "outer_name": {
        "sub_sequences": {
            "inner_1": {"sequence": SeqA, "config": config_a},
            "inner_2": {"sequence": SeqB, "config": config_b},
        }
    }
}
```

---

## Git Hooks

The project includes git hooks that strip Jupyter notebook outputs before commit (prevents large binary diffs):

```bash
# Linux
./tools/git.hooks/setupLinux.sh

# Windows
.\tools\git.hooks\setupMicrosoft.ps1
```

---

## Common Tasks

| Task | How |
|------|-----|
| Add a new SubSequence | Create class with `PARAMETER_CLASS`, implement `fpga_sequence()` using `arbok.*` |
| Add a new readout | Subclass `AbstractReadout`, implement `qua_measure()` using `arbok.*`, create gettables |
| Add a new experiment | Subclass `Experiment`, implement `sequences_config` property |
| Add a new backend | Subclass `Backend`, implement all abstract methods |
| Scale to more qubits | Add elements to OPX config, use `"elements": {...}` in parameter configs |
| Sweep a parameter | `measurement.set_sweeps({param: np.array})` |
| Update params without recompile | Use `input_stream_parameters` + `insert_single_value_input_streams()` |
| Hot-reload code | `ekans = Ekans(my_module); ekans.reload_modules()` |
| Simulate waveforms | `ArbokDriver("sim", backend=SimBackend())` then `.backend.get_waveforms()` |
| Simulate QUA program | `measurement.simulate(duration_ns=10000)` or `driver.is_mock = True` |
| Migrate to agnostic API | See `MIGRATION.md` for step-by-step guide |
