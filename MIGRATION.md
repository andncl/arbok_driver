# Migration Guide: Hardware-Agnostic Arbok

This document explains how to migrate existing `SubSequence` and `ReadSequence` classes
from the QUA-specific API (`qua.*`) to the hardware-agnostic `arbok.*` API.

## Overview of Changes

Arbok now supports swappable hardware backends. The default backend remains **QuaBackend**
(Quantum Machines OPX), so existing code continues to work unchanged. A new **SimBackend**
enables waveform simulation without hardware.

### Key concepts

| Before | After | Notes |
|--------|-------|-------|
| `qua_sequence()` | `fpga_sequence()` | New primary hook; `qua_sequence()` still works |
| `qua_before_sequence()` | `fpga_before_sequence()` | Same pattern |
| `qua_after_sequence()` | `fpga_after_sequence()` | Same pattern |
| `qua_declare()` | `fpga_declare()` | Same pattern |
| `qua_stream()` | `fpga_stream()` | Same pattern |
| `param.qua` | `param.hw_var` | `.qua` is a backwards-compatible alias |
| `from qm import qua; qua.wait(...)` | `arbok.wait(...)` | All operations below |

## Step-by-Step Migration

### 1. Replace `qua.*` calls with `arbok.*` equivalents

```python
# Before
from qm import qua

class MySequence(SubSequence):
    def qua_sequence(self):
        qua.align(*self.elements)
        qua.wait(self.arbok_params.t_wait.qua, *self.elements)
        qua.assign(self.my_var, 0)

# After
from arbok_driver import arbok

class MySequence(SubSequence):
    def fpga_sequence(self):
        arbok.align(*self.elements)
        arbok.wait(self.arbok_params.t_wait.hw_var, *self.elements)
        arbok.assign(self.my_var, 0)
```

### 2. Operation mapping reference

| QUA call | arbok equivalent |
|----------|-----------------|
| `qua.align(*elements)` | `arbok.align(*elements)` |
| `qua.wait(duration, *elements)` | `arbok.wait(duration, *elements)` |
| `qua.assign(var, value)` | `arbok.assign(var, value)` |
| `qua.save(var, stream)` | `arbok.save(var, stream)` |
| `qua.measure(op, element, *outputs)` | `arbok.measure(op, element, *outputs)` |
| `qua.integration.full(weights, var)` | `arbok.integration_full(weights, var)` |
| `qua.play(pulse, element)` | `arbok.play_pulse(pulse, element)` |
| `qua.frame_rotation_2pi(angle, el)` | `arbok.frame_rotation(angle, el)` |
| `qua.ramp_to_zero(element)` | `arbok.ramp_to_zero(element)` |
| `qua.declare(type, value=...)` | `arbok.declare(type, value=...)` |
| `qua.declare_stream()` | `arbok.declare_stream()` |
| `qua.amp(value)` | `arbok.amp(value)` |
| `arbok.ramp(...)` | `arbok.play(...)` (ramp is deprecated alias) |
| `Cast.mul_int_by_fixed(a, b)` | `arbok.cast_mul_int_by_fixed(a, b)` |
| `Cast.mul_fixed_by_int(a, b)` | `arbok.cast_mul_fixed_by_int(a, b)` |

### 3. Control flow mapping

```python
# Before (QUA)
with qua.for_(var=i, init=0, cond=i < N, update=i + 1):
    ...
with qua.if_(condition):
    ...
with qua.else_():
    ...
with qua.while_(condition):
    ...
with qua.switch_(var, unsafe=True):
    with qua.case_(0):
        ...

# After (arbok)
with arbok.for_loop(variable=i, init=0, condition=i < N, update=i + 1):
    ...
with arbok.if_block(condition):
    ...
with arbok.else_block():
    ...
with arbok.while_loop(condition):
    ...
with arbok.switch_block(var, unsafe=True):
    with arbok.case_block(0):
        ...
```

### 4. Replace `.qua` with `.hw_var`

```python
# Before
amplitude = self.arbok_params.voltage.qua
duration = self.arbok_params.t_wait.qua

# After
amplitude = self.arbok_params.voltage.hw_var
duration = self.arbok_params.t_wait.hw_var
```

The `.qua` accessor still works as a backwards-compatible alias but `.hw_var` is preferred.

### 5. Rename method hooks

Rename your sequence methods from `qua_*` to `fpga_*`:

```python
# Before
class MySequence(SubSequence):
    def qua_declare(self): ...
    def qua_before_sequence(self): ...
    def qua_sequence(self): ...
    def qua_after_sequence(self): ...
    def qua_stream(self): ...

# After
class MySequence(SubSequence):
    def fpga_declare(self): ...
    def fpga_before_sequence(self): ...
    def fpga_sequence(self): ...
    def fpga_after_sequence(self): ...
    def fpga_stream(self): ...
```

The `qua_*` methods are kept as deprecated aliases. When using `QuaBackend`, the dispatch
system automatically falls back to `qua_*` if no `fpga_*` override is found.

**Important**: If you override a `qua_*` method and your code is run on a non-QUA backend
(e.g. SimBackend), a `NotImplementedError` is raised. Only `fpga_*` methods work across
all backends.

### 5b. Backend-specific overrides

If you need logic that differs per backend (e.g. raw QUA SDK calls for performance),
use the double-underscore suffix with the backend name:

```python
class MySequence(SubSequence):
    def fpga_sequence(self):
        """Default — works on all backends."""
        arbok.align(*self.elements)
        arbok.play(...)

    def fpga_sequence__qua(self):
        """QUA-specific — only runs when QuaBackend is active."""
        from qm import qua
        qua.align(*self.elements)
        qua.play(...)  # raw QUA for special cases

    def fpga_sequence__sim(self):
        """Sim-specific — only runs when SimBackend is active."""
        ...
```

**Resolution order** (first match wins):
1. `fpga_<hook>__<backend.name>` — backend-specific override
2. `fpga_<hook>` — hardware-agnostic (if user overrides it)
3. `qua_<hook>` — legacy fallback (QuaBackend only, deprecated)
4. Default `fpga_<hook>` — iterates child sub_sequences

Each backend has a `name` attribute: `QuaBackend.name = 'qua'`, `SimBackend.name = 'sim'`.

**Migrating legacy `qua_sequence()` code:** If your `qua_sequence()` uses raw QUA SDK
calls, rename it to `fpga_sequence__qua()` — it will only run on the QUA backend, and
the dispatch won't require you to provide a hardware-agnostic version.

### 6. Replace `arbok.ramp()` with `arbok.play()`

```python
# Before
arbok.ramp(
    elements=self.elements,
    reference=self.arbok_params.v_home,
    target=self.arbok_params.v_level,
    operation='unit_ramp',
)

# After (identical signature, just renamed)
arbok.play(
    elements=self.elements,
    reference=self.arbok_params.v_home,
    target=self.arbok_params.v_level,
    operation='unit_ramp',
)
```

`arbok.ramp()` still works but emits a `DeprecationWarning`.

## Using the Simulation Backend

```python
from arbok_driver import ArbokDriver, SimBackend

# Create driver with simulation backend
driver = ArbokDriver(name='sim', backend=SimBackend())

# ... set up measurement, add sequences ...

# After compilation, retrieve waveforms
waveforms = driver.backend.get_waveforms()
# Returns: dict[str, NDArray] - element name -> samples at 1 GS/s
```

## Backwards Compatibility

- All existing `qua_*` methods continue to work with `QuaBackend`
- `.qua` property on parameters still works (alias for `.hw_var`)
- `arbok.ramp()` still works (deprecated alias for `arbok.play()`)
- No changes required for code that only targets QUA hardware

## Minimal Migration (recommended first step)

If you want to maintain backwards compatibility while enabling future backend support:

1. Add `fpga_sequence()` alongside your existing `qua_sequence()`
2. Use `arbok.*` operations in the new method
3. Use `.hw_var` instead of `.qua` in the new method
4. Keep `qua_sequence()` as-is for reference

The dispatch system will prefer `fpga_sequence()` when present.

---

## Deprecated / Legacy API (scheduled for removal)

The following attributes, methods, and aliases are kept for backwards compatibility but
**will be removed in a future release**. Migrate to the new names now.

### Device

| Legacy | Replacement | Notes |
|--------|-------------|-------|
| `Device(opx_config=...)` | `Device(hardware_config=...)` | Emits `DeprecationWarning` |

### ArbokDriver

| Legacy | Replacement | Notes |
|--------|-------------|-------|
| `driver.connect_opx(host, config)` | `driver.connect_hardware(host, config=config)` | Delegates to `backend.connect()` |
| `driver.reconnect_opx(host, config)` | `driver.reconnect_hardware(host, config=config)` | Delegates to `backend.disconnect()` + `connect()` |
| `driver.print_qua_program_to_file(path, prog)` | `driver.print_program_to_file(path, prog)` | Backend-agnostic name |
| `driver.qmm` | `driver.backend.qmm` | QUA-specific state now lives on QuaBackend |
| `driver.opx` | `driver.backend.opx` | QUA-specific state now lives on QuaBackend |
| `driver.qm_job` | `driver.backend.qm_job` | QUA-specific state now lives on QuaBackend |
| `driver.result_handles` | `driver.backend.result_handles` | QUA-specific state now lives on QuaBackend |
| `driver.host_ip` | `driver.backend.host_ip` | QUA-specific state now lives on QuaBackend |

### SequenceBase / SubSequence

| Legacy | Replacement | Notes |
|--------|-------------|-------|
| `seq.opx_config` | `seq.hardware_config` | Generic name for hardware config dict |
| `seq.get_qua_program()` | `seq.compile_program()` | Backend-agnostic name |
| `seq.get_qua_code()` | `seq.compile_fpga_code()` | Backend-agnostic name |
| `seq.get_qua_program_as_str()` | `seq.get_program_as_str()` | Backend-agnostic name |
| `qua_sequence()` | `fpga_sequence()` | See hook migration above |
| `qua_before_sequence()` | `fpga_before_sequence()` | See hook migration above |
| `qua_after_sequence()` | `fpga_after_sequence()` | See hook migration above |
| `qua_declare()` | `fpga_declare()` | See hook migration above |
| `qua_stream()` | `fpga_stream()` | See hook migration above |

### AbstractReadout

| Legacy | Replacement | Notes |
|--------|-------------|-------|
| `readout.qua_measure()` | `readout.fpga_measure()` | Override `fpga_measure()` in new subclasses |
| `readout.qua_declare_variables()` | `readout.fpga_declare_variables()` | Override for custom declarations |
| `readout.qua_save_variables()` | `readout.fpga_save_variables()` | Override for custom save logic |
| `readout.qua_save_streams()` | `readout.fpga_save_streams()` | Override for custom stream saving |
| `readout.qua_measure_and_save()` | `readout.fpga_measure_and_save()` | Emits `DeprecationWarning` |

### GettableParameter / GettableParameterBase

| Legacy | Replacement | Notes |
|--------|-------------|-------|
| `gettable.qua_declare_variables()` | `gettable.fpga_declare_variables()` | Emits `DeprecationWarning` |
| `gettable.qua_save_variables()` | `gettable.fpga_save_variables()` | Emits `DeprecationWarning` |
| `gettable.qua_save_streams()` | `gettable.fpga_save_streams()` | Emits `DeprecationWarning` |
| `gettable.qua_stream` | `gettable.hw_stream` | Property alias (no warning) |
| `gettable.qua_result_var` | `gettable.hw_result_var` | Property alias (no warning) |
| `gettable.qua_var_index` | `gettable.hw_var_index` | Property alias (GettableParameterMulti) |
| `gettable.qua_result_array` | `gettable.hw_result_array` | Property alias (GettableParameterMulti) |

### Parameters

| Legacy | Replacement | Notes |
|--------|-------------|-------|
| `param.qua` | `param.hw_var` | Hardware variable handle |

### arbok module

| Legacy | Replacement | Notes |
|--------|-------------|-------|
| `arbok.ramp(...)` | `arbok.play(...)` | Emits `DeprecationWarning` |
