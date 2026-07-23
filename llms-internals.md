# arbok-driver — Internals Reference

> **This file is for debugging and extending the core framework only.**
> For writing sequences, configs, and tests, see [llms.md](llms.md).

---

## Class hierarchy

```
QCoDeS Instrument
└── ArbokDriver                    # Top-level driver, manages QM connection
    └── Measurement(SequenceBase)  # Root of a sequence tree
        ├── SubSequence(SequenceBase, ABC)   # Leaf nodes with QUA code
        │   └── ReadSequence(SubSequence)    # SubSequence with readout groups
        └── SubSequence ...                  # (can nest arbitrarily)

Supporting classes:
  Device            — Holds OPX config, divider config, master_config (shared params)
  Experiment(ABC)   — Blueprint encoding invariant measurement structure
  Sweep             — Generates QUA for_/while_ loops for parameter sweeps
  SequenceParameter — QCoDeS Parameter with QUA variable binding
  GettableParameter — Result variable (declared, measured, streamed)
  AbstractReadout   — Processing step producing GettableParameters
  Signal            — Groups gettables by physical readout line
  ParameterClass    — Frozen dataclass declaring required params for a SubSequence
  GenericTuningInterface — Real-time parameter updates via input streams
  Ekans             — Hot-reload: swap sub-sequences without full recompilation
```

### Inheritance chain for sequences

```
InstrumentModule (QCoDeS)
└── SequenceBase(InstrumentModule, ABC)
    ├── Measurement             # NOT a SubSequence — it's the root
    └── SubSequence(ABC)        # Must have a parent (Measurement or SubSequence)
        └── ReadSequence        # Adds signals, readout_groups, abstract_readouts
```

---

## Compilation pipeline

`Measurement.get_qua_program()` orchestrates everything:

```
get_qua_program()
│
├── qua.program() context manager opened
│   └── get_qua_code(simulate=False)
│       ├── qua_declare_sweep_vars()     # declare loop counter vars for sweeps
│       ├── qua_declare()                # recursive: each SubSequence declares vars
│       │
│       ├── infinite_loop_()             # QUA infinite loop
│       │   ├── pause()                  # wait for host resume
│       │   ├── qua_before_sweep()       # one-time setup per resume
│       │   │
│       │   └── recursive_sweep_generation(sweeps)
│       │       ├── (outer sweep) for_ loop
│       │       │   ├── (inner sweep) for_ loop
│       │       │   │   ├── qua_before_sequence()   # per-iteration setup
│       │       │   │   ├── qua_sequence()          # MAIN: calls each SubSequence
│       │       │   │   └── qua_after_sequence()    # per-iteration cleanup
│       │       │   │       └── qua_check_step_requirements(save/increment)
│       │       │   └── ...
│       │       └── ...
│       │
│       └── stream_processing()
│           └── qua_stream()             # recursive: define buffers/saves
│
└── generate_qua_script(prog, config)    # serialize to string (for inspection)
```

### Key detail: recursive dispatch

`SequenceBase.qua_sequence()` (line ~111 in `sequence_base.py`) iterates over
`self.sub_sequences` and calls each child's `qua_sequence()`. Leaf nodes
override this to emit actual QUA instructions. Container nodes (created by
`'sub_sequences'` in the dict) just recurse.

`SubSequence.qua_sequence()` (in `sub_sequence.py`) wraps the parent's version:
if `check_step_requirements=True`, the entire recursive call is gated behind
`measurement.qua_check_step_requirements(...)`.

---

## Step requirement mechanism

A **step requirement** is a `qua.declare(bool)` variable registered on the
`Measurement` via `add_step_requirement(var)`.

### How it gates execution

`qua_check_step_requirements(action, requirements_list)` is a recursive
function that nests `qua.if_(req)` blocks — one per registered requirement.
Only when ALL requirements are True does `action()` execute.

### What is gated

1. **SubSequences** with `check_step_requirements=True` — their `qua_sequence`
2. **Data saving** — `ReadSequence.qua_after_sequence()` wraps `save_variables`
   in `qua_check_step_requirements`
3. **Shot counter** — `Measurement.qua_after_sequence()` wraps the increment

### Who sets the requirement

Typically a heralded init sub-sequence (e.g. `ParityInitHeralded`):
- Declares a bool and registers it: `measurement.add_step_requirement(self.step_requirement)`
- Sets it `True` when initialization succeeded, `False` otherwise
- Reads a feedback variable resolved from a gettable on a ReadSequence

---

## Parameter resolution

### How `ParameterClass` fields get populated

`SubSequence.map_arbok_params()` collects parameters from:
1. The **Measurement** (via `measurement.get_parameters_and_maps(arg_names)`)
2. The **SubSequence itself** (via `self.get_parameters_and_maps(arg_names)`)

The SubSequence's own params take precedence over the Measurement's.

### Where parameters come from

- **Device `master_config`** → registered on the Measurement at construction
  (e.g. `gate_elements`, `qubit_elements`, `v_home`, `v_control`)
- **Sequence config dict `'parameters'`** → registered on the SubSequence
- **Element-wise params** (`'elements'` key) → expanded to one
  `SequenceParameter` per element: `v_home_P1`, `v_home_J1`, etc.
  Grouped in a `ParameterMap` when accessed through `arbok_params`.

### `find_parameter_from_sub_sequence(path)` — cross-sequence variable lookup

Resolves a **dot-separated attribute path** starting from the Measurement.
This is the general mechanism for one sub-sequence to reference a variable
owned by another sub-sequence in the same measurement tree — used for
feedback/heralding, but also for any inter-sequence communication.

```python
'parity_read.p1p2.state__p1p2.qua_result_var'
```
Walks: `measurement.parity_read` → `.p1p2` (Signal) → `.state__p1p2`
(GettableParameter) → `.qua_result_var` (the QUA bool variable).

Each segment is a `getattr` call. If the final resolved object is callable,
it is called and its return value is used. This enables patterns like
resolving a method that returns a dynamically computed QUA expression.

---

## Sweep generation

`Measurement.set_sweeps(*dicts)` takes one dict per axis:
```python
meas.set_sweeps(
    {meas.parity_init.t_wait_at_t1: np.linspace(100, 1000, 50)},  # outer
    {meas.parity_read.threshold: np.linspace(0, 0.01, 20)},       # inner
)
```

Each dict becomes a `Sweep` object. `recursive_sweep_generation` nests them:
the first sweep is the outermost QUA `for_` loop, the last is innermost.
Inside the innermost loop, `qua_before_sequence` / `qua_sequence` /
`qua_after_sequence` are called.

Snake scanning (boustrophedon) is supported via `Sweep.snake_scan`.

---

## ReadSequence and readout pipeline

A `ReadSequence` extends `SubSequence` with:
- **Signals** — named logical channels (e.g. `p1p2`, `p7p8`)
- **Readout groups** — ordered processing stages: `ref`, `read`, `diff`, `state`, `set_feedback`
- **AbstractReadouts** — each produces one or more `GettableParameter`s

### Readout group ordering (typical PSB readout)

1. `ref` — measure reference point (DcAverage)
2. `read` — measure readout point (DcAverage)
3. `diff` — compute difference (Difference readout)
4. `state` — threshold the difference (Threshold readout → bool gettable)
5. `set_feedback` — (optional) set feedback variables for heralding

### AbstractReadout naming

Full name: `{group_name}__{readout_name}` (e.g. `state__p1p2`).
The gettable is added to the Signal and accessible as:
`read_sequence.signal_name.gettable_name` (e.g. `parity_read.p1p2.state__p1p2`).

---

## Dict-based composition internals

`_add_subsequences_from_dict()` processes each entry:

| Dict keys present | Behavior |
|---|---|
| `'sub_sequences'` only | Creates an empty container SubSequence, recurses into children |
| `'config'` | Uses the config's `'sequence'` class, `'parameters'`, and optional readout keys |
| `'sequence'` | Overrides the class from config (if both given) |
| `'kwargs'` | Passed as `**kwargs` to the SubSequence constructor |

The sequence class is instantiated via `_add_subsequence()`:
```python
seq_instance = subsequence_class(parent=self, name=name, sequence_config=config, **kwargs)
```

---

## GenericTuningInterface (input streams)

Allows real-time parameter updates without recompilation:
- Parameters are declared as QUA input streams
- Host pushes new values via `advance_input_stream` between resumes
- The QUA program reads updated values each iteration

Used for adaptive calibrations, ML-driven tuning, live Larmor tracking.

---

## Ekans (hot-reload)

`Ekans` enables swapping sub-sequences or their configs on a running measurement
without full recompilation. It patches the sequence tree and regenerates only
the affected QUA code sections.

---

## Key files to read when debugging

| Symptom | Start here |
|---|---|
| Parameter not found / TypeError on init | `sub_sequence.py:map_arbok_params()`, `sequence_base.py:_add_param()` |
| QUA compilation error | `sequence_base.py:get_qua_code()`, check lifecycle hook order |
| Step requirement not gating | `measurement.py:qua_check_step_requirements()`, verify `add_step_requirement` is called in `qua_declare` |
| Readout/gettable not streaming | `read_sequence.py:qua_stream()`, `abstract_readout.py:qua_save_streams()` |
| Sweep not working | `sweep.py:qua_generate_parameter_sweep()`, `sequence_base.py:recursive_sweep_generation()` |
| Variable path not resolving | `measurement.py:find_parameter_from_sub_sequence()`, check attribute names at each segment |
| Dict composition failing | `sequence_base.py:_add_subsequences_from_dict()` and `_prepare_adding_subsequence()` |

---

## Extending the framework: guidelines

1. **Prefer composition over modification** — write new SubSequences rather
   than patching existing ones
2. **Never break the lifecycle hook contract** — if you override `qua_declare`,
   call `super().qua_declare()` unless you fully replace it
3. **Register parameters on the correct level** — shared params go in
   `master_config`, sequence-specific params go in the sequence config dict
4. **Test compilation** — always assert `get_qua_program_as_str()` succeeds
   and contains expected structures
5. **Keep ParameterClass frozen** — it must be a `@dataclass(frozen=True)`;
   mutable state goes on the class instance, not in the parameter declaration
