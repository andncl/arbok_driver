"""Module containing the abstract Backend class for hardware abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from numpy.typing import NDArray
    from .measurement import Measurement
    from .parameters.gettable_parameter_base import GettableParameterBase


class HardwareVariable:
    """Opaque handle representing a variable on the target hardware.

    For the QUA backend this wraps a QuaVariable. For the simulation backend
    it wraps a plain Python value. User code should not inspect internals —
    pass these to arbok.* operations or to backend methods.
    """

    def __init__(self, value: Any = None, var_type: type | None = None):
        self.value = value
        self.var_type = var_type

    def __repr__(self):
        return f"HardwareVariable({self.value!r}, type={self.var_type})"


class HardwareStream:
    """Opaque handle representing a data stream on the target hardware."""

    def __init__(self, value: Any = None):
        self.value = value

    def __repr__(self):
        return f"HardwareStream({self.value!r})"


class Backend(ABC):
    """Abstract base class defining the hardware backend interface.

    Every backend must implement these methods. They fall into two categories:

    1. **User-facing operations** — called from SubSequence.sequence() and
       AbstractReadout.measure() via the arbok.* API layer.
    2. **Framework operations** — called by the arbok framework to compile
       programs, manage sweeps, and fetch results.
    """

    # ──────────────────────────────────────────────────────────────────────
    # Pulse / Element Operations (user-facing)
    # ──────────────────────────────────────────────────────────────────────

    @abstractmethod
    def play(
        self,
        element: str,
        operation: str,
        amplitude: Any | None = None,
        duration: Any | None = None,
    ) -> None:
        """Play a pulse operation on an element.

        Args:
            element: Target element name.
            operation: Operation/pulse name from config.
            amplitude: Runtime amplitude scaling (HardwareVariable or float).
            duration: Pulse duration in clock cycles (HardwareVariable or int).
        """

    @abstractmethod
    def wait(self, duration: Any, elements: list[str]) -> None:
        """Wait for a given number of clock cycles on elements.

        Args:
            duration: Wait duration in clock cycles (HardwareVariable or int).
            elements: Elements to wait on.
        """

    @abstractmethod
    def align(self, elements: list[str] | None = None) -> None:
        """Synchronize elements. If elements is None, align all.

        Args:
            elements: Elements to align, or None for all.
        """

    @abstractmethod
    def measure(
        self,
        operation: str,
        element: str,
        outputs: list[Any] | None = None,
    ) -> None:
        """Perform a measurement on an element.

        Args:
            operation: Measurement operation name.
            element: Target element.
            outputs: Integration/demodulation output specifications.
        """

    @abstractmethod
    def ramp_to_zero(self, element: str) -> None:
        """Ramp a sticky element back to zero voltage.

        Args:
            element: Element to ramp down.
        """

    @abstractmethod
    def frame_rotation(self, angle: float | Any, element: str) -> None:
        """Rotate the frame of an element by a fraction of 2pi.

        Args:
            angle: Rotation angle as fraction of 2pi.
            element: Target element.
        """

    @abstractmethod
    def integration_full(
        self, weights: str, output_var: Any, element: str | None = None
    ) -> Any:
        """Create a full integration output specification.

        Args:
            weights: Integration weights name.
            output_var: Variable to store the result.
            element: Optional output element.

        Returns:
            An output specification to pass to measure().
        """

    # ──────────────────────────────────────────────────────────────────────
    # Variable System (user-facing)
    # ──────────────────────────────────────────────────────────────────────

    @abstractmethod
    def declare(
        self,
        var_type: type,
        value: Any | None = None,
        size: int | None = None,
    ) -> HardwareVariable:
        """Declare a variable on the hardware.

        Args:
            var_type: Type of variable (int, bool, or fixed-point).
            value: Initial value or array of values.
            size: Array size (for array declarations).

        Returns:
            A HardwareVariable handle.
        """

    @abstractmethod
    def declare_stream(self) -> HardwareStream:
        """Declare a data output stream.

        Returns:
            A HardwareStream handle.
        """

    @abstractmethod
    def assign(self, variable: Any, value: Any) -> None:
        """Assign a value or expression to a hardware variable.

        Args:
            variable: Target HardwareVariable.
            value: Value or expression to assign.
        """

    @abstractmethod
    def save(self, variable: Any, stream: Any) -> None:
        """Save a variable value to a stream.

        Args:
            variable: Variable to save.
            stream: Target stream.
        """

    # ──────────────────────────────────────────────────────────────────────
    # Control Flow (user-facing)
    # ──────────────────────────────────────────────────────────────────────

    @abstractmethod
    @contextmanager
    def for_loop(
        self,
        variable: Any,
        init: Any,
        condition: Any,
        update: Any,
    ) -> Generator[None, None, None]:
        """Context manager for a for-loop.

        Args:
            variable: Loop variable.
            init: Initial value.
            condition: Loop condition.
            update: Update expression.
        """
        yield  # pragma: no cover

    @abstractmethod
    @contextmanager
    def while_loop(self, condition: Any) -> Generator[None, None, None]:
        """Context manager for a while-loop.

        Args:
            condition: Loop condition expression.
        """
        yield  # pragma: no cover

    @abstractmethod
    @contextmanager
    def if_block(self, condition: Any) -> Generator[None, None, None]:
        """Context manager for an if-branch.

        Args:
            condition: Boolean condition.
        """
        yield  # pragma: no cover

    @abstractmethod
    @contextmanager
    def else_block(self) -> Generator[None, None, None]:
        """Context manager for an else-branch (must follow if_block)."""
        yield  # pragma: no cover

    @abstractmethod
    @contextmanager
    def switch_block(self, variable: Any, unsafe: bool = False) -> Generator[None, None, None]:
        """Context manager for a switch statement.

        Args:
            variable: Variable to switch on.
            unsafe: If True, no bounds checking.
        """
        yield  # pragma: no cover

    @abstractmethod
    @contextmanager
    def case_block(self, value: int) -> Generator[None, None, None]:
        """Context manager for a case within a switch.

        Args:
            value: Case value to match.
        """
        yield  # pragma: no cover

    # ──────────────────────────────────────────────────────────────────────
    # Arithmetic Helpers (user-facing)
    # ──────────────────────────────────────────────────────────────────────

    @abstractmethod
    def amp(self, amplitude: Any) -> Any:
        """Create an amplitude modifier for pulse operations.

        Args:
            amplitude: Amplitude value (variable or literal).

        Returns:
            Backend-specific amplitude representation.
        """

    @abstractmethod
    def cast_mul_fixed_by_int(self, fixed_val: Any, int_val: Any) -> Any:
        """Multiply a fixed-point value by an integer.

        Args:
            fixed_val: Fixed-point value.
            int_val: Integer value.

        Returns:
            Result as hardware expression.
        """

    @abstractmethod
    def cast_mul_int_by_fixed(self, int_val: Any, fixed_val: Any) -> Any:
        """Multiply an integer by a fixed-point value.

        Args:
            int_val: Integer value.
            fixed_val: Fixed-point value.

        Returns:
            Result as hardware expression.
        """

    # ──────────────────────────────────────────────────────────────────────
    # Type Constants
    # ──────────────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def fixed_type(self) -> Any:
        """The fixed-point type for this backend (e.g. qua.fixed)."""

    # ──────────────────────────────────────────────────────────────────────
    # Connection Management
    # ──────────────────────────────────────────────────────────────────────

    @abstractmethod
    def connect(
        self,
        host_ip: str,
        config: dict,
        reconnect: bool = False,
        **kwargs,
    ) -> None:
        """Connect to the hardware.

        Args:
            host_ip: Address of the hardware (e.g. IP for OPX).
            config: Hardware configuration dictionary.
            reconnect: If True, reuses existing manager/session.
            **kwargs: Backend-specific connection arguments.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """Close the current hardware connection."""

    # ──────────────────────────────────────────────────────────────────────
    # Framework Operations (not user-facing — called by arbok internals)
    # ──────────────────────────────────────────────────────────────────────

    @abstractmethod
    @contextmanager
    def program_context(self) -> Generator[Any, None, None]:
        """Context manager that opens a new program for compilation.

        Yields:
            A program handle (e.g. qua Program object).
        """
        yield  # pragma: no cover

    @abstractmethod
    @contextmanager
    def infinite_loop(self) -> Generator[None, None, None]:
        """Context manager for an infinite loop (framework use)."""
        yield  # pragma: no cover

    @abstractmethod
    def pause(self) -> None:
        """Pause program execution (framework use)."""

    @abstractmethod
    @contextmanager
    def stream_processing(self) -> Generator[None, None, None]:
        """Context manager for stream processing block (framework use)."""
        yield  # pragma: no cover

    @abstractmethod
    def declare_input_stream(
        self, var_type: Any, name: str, size: int
    ) -> Any:
        """Declare an input stream for client-side data injection.

        Args:
            var_type: Type of stream data.
            name: Stream identifier.
            size: Number of elements.

        Returns:
            Input stream handle.
        """

    @abstractmethod
    def advance_input_stream(self, stream: Any) -> None:
        """Advance an input stream to the next set of values.

        Args:
            stream: Input stream handle.
        """

    @abstractmethod
    def load_waveform(
        self, operation: str, index: Any, element: str
    ) -> None:
        """Load a pre-computed waveform by index (waveform caching).

        Args:
            operation: Operation name.
            index: Waveform index variable.
            element: Target element.
        """

    @abstractmethod
    def stream_buffer(self, stream: Any, *shape: int) -> Any:
        """Create a buffered view of a stream for saving.

        Args:
            stream: Stream handle.
            *shape: Buffer dimensions.

        Returns:
            Buffered stream handle.
        """

    @abstractmethod
    def stream_save(self, buffered_stream: Any, name: str) -> None:
        """Save a buffered stream with a given name.

        Args:
            buffered_stream: Buffered stream from stream_buffer().
            name: Name to save under.
        """

    @abstractmethod
    def compile_and_execute(
        self,
        measurement: Measurement,
        program: Any,
        config: dict,
    ) -> Any:
        """Compile the program and execute it on hardware.

        Args:
            measurement: The Measurement instance.
            program: Program handle from program_context().
            config: Hardware configuration dict.

        Returns:
            A job handle or result object.
        """

    @abstractmethod
    def fetch_results(
        self,
        measurement: Measurement,
        gettables: dict[str, GettableParameterBase],
    ) -> dict[GettableParameterBase, NDArray]:
        """Fetch measurement results from the hardware.

        Args:
            measurement: The Measurement instance.
            gettables: Registered gettable parameters.

        Returns:
            Dict mapping gettables to their result arrays.
        """

    @abstractmethod
    def generate_program_script(self, program: Any, config: dict) -> str:
        """Generate a human-readable script of the compiled program.

        Args:
            program: Program handle.
            config: Hardware configuration.

        Returns:
            String representation of the program.
        """

    @abstractmethod
    def run(self, program: Any, **kwargs) -> Any:
        """Execute a compiled program on the hardware.

        Args:
            program: Program handle from program_context().
            **kwargs: Backend-specific execution arguments.

        Returns:
            A job handle or result object.
        """

    @abstractmethod
    def simulate(
        self,
        program: Any,
        config: dict,
        duration_ns: int = 10000,
        **kwargs,
    ) -> Any:
        """Simulate the compiled program and return results.

        Args:
            program: Program handle from program_context().
            config: Hardware configuration dict.
            duration_ns: Simulation duration in nanoseconds.
            **kwargs: Backend-specific simulation options.

        Returns:
            Backend-specific simulation result.
        """
