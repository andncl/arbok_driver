# arbok-driver — LLM Guide

> **See also:** [llms-internals.md](llms-internals.md) for the architecture
> reference (class hierarchy, compilation pipeline, parameter resolution).
> Only consult that file when debugging or extending the core framework.

## What is this project?

arbok-driver is a **dynamically generated QCoDeS instrument** that compiles
Python-level measurement descriptions into [QUA](https://docs.quantum-machines.co/latest/)
programs for Quantum Machines OPX+/OPX1000 FPGAs. It is used to run spin-qubit
experiments on silicon quantum dot devices in a dilution refrigerator.

The user describes a measurement as a tree of `SubSequence` and `ReadSequence`
objects, configures them with Python dicts, and arbok-driver:

1. Registers every parameter as a QCoDeS parameter (sweepable, gettable)
2. Compiles the tree into a single QUA program
3. Manages execution, streaming, and data acquisition

---

## From zero to first measurement

```python
from arbok_driver import ArbokDriver, Device, Measurement
from arbok_driver.examples.configurations.hardware import opx1000_config
from arbok_driver.examples.configurations.sequence import (
    device_config, parity_init_conf, parity_read_conf
)
from arbok_driver.examples.sequences import Xstrict

# 1. Create device (hardware configs reflect the physical wiring)
device = Device(
    'my_device',
    opx_config=opx1000_config,
    divider_config={},
    master_config=device_config,
)

# 2. Create driver
driver = ArbokDriver('driver', device)

# 3. Define measurement structure as a dict
meas_dict = {
    'parity_init': {'config': parity_init_conf},
    'control': {
        'sub_sequences': {
            'x_gate': {
                'sequence': Xstrict,
                'kwargs': {'target_qubit': 'Q1', 'control_pulse': 'control_pi'},
            },
        },
    },
    'parity_read': {'config': parity_read_conf},
}

# 4. Build and compile
meas = Measurement(driver, 'my_meas')
meas.add_subsequences_from_dict(meas_dict)
program = meas.get_qua_program()           # compiles to QUA
print(meas.get_qua_program_as_str())       # inspect the compiled code

# 5. (On real hardware) set sweeps and run
# meas.set_sweeps({meas.parity_init.t_wait_at_t1: np.linspace(100, 1000, 50)})
# meas.compile_qua_and_run()
```

---

## Project structure

```
arbok_driver/
├── arbok_driver.py          # ArbokDriver — top-level QCoDeS Instrument
├── device.py                # Device — holds OPX config + master params
├── measurement.py           # Measurement — root of a sequence tree
├── sequence_base.py         # SequenceBase — shared tree/compilation logic
├── sub_sequence.py          # SubSequence — leaf node with QUA code
├── read_sequence.py         # ReadSequence — SubSequence with readouts
├── abstract_readout.py      # AbstractReadout — readout processing base
├── signal.py                # Signal — groups gettables per physical line
├── sweep.py                 # Sweep — QUA loop generation for sweeps
├── experiment.py            # Experiment — reusable measurement blueprint
├── parameter_class.py       # ParameterClass — frozen dataclass base
├── parameter_types.py       # Typed parameters: Time, Voltage, Amplitude, ...
├── parameters/              # SequenceParameter, GettableParameter, ...
├── arbok/                   # QUA helper functions (ramp, reset_sticky)
├── ekans.py                 # Ekans — hot-reload of running programs
├── generic_tuning_interface.py  # Real-time parameter streaming
└── examples/
    ├── sequences/           # SubSequence implementations
    ├── configurations/
    │   ├── hardware/        # OPX + divider configs (static, reflects physical wiring)
    │   └── sequence/        # Parameter dicts for sequences
    ├── readout_classes/     # AbstractReadout implementations
    └── experiments/         # Experiment blueprints
```

---

## Writing a new SubSequence

This is the most common task. A SubSequence has:

1. A **frozen dataclass** declaring required parameters
2. A **class** inheriting `SubSequence` with QUA lifecycle hooks

```python
from dataclasses import dataclass
from qm import qua
from arbok_driver import SubSequence, ParameterClass, arbok
from arbok_driver.parameter_types import Time, Voltage, ParameterMap, List

@dataclass(frozen=True)
class MySeqParameters(ParameterClass):
    gate_elements: List
    v_home: ParameterMap[str, Voltage]
    v_target: ParameterMap[str, Voltage]
    t_ramp: Time
    t_wait: Time

class MySeq(SubSequence):
    PARAMETER_CLASS = MySeqParameters
    arbok_params: MySeqParameters

    def __init__(self, parent, name, sequence_config, **kwargs):
        super().__init__(parent, name, sequence_config, **kwargs)
        self.elements = self.arbok_params.gate_elements.get()

    def qua_sequence(self):
        arbok.ramp(
            elements=self.elements,
            reference=self.arbok_params.v_home,
            target=self.arbok_params.v_target,
            duration=self.arbok_params.t_ramp,
            operation='unit_ramp',
        )
        qua.wait(self.arbok_params.t_wait.qua, *self.elements)
        arbok.reset_sticky_elements(self.elements)
```

### QUA lifecycle hooks (called in this order per iteration)

| Hook                  | Purpose                                      |
|-----------------------|----------------------------------------------|
| `qua_declare()`      | Declare QUA variables and streams            |
| `qua_before_sweep()` | Code before the sweep loop (once per resume) |
| `qua_before_sequence()` | Code before each iteration                |
| `qua_sequence()`     | Main QUA instructions                        |
| `qua_after_sequence()` | Code after each iteration (feedback, flags)|
| `qua_stream()`       | Stream processing (buffer/save definitions)  |

### Providing a config dict for the sequence

```python
from arbok_driver.parameter_types import Time, Voltage, List

my_seq_conf = {
    'sequence': MySeq,
    'parameters': {
        'gate_elements': {'type': List, 'value': ['P1', 'J1', 'P2']},
        't_ramp': {'type': Time, 'value': int(1e3/4)},
        't_wait': {'type': Time, 'value': int(500/4)},
        'v_home': {'type': Voltage, 'elements': {'P1': 0, 'J1': 0, 'P2': 0}},
        'v_target': {'type': Voltage, 'elements': {'P1': 0.05, 'J1': -0.02, 'P2': -0.05}},
    },
}
```

---

## Common gotchas

### Timing is in FPGA clock cycles, not nanoseconds

The `Time` parameter type stores values in **clock cycles** (1 cycle = 4 ns).
When you see `int(1e3/4)` in a config, that's 1000 ns = 250 cycles.
Always divide nanoseconds by 4 when writing time values.

### Config dicts must always have a `'parameters'` key

Even if there are no extra parameters, a config dict needs:
```python
{'sequence': MySeq, 'parameters': {}}
```
Omitting `'parameters'` raises a `KeyError`.

### `ParameterClass` fields must match available parameters

Every field in your frozen dataclass must be resolvable — either from the
sequence's own config, the `master_config` on the Device, or a parent sequence.
A mismatch raises `TypeError: ... missing required positional arguments`.

### `ParameterMap` values are resolved per-element

When you write `'v_home': {'type': Voltage, 'elements': {'P1': 0, 'J1': 0}}`,
this creates **one QCoDeS parameter per element** (e.g. `v_home_P1`,
`v_home_J1`). In the `ParameterClass` they are grouped as a
`ParameterMap[str, Voltage]` and accessed as a dict-like mapping.

### The `'sequence'` key points to a class, not an instance

Config dicts reference the SubSequence **class**:
```python
{'sequence': ParityInit, ...}   # correct — class reference
{'sequence': ParityInit(), ...} # WRONG — do not instantiate
```

### ReadSequence configs need `'signals'` and `'readout_groups'`

A ReadSequence config requires three top-level keys:
```python
{'sequence': MyRead, 'parameters': {...}, 'signals': ['sig1'], 'readout_groups': {...}}
```

### `check_step_requirements` goes in `kwargs`, not in the config

When composing via dict, step-requirement gating is a constructor kwarg:
```python
'spin_control': {
    'sub_sequences': {...},
    'kwargs': {'check_step_requirements': True},  # here, not inside config
}
```

### Variable paths for cross-sequence lookup

Sub-sequences often need to reference variables declared elsewhere in the
measurement tree — for feedback/heralding, but also for any inter-sequence
communication. The mechanism is `measurement.find_parameter_from_sub_sequence(path)`,
which walks a **dot-separated attribute path** starting from the Measurement:

```python
'parity_read.p1p2.state__p1p2.qua_result_var'
#  ^sub-sequence  ^signal  ^gettable        ^attribute on the gettable
```

This resolves to the QUA variable holding the thresholded state. The path
follows Python attribute access — each segment is an `getattr` call on the
previous result. Common patterns:

| What you want | Path |
|---|---|
| A gettable's QUA variable | `'read_seq.signal.gettable_name.qua_result_var'` |
| A parameter's QUA variable | `'sub_seq.param_name.qua_var'` |
| A callable (returns a value) | `'sub_seq.some_method'` (if callable, it's called) |

This is used by heralded init (`feedback_result`), but the same mechanism
works whenever one sub-sequence needs runtime access to a variable owned by
another sub-sequence in the same measurement tree.

### `opx1000_config` and `divider_config` reflect physical wiring

These hardware configurations describe the physical connections between the
OPX instrument and the dilution fridge (element-to-port mapping, mixer
calibrations, pulse definitions, etc.). They depend on the specific hardware
setup and should not change dynamically at runtime. Treat them as static once
the device is connected — modifications are only appropriate when the physical
wiring or instrument configuration changes.

### `sub_sequences` dict entries must not also have `'sequence'` or `'config'`

A dict entry with `'sub_sequences'` creates a container node. It cannot
simultaneously specify a `'sequence'` or `'config'` — that's a `KeyError`.

---

## Testing conventions

Tests live in `tests/` and use `pytest`. The shared fixtures in
`tests/conftest.py` provide:

- `dummy_device` — a Device with the example OPX config + device_config
- `arbok_driver` — an ArbokDriver wrapping dummy_device
- `mock_measurement` — a fresh Measurement (auto-cleaned after each test)

New example sequences should have a corresponding test in `tests/examples/`
that:
1. Builds the measurement from a dict
2. Asserts the hierarchy structure (sub_sequences count, parameter values)
3. Compiles to QUA (`get_qua_program_as_str(recompile=True)`)
4. Asserts key structures exist in the compiled output

---

## What NOT to do

- **Do not dynamically modify hardware configs** (`opx1000_config`, `divider_config`) — they reflect physical wiring
- **Do not instantiate SubSequence classes directly** in measurement dicts — pass the class reference
- **Do not call `qua.*` functions outside** of `qua_*` lifecycle hooks — they are only valid inside a `qua.program()` context
- **Do not create new files in `arbok_driver/` core** without understanding the compilation pipeline (see [llms-internals.md](llms-internals.md))
- **Do not use `time.sleep`** or blocking calls inside QUA sequences — everything runs on the FPGA
