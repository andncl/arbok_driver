"""Module containing functions for path finding objects within the Arbok driver."""
from __future__ import annotations
from typing import TYPE_CHECKING
from functools import reduce


if TYPE_CHECKING:
    from .abstract_readout import AbstractReadout
    from .gettable_parameter import GettableParameter
    from .measurement import Measurement
    from .read_sequence import ReadSequence
    from .signal import Signal
    from .sub_sequence import SubSequence

def get_gettable_from_read_sequence(
        read_sequence: ReadSequence,
        signal_name: str,
        gettable_name: str,
        ) -> GettableParameter:
    """
    Helper method to get a gettable from this readout. This is used

    Args:
        read_sequence (ReadSequence): The read sequence to get the gettable from
        signal_name (str): Name of the signal
        gettable_name (str): Name of the gettable
    
    Raises:
        KeyError: If the signal or gettable is not found in the read sequence
        KeyError: If the GettableParameter is not found in the signal
        ValueError: If the found object is not a child class of GettableParameter
    """
    from .gettable_parameter import GettableParameter
    if signal_name not in read_sequence.signals:
        raise KeyError(
            f"Signal {signal_name} not found in read sequence"
            f" '{read_sequence.name}'. Available signals: "
            f"{read_sequence.signals.keys()}"
        )
    signal: Signal = read_sequence.signals[signal_name]
    if gettable_name not in signal.gettables:
        raise KeyError(
            f"Gettable {gettable_name} not found in signal {signal.name}"
            f" of read sequence '{read_sequence.name}'. "
            f"Available gettables: {signal.gettables.keys()}"
        )
    gettable: GettableParameter = signal.gettables[gettable_name]
    if not isinstance(gettable, GettableParameter):
        raise ValueError(
            f"The given path {signal_name}.{gettable_name} yields a ",
            f"{type(gettable)}-type, not a child class of gettable"
        )
    return gettable

def get_sequence_from_measurement_path(
        measurement: Measurement,
        path: str | list[str]
        ) -> SubSequence:
    """
    Get a sequence from a measurement by resolving the given attribute path.

    Args:
        measurement (Measurement): The measurement to get the read sequence from
        path (str): The attribute path to the read sequence relative to the measurement

    Returns:
        SubSequence: The sub-sequence found at the given path
    """
    if isinstance(path, str):
        path: list[str] = path.split('.')
    sequence = reduce(getattr, path, measurement)
    from .sub_sequence import SubSequence
    if not isinstance(sequence, SubSequence):
        raise ValueError(
            f"The given path {path} does not resolve to a SubSequence"
            f" on measurement {measurement.name}. Got {type(sequence)} instead."
        )
    return sequence

def get_read_sequence_from_measurement_path(
        measurement: Measurement,
        path: str | list[str]
) -> ReadSequence:
    """
    Get a read sequence from a measurement by resolving the given attribute path.

    Args:
        measurement (Measurement): The measurement to get the read sequence from
        path (str): The attribute path to the read sequence relative to the measurement

    Returns:
        ReadSequence: The read sequence found at the given path
    """
    if isinstance(path, str):
        path: list[str] = path.split('.')
    sub_sequence = get_sequence_from_measurement_path(measurement, path)
    from .read_sequence import ReadSequence
    if not isinstance(sub_sequence, ReadSequence):
        raise ValueError(
            f"The given path {path} does not resolve to a ReadSequence on "
            f"measurement {measurement.name}. Got {type(sub_sequence)} instead."
        )
    return sub_sequence

def get_read_sequence_from_readout_path(
        readout: AbstractReadout,
        path: str | list[str]
) -> ReadSequence:
    """
    Get a read sequence from a readout by resolving the given attribute path.

    Args:
        readout (AbstractReadout): The readout to get the read sequence from
        path (str): The attribute path to the read sequence relative to the readout

    Returns:
        ReadSequence: The read sequence found at the given path
    """
    measurement = readout.read_sequence.measurement
    return get_read_sequence_from_measurement_path(measurement, path)

def get_params_with_prefix(sub_sequence: SubSequence, prefix: str) -> dict:
    """
    Finds all parameters in a sub-sequence that have the given prefix in their name.
    TODO: This is not a very clean solution, make more readable

    Args:
        prefix (str): Prefix of the element parameters
    
    Returns:
        dict: Dictionary with suffixes as keys and parameters as values
    """
    all_params = sub_sequence.parameters
    full_prefix = f"{sub_sequence.name}__{prefix}"
    param_names = [x for x in all_params if full_prefix in x]
    suffix_list = [x.split(full_prefix)[-1].split('_')[-1] for x in param_names]
    return {e: all_params[p] for e, p in zip(suffix_list, param_names)}

def get_gettable_from_measurement_path(
        measurement: Measurement,
        path: str | list[str]) -> GettableParameter:
    """
    Get a gettable from a measurement by resolving the given attribute path.

    Args:
        measurement (Measurement): The measurement to get the gettable from
        path (str): The attribute path to the gettable relative to the measurement
    
    Returns:
        GettableParameter: The gettable found at the given path
    """
    if isinstance(path, str):
        path: list[str] = path.split('.')

    if len(path) <= 2:
        raise ValueError(
            f"The given path {path} is too short to resolve a gettable. "
            "Please provide a path with the format "
            "'sub_sequence_path.signal.gettable_name'."
        )
    signal_name, gettable_name = path[-2:]
    sub_sequence_path = path[:-2]
    read_sequence = get_read_sequence_from_measurement_path(
        measurement, sub_sequence_path)
    return get_gettable_from_read_sequence(
        read_sequence, signal_name, gettable_name
    )
