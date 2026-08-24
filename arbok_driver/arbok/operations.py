"""Hardware-agnostic operations dispatched through the active backend.

These functions are the user-facing API for writing sequences. They
dispatch to whichever backend is currently active (QUA, simulation, etc.).
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from .context import get_active_backend

if TYPE_CHECKING:
    from collections.abc import Generator
    from arbok_driver.backend import HardwareVariable, HardwareStream


def play_pulse(
    operation: str,
    element: str,
    amplitude: Any = None,
    duration: Any = None,
) -> None:
    """Play a pulse operation on an element.

    This is the low-level play that maps directly to the hardware's play
    instruction. For voltage-ramping with ParameterMaps, use arbok.play().

    Args:
        operation: Operation/pulse name from config.
        element: Target element name.
        amplitude: Runtime amplitude scaling (variable or float).
        duration: Pulse duration in clock cycles (variable or int).
    """
    get_active_backend().play(element, operation, amplitude, duration)


def wait(duration: Any, *elements: str) -> None:
    """Wait for a given number of clock cycles on elements.

    Args:
        duration: Duration in clock cycles (hw_var or int). 1 cycle = 4 ns.
        *elements: One or more element names to wait on.
    """
    get_active_backend().wait(duration, list(elements))


def align(*elements: str) -> None:
    """Synchronize elements. If no elements given, aligns all.

    Args:
        *elements: Elements to synchronize.
    """
    backend = get_active_backend()
    backend.align(list(elements) if elements else None)


def measure(operation: str, element: str, *outputs: Any) -> None:
    """Perform a measurement on an element.

    Args:
        operation: Measurement operation name (e.g. 'measure').
        element: Target element name.
        *outputs: Integration/demodulation output specifications.
    """
    get_active_backend().measure(operation, element, list(outputs) if outputs else None)


def integration_full(weights: str, output_var: Any, element: str | None = None) -> Any:
    """Create a full integration output specification.

    Args:
        weights: Integration weights name (e.g. 'x_const').
        output_var: Variable to store the integrated result.
        element: Optional output element.

    Returns:
        Output specification to pass to measure().
    """
    return get_active_backend().integration_full(weights, output_var, element)


def ramp_to_zero(element: str) -> None:
    """Ramp a sticky element back to zero voltage.

    Args:
        element: Element to ramp down.
    """
    get_active_backend().ramp_to_zero(element)


def frame_rotation(angle: float | Any, element: str) -> None:
    """Rotate the frame of an element by a fraction of 2pi.

    Args:
        angle: Rotation angle as fraction of 2pi (e.g. 0.25 for pi/2).
        element: Target element.
    """
    get_active_backend().frame_rotation(angle, element)


# ──────────────────────────────────────────────────────────────────────────
# Variable System
# ──────────────────────────────────────────────────────────────────────────

def declare(var_type: type, value: Any = None, size: int | None = None) -> HardwareVariable:
    """Declare a variable on the active backend.

    Args:
        var_type: Type (int, bool, or backend's fixed type).
        value: Initial value or array of values.
        size: Array size for array declarations.

    Returns:
        A HardwareVariable handle.
    """
    return get_active_backend().declare(var_type, value, size)


def declare_stream() -> HardwareStream:
    """Declare a data output stream.

    Returns:
        A HardwareStream handle.
    """
    return get_active_backend().declare_stream()


def assign(variable: Any, value: Any) -> None:
    """Assign a value or expression to a hardware variable.

    Args:
        variable: Target variable (HardwareVariable or backend-native).
        value: Value or expression to assign.
    """
    get_active_backend().assign(variable, value)


def save(variable: Any, stream: Any) -> None:
    """Save a variable value to a stream.

    Args:
        variable: Variable whose value to save.
        stream: Target stream handle.
    """
    get_active_backend().save(variable, stream)


# ──────────────────────────────────────────────────────────────────────────
# Control Flow
# ──────────────────────────────────────────────────────────────────────────

def for_loop(variable: Any, init: Any, condition: Any, update: Any):
    """Context manager for a for-loop on the hardware.

    Usage:
        with arbok.for_loop(var, 0, var < N, var + 1):
            ...

    Args:
        variable: Loop variable.
        init: Initial value.
        condition: Continue condition.
        update: Per-iteration update expression.
    """
    return get_active_backend().for_loop(variable, init, condition, update)


def while_loop(condition: Any):
    """Context manager for a while-loop on the hardware.

    Usage:
        with arbok.while_loop(condition):
            ...

    Args:
        condition: Boolean expression to evaluate each iteration.
    """
    return get_active_backend().while_loop(condition)


def if_block(condition: Any):
    """Context manager for an if-branch.

    Usage:
        with arbok.if_block(my_bool_var):
            ...

    Args:
        condition: Boolean condition.
    """
    return get_active_backend().if_block(condition)


def else_block():
    """Context manager for an else-branch. Must follow if_block.

    Usage:
        with arbok.if_block(cond):
            ...
        with arbok.else_block():
            ...
    """
    return get_active_backend().else_block()


def switch_block(variable: Any, unsafe: bool = False):
    """Context manager for a switch statement.

    Args:
        variable: Variable to switch on.
        unsafe: If True, skip bounds checking.
    """
    return get_active_backend().switch_block(variable, unsafe)


def case_block(value: int):
    """Context manager for a case within a switch.

    Args:
        value: Integer value to match.
    """
    return get_active_backend().case_block(value)


# ──────────────────────────────────────────────────────────────────────────
# Arithmetic / Type Helpers
# ──────────────────────────────────────────────────────────────────────────

def amp(amplitude: Any) -> Any:
    """Create an amplitude modifier for pulse operations.

    Used as: operation * arbok.amp(value)

    Args:
        amplitude: Amplitude value (variable or literal).

    Returns:
        Backend-specific amplitude representation.
    """
    return get_active_backend().amp(amplitude)


def cast_mul_fixed_by_int(fixed_val: Any, int_val: Any) -> Any:
    """Multiply a fixed-point value by an integer.

    Args:
        fixed_val: Fixed-point value.
        int_val: Integer value.

    Returns:
        Result expression.
    """
    return get_active_backend().cast_mul_fixed_by_int(fixed_val, int_val)


def cast_mul_int_by_fixed(int_val: Any, fixed_val: Any) -> Any:
    """Multiply an integer by a fixed-point value.

    Args:
        int_val: Integer value.
        fixed_val: Fixed-point value.

    Returns:
        Result expression.
    """
    return get_active_backend().cast_mul_int_by_fixed(int_val, fixed_val)


@property
def fixed_type() -> Any:
    """The fixed-point type for the active backend."""
    return get_active_backend().fixed_type


def get_fixed_type() -> Any:
    """Return the fixed-point type for the active backend."""
    return get_active_backend().fixed_type
