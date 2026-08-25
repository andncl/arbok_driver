"""QuaBackend — wraps Quantum Machines QUA SDK calls."""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import numpy as np
from qm import qua, generate_qua_script, SimulationConfig
from qm.qua.lib import Cast

from arbok_driver.backend import Backend, HardwareVariable, HardwareStream

if TYPE_CHECKING:
    from collections.abc import Generator
    from numpy.typing import NDArray
    from arbok_driver.measurement import Measurement
    from arbok_driver.parameters.gettable_parameter_base import GettableParameterBase
    from qm.jobs.running_qm_job import RunningQmJob
    from qm.quantum_machine import QuantumMachine
    from qm.quantum_machines_manager import QuantumMachinesManager
    from qm import StreamsManager
    from qm.api.v2.qm_api import QmApi


class QuaBackend(Backend):
    """Backend implementation targeting the Quantum Machines OPX via QUA."""

    name = 'qua'

    def __init__(self):
        self.qmm: QuantumMachinesManager | None = None
        self.opx: QuantumMachine | QmApi | None = None
        self.qm_job: RunningQmJob | None = None
        self.result_handles: StreamsManager | None = None
        self.host_ip: str | None = None

    def connect(
        self,
        host_ip: str,
        config: dict,
        reconnect: bool = False,
        **kwargs,
    ) -> None:
        """Connect to the OPX hardware.

        Args:
            host_ip: IP address of the OPX.
            config: Hardware configuration dictionary.
            reconnect: If True, reuses existing QMM connection.
            **kwargs: Passed to QuantumMachinesManager constructor.
        """
        from qm.quantum_machines_manager import QuantumMachinesManager
        if not reconnect:
            self.qmm = QuantumMachinesManager(host=host_ip, **kwargs)
            self.host_ip = host_ip
        self.opx = self.qmm.open_qm(config, close_other_machines=True)

    def disconnect(self) -> None:
        """Close the current OPX connection."""
        if self.opx is not None:
            self.opx.close()
            self.qmm.close_all_quantum_machines()
            self.opx = None

    def run(self, program: Any, **kwargs) -> Any:
        """Execute a compiled program on the OPX.

        Args:
            program: Compiled QUA program handle.
            **kwargs: Passed to opx.execute().

        Returns:
            The running job handle.
        """
        self.qm_job = self.opx.execute(program, **kwargs)
        self.result_handles = self.qm_job.result_handles
        return self.qm_job

    # ──────────────────────────────────────────────────────────────────────
    # Pulse / Element Operations
    # ──────────────────────────────────────────────────────────────────────

    def play(
        self,
        element: str,
        operation: str,
        amplitude: Any | None = None,
        duration: Any | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"element": element}
        if amplitude is not None:
            kwargs["pulse"] = operation * qua.amp(amplitude)
        else:
            kwargs["pulse"] = operation
        if duration is not None:
            kwargs["duration"] = duration
        qua.play(**kwargs)

    def wait(self, duration: Any, elements: list[str]) -> None:
        qua.wait(duration, *elements)

    def align(self, elements: list[str] | None = None) -> None:
        if elements:
            qua.align(*elements)
        else:
            qua.align()

    def measure(
        self,
        operation: str,
        element: str,
        outputs: list[Any] | None = None,
    ) -> None:
        if outputs:
            qua.measure(operation, element, *outputs)
        else:
            qua.measure(operation, element)

    def ramp_to_zero(self, element: str) -> None:
        qua.ramp_to_zero(element)

    def frame_rotation(self, angle: float | Any, element: str) -> None:
        qua.frame_rotation_2pi(angle, element)

    def integration_full(
        self, weights: str, output_var: Any, element: str | None = None
    ) -> Any:
        if element is not None:
            return qua.integration.full(weights, output_var, element)
        return qua.integration.full(weights, output_var)

    # ──────────────────────────────────────────────────────────────────────
    # Variable System
    # ──────────────────────────────────────────────────────────────────────

    def declare(
        self,
        var_type: type,
        value: Any | None = None,
        size: int | None = None,
    ) -> Any:
        hw_type = qua.fixed if var_type is float else var_type
        kwargs: dict[str, Any] = {}
        if value is not None:
            kwargs["value"] = value
        if size is not None:
            kwargs["size"] = size
        return qua.declare(hw_type, **kwargs)

    def declare_stream(self) -> Any:
        return qua.declare_stream()

    def assign(self, variable: Any, value: Any) -> None:
        qua.assign(variable, value)

    def save(self, variable: Any, stream: Any) -> None:
        qua.save(variable, stream)

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
        with qua.for_(variable, init, condition, update):
            yield

    @contextmanager
    def while_loop(self, condition: Any) -> Generator[None, None, None]:
        with qua.while_(condition):
            yield

    @contextmanager
    def if_block(self, condition: Any) -> Generator[None, None, None]:
        with qua.if_(condition):
            yield

    @contextmanager
    def else_block(self) -> Generator[None, None, None]:
        with qua.else_():
            yield

    @contextmanager
    def switch_block(self, variable: Any, unsafe: bool = False) -> Generator[None, None, None]:
        with qua.switch_(variable, unsafe=unsafe):
            yield

    @contextmanager
    def case_block(self, value: int) -> Generator[None, None, None]:
        with qua.case_(value):
            yield

    # ──────────────────────────────────────────────────────────────────────
    # Arithmetic / Type Helpers
    # ──────────────────────────────────────────────────────────────────────

    def amp(self, amplitude: Any) -> Any:
        return qua.amp(amplitude)

    def cast_mul_fixed_by_int(self, fixed_val: Any, int_val: Any) -> Any:
        return Cast.mul_fixed_by_int(fixed_val, int_val)

    def cast_mul_int_by_fixed(self, int_val: Any, fixed_val: Any) -> Any:
        return Cast.mul_int_by_fixed(int_val, fixed_val)

    @property
    def fixed_type(self) -> Any:
        return float

    # ──────────────────────────────────────────────────────────────────────
    # Framework Operations
    # ──────────────────────────────────────────────────────────────────────

    @contextmanager
    def program_context(self) -> Generator[Any, None, None]:
        with qua.program() as prog:
            yield prog

    @contextmanager
    def infinite_loop(self) -> Generator[None, None, None]:
        with qua.infinite_loop_():
            yield

    def pause(self) -> None:
        qua.pause()

    @contextmanager
    def stream_processing(self) -> Generator[None, None, None]:
        with qua.stream_processing():
            yield

    def declare_input_stream(
        self, var_type: Any, name: str, size: int
    ) -> Any:
        hw_type = qua.fixed if var_type is float else var_type
        return qua.declare_input_stream(hw_type, name=name, size=size)

    def advance_input_stream(self, stream: Any) -> None:
        qua.advance_input_stream(stream)

    def load_waveform(
        self, operation: str, index: Any, element: str
    ) -> None:
        qua.load_waveform(operation, index, element)

    def stream_buffer(self, stream: Any, *shape: int) -> Any:
        return stream.buffer(*shape)

    def stream_save(self, buffered_stream: Any, name: str) -> None:
        buffered_stream.save(name)

    def compile_and_execute(
        self,
        measurement: Measurement,
        program: Any,
        config: dict,
    ) -> Any:
        import copy
        device = measurement.driver.device
        device.config = copy.deepcopy(config)
        if self.opx is not None:
            self.disconnect()
        self.connect(self.host_ip, device.config, reconnect=True)
        return self.run(program)

    def fetch_results(
        self,
        measurement: Measurement,
        gettables: dict[str, GettableParameterBase],
    ) -> dict[GettableParameterBase, NDArray]:
        return measurement.fetch_all_results()

    def generate_program_script(self, program: Any, config: dict) -> str:
        return generate_qua_script(program, config)

    def simulate(
        self,
        program: Any,
        config: dict,
        duration_ns: int = 10000,
        **kwargs,
    ) -> Any:
        from arbok_driver import utils
        qmm = kwargs.pop("qmm", None) or self.qmm
        if qmm is None:
            raise ConnectionError(
                "QuaBackend.simulate() requires a connected QMM. "
                "Call connect_hardware() first or pass qmm=... explicitly.")
        sim_job = qmm.simulate(
            config,
            program,
            SimulationConfig(duration=int(duration_ns // 4)),
            **kwargs,
        )
        sim_job.wait_until("Done")
        sim_results = sim_job.get_simulated_samples()
        fig = utils.plot_simulation(sim_results, config)
        fig.show()
        return sim_job
