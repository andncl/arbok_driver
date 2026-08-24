"""SimBackend — waveform simulation backend producing sample-by-sample output."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from arbok_driver.backend import Backend, HardwareVariable, HardwareStream

if TYPE_CHECKING:
    from collections.abc import Generator
    from numpy.typing import NDArray
    from arbok_driver.measurement import Measurement
    from arbok_driver.parameters.gettable_parameter_base import GettableParameterBase


CLOCK_CYCLE_NS = 4
SAMPLE_RATE_GHZ = 1.0


@dataclass
class SimVariable:
    """A simulated hardware variable — just holds a Python value."""
    value: Any = 0
    var_type: type = int
    size: int | None = None

    def __repr__(self):
        return f"SimVariable({self.value!r})"


@dataclass
class SimStream:
    """A simulated stream — collects saved values."""
    data: list = field(default_factory=list)
    name: str | None = None

    def buffer(self, *shape):
        return SimBufferedStream(stream=self, shape=shape)


@dataclass
class SimBufferedStream:
    """Buffered view of a SimStream for save operations."""
    stream: SimStream = None
    shape: tuple = ()

    def save(self, name: str):
        self.stream.name = name


@dataclass
class SimIntegrationOutput:
    """Placeholder for an integration output in simulation."""
    weights: str = ""
    output_var: SimVariable = None
    element: str | None = None


class ElementTimeline:
    """Tracks the waveform output of a single element."""

    def __init__(self, name: str):
        self.name = name
        self.samples: list[float] = []
        self.current_voltage: float = 0.0
        self.frame_phase: float = 0.0

    @property
    def time_ns(self) -> int:
        return len(self.samples)

    def append_samples(self, waveform: list[float] | NDArray) -> None:
        """Append waveform samples and update current_voltage to last sample."""
        for sample in waveform:
            self.samples.append(float(sample))
        if len(waveform) > 0:
            self.current_voltage = float(waveform[-1])

    def append_wait(self, duration_ns: int) -> None:
        """Append a wait period holding at the current voltage."""
        self.samples.extend([self.current_voltage] * duration_ns)

    def pad_to(self, target_ns: int) -> None:
        """Pad timeline to reach target length (holding current voltage)."""
        if self.time_ns < target_ns:
            self.append_wait(target_ns - self.time_ns)

    def ramp_to_zero(self, ramp_ns: int = 4) -> None:
        """Linearly ramp from current voltage to zero."""
        if ramp_ns <= 0:
            self.current_voltage = 0.0
            return
        ramp = np.linspace(self.current_voltage, 0.0, ramp_ns).tolist()
        self.append_samples(ramp)
        self.current_voltage = 0.0


class SimBackend(Backend):
    """Simulation backend that produces per-element waveform timelines.

    Instead of compiling and executing on real hardware, this backend
    directly interprets sequence operations and accumulates voltage
    samples at 1 GS/s (1 sample per nanosecond).

    After a measurement run, results are available as numpy arrays
    per element.
    """

    def __init__(self):
        self._timelines: dict[str, ElementTimeline] = {}
        self._streams: dict[str, SimStream] = {}
        self._opx_config: dict = {}

    def connect(
        self,
        host_ip: str,
        config: dict,
        reconnect: bool = False,
        **kwargs,
    ) -> None:
        pass

    def disconnect(self) -> None:
        pass

    @property
    def timelines(self) -> dict[str, ElementTimeline]:
        """Access element timelines after simulation."""
        return self._timelines

    def get_waveforms(self) -> dict[str, NDArray]:
        """Return simulation results as numpy arrays per element.

        Returns:
            Dict mapping element names to their voltage waveform arrays.
        """
        return {
            name: np.array(tl.samples, dtype=np.float64)
            for name, tl in self._timelines.items()
        }

    def _get_or_create_timeline(self, element: str) -> ElementTimeline:
        if element not in self._timelines:
            self._timelines[element] = ElementTimeline(element)
        return self._timelines[element]

    def _resolve_value(self, val: Any) -> Any:
        """Resolve a SimVariable or raw value to its Python value."""
        if isinstance(val, SimVariable):
            return val.value
        return val

    # ──────────────────────────────────────────────────────────────────────
    # Pulse / Element Operations
    # ──────────────────────────────────────────────────────────────────────

    def play(
        self,
        element: str,
        operation: Any,
        amplitude: Any | None = None,
        duration: Any | None = None,
    ) -> None:
        if not callable(operation):
            raise TypeError(
                f"SimBackend.play() requires a callable as operation, "
                f"got {type(operation).__name__} '{operation}'. "
                f"Pass a waveform generator: (amplitude, duration_ns) -> samples.")
        tl = self._get_or_create_timeline(element)
        amp_val = self._resolve_value(amplitude) if amplitude is not None else 1.0
        dur_cycles = self._resolve_value(duration) if duration is not None else 25
        dur_ns = int(dur_cycles) * CLOCK_CYCLE_NS
        samples = operation(amp_val, dur_ns)
        tl.append_samples(samples)

    def wait(self, duration: Any, elements: list[str]) -> None:
        dur_cycles = self._resolve_value(duration)
        dur_ns = int(dur_cycles) * CLOCK_CYCLE_NS
        for element in elements:
            tl = self._get_or_create_timeline(element)
            tl.append_wait(dur_ns)

    def align(self, elements: list[str] | None = None) -> None:
        if elements is None:
            elements = list(self._timelines.keys())
        if not elements:
            return
        max_time = max(
            (self._get_or_create_timeline(e).time_ns for e in elements),
            default=0,
        )
        for element in elements:
            self._get_or_create_timeline(element).pad_to(max_time)

    def measure(
        self,
        operation: str,
        element: str,
        outputs: list[Any] | None = None,
    ) -> None:
        tl = self._get_or_create_timeline(element)
        # Simulate a measurement: generate synthetic readout signal
        dur_ns = 100 * CLOCK_CYCLE_NS  # default measurement duration
        measurement_signal = np.random.normal(0, 0.01, dur_ns).tolist()
        tl.append_samples(measurement_signal)

        if outputs:
            for output in outputs:
                if isinstance(output, SimIntegrationOutput) and output.output_var is not None:
                    # Simulate integration: sum of measurement signal
                    integrated = float(np.sum(measurement_signal)) / dur_ns
                    output.output_var.value = integrated

    def ramp_to_zero(self, element: str) -> None:
        tl = self._get_or_create_timeline(element)
        tl.ramp_to_zero(ramp_ns=CLOCK_CYCLE_NS)

    def frame_rotation(self, angle: float | Any, element: str) -> None:
        angle_val = self._resolve_value(angle)
        tl = self._get_or_create_timeline(element)
        tl.frame_phase += float(angle_val) * 2 * np.pi

    def integration_full(
        self, weights: str, output_var: Any, element: str | None = None
    ) -> Any:
        return SimIntegrationOutput(
            weights=weights, output_var=output_var, element=element
        )

    # ──────────────────────────────────────────────────────────────────────
    # Variable System
    # ──────────────────────────────────────────────────────────────────────

    def declare(
        self,
        var_type: type,
        value: Any | None = None,
        size: int | None = None,
    ) -> SimVariable:
        if size is not None:
            init_val = [0] * size if value is None else value
            return SimVariable(value=init_val, var_type=var_type, size=size)
        if value is not None:
            return SimVariable(value=value, var_type=var_type)
        defaults = {int: 0, bool: False, float: 0.0}
        return SimVariable(value=defaults.get(var_type, 0.0), var_type=var_type)

    def declare_stream(self) -> SimStream:
        return SimStream()

    def assign(self, variable: Any, value: Any) -> None:
        resolved = self._resolve_value(value)
        if isinstance(variable, SimVariable):
            variable.value = resolved
        elif isinstance(variable, list):
            pass  # array indexing not fully supported in sim

    def save(self, variable: Any, stream: Any) -> None:
        val = self._resolve_value(variable)
        if isinstance(stream, SimStream):
            stream.data.append(val)

    # ──────────────────────────────────────────────────────────────────────
    # Control Flow
    # ──────────────────────────────────────────────────────────────────────

    @contextmanager
    def for_loop(
        self,
        variable: Any,
        init: Any,
        condition: Any,
        update: Any,
    ) -> Generator[None, None, None]:
        # In simulation, control flow context managers just yield —
        # user code executes in Python naturally. For loops in simulation
        # require the caller to use Python for-loops.
        yield

    @contextmanager
    def while_loop(self, condition: Any) -> Generator[None, None, None]:
        yield

    @contextmanager
    def if_block(self, condition: Any) -> Generator[None, None, None]:
        cond_val = self._resolve_value(condition)
        if cond_val:
            yield
        else:
            # Skip the block — we need a way to not execute the body
            # This is a limitation: in sim mode, if_block executes conditionally
            yield

    @contextmanager
    def else_block(self) -> Generator[None, None, None]:
        yield

    @contextmanager
    def switch_block(self, variable: Any, unsafe: bool = False) -> Generator[None, None, None]:
        yield

    @contextmanager
    def case_block(self, value: int) -> Generator[None, None, None]:
        yield

    # ──────────────────────────────────────────────────────────────────────
    # Arithmetic / Type Helpers
    # ──────────────────────────────────────────────────────────────────────

    def amp(self, amplitude: Any) -> Any:
        return self._resolve_value(amplitude)

    def cast_mul_fixed_by_int(self, fixed_val: Any, int_val: Any) -> Any:
        return self._resolve_value(fixed_val) * self._resolve_value(int_val)

    def cast_mul_int_by_fixed(self, int_val: Any, fixed_val: Any) -> Any:
        return self._resolve_value(int_val) * self._resolve_value(fixed_val)

    @property
    def fixed_type(self) -> type:
        return float

    # ──────────────────────────────────────────────────────────────────────
    # Framework Operations
    # ──────────────────────────────────────────────────────────────────────

    @contextmanager
    def program_context(self) -> Generator[Any, None, None]:
        self._timelines.clear()
        self._streams.clear()
        yield self

    @contextmanager
    def infinite_loop(self) -> Generator[None, None, None]:
        # In simulation, we execute the body exactly once (no real infinite loop)
        yield

    def pause(self) -> None:
        pass

    @contextmanager
    def stream_processing(self) -> Generator[None, None, None]:
        yield

    def declare_input_stream(
        self, var_type: Any, name: str, size: int
    ) -> list:
        return [0] * size

    def advance_input_stream(self, stream: Any) -> None:
        pass

    def load_waveform(
        self, operation: str, index: Any, element: str
    ) -> None:
        pass

    def stream_buffer(self, stream: Any, *shape: int) -> Any:
        if isinstance(stream, SimStream):
            return stream.buffer(*shape)
        return stream

    def stream_save(self, buffered_stream: Any, name: str) -> None:
        if isinstance(buffered_stream, SimBufferedStream):
            buffered_stream.save(name)

    def run(self, program: Any, **kwargs) -> Any:
        return None

    def compile_and_execute(
        self,
        measurement: Measurement,
        program: Any,
        config: dict,
    ) -> Any:
        self._opx_config = config
        return None

    def fetch_results(
        self,
        measurement: Measurement,
        gettables: dict[str, GettableParameterBase],
    ) -> dict[GettableParameterBase, NDArray]:
        results = {}
        for _, gettable in gettables.items():
            results[gettable] = gettable.get_mock_result()
        return results

    def generate_program_script(self, program: Any, config: dict) -> str:
        lines = ["# SimBackend — simulated program", ""]
        for name, tl in self._timelines.items():
            lines.append(f"# Element '{name}': {tl.time_ns} ns, "
                         f"sticky={tl.sticky}")
        return "\n".join(lines)

    def simulate(
        self,
        program: Any,
        config: dict,
        duration_ns: int = 10000,
        **kwargs,
    ) -> dict[str, NDArray]:
        self._opx_config = config
        return self.get_waveforms()

    def reset(self) -> None:
        """Reset all timelines for a fresh simulation."""
        self._timelines.clear()
        self._streams.clear()
