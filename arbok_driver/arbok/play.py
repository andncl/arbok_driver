from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
import logging
import math
import warnings

import numpy as np
from qm import qua

from arbok_driver.parameter_types import ParameterMap, Voltage, Time
from arbok_driver.sweep import build_wfc_op_name, _strip_measurement_prefix

if TYPE_CHECKING:
    from arbok_driver.measurement import Measurement
    from arbok_driver.sweep import Sweep

# Type alias for pulse generator: (amplitude_V, duration_ns) -> samples at 1GHz
PulseGenerator = Callable[[float, int], list[float]]

MAX_WFC_DURATION_NS = 128_000
"""Maximum pulse duration (ns) for waveform caching eligibility."""


def play(
        elements: list[str],
        target: ParameterMap[str, Voltage],
        operation: str | PulseGenerator,
        duration: Time | None = None,
        reference: ParameterMap[str, Voltage] | None = None,
        do_align: bool = True,
        no_play_tolerance: float = 1e-6,
        always_play: bool = False,
    ) -> None:
    """
    Plays a pulse on all specified elements. Two modes determined by `operation`:

    Legacy mode (str): plays a pre-existing operation from the OPX config,
    scaling amplitude and duration at runtime via classical logic.

    Generator mode (callable): auto-generates a discrete waveform and injects it
    into the OPX config (waveforms, pulses, element operations). Fixed amplitude
    and duration are baked into the waveform — no runtime classical logic. Only
    swept quantities use runtime scaling.

    Args:
        elements (list): elements on which pulse is applied
        target (ParameterMap): voltage point to move to
        operation (str | PulseGenerator): either an operation name from OPX
            config (legacy), or a callable(amplitude_V, duration_ns) -> list of
            samples at 1 GHz (1 sample per ns)
        duration (Time | None): duration parameter (clock cycles, 1cc = 4ns)
        reference (Optional[ParameterMap | None]): voltage point to come from.
            Amplitude is always target - reference.
        do_align (bool): whether to align elements before and after
        no_play_tolerance (float): amplitude below which pulse is skipped
        always_play (bool): force playing even at zero amplitude
    """
    _check_voltage_point_input(target, elements)
    if reference is not None:
        _check_voltage_point_input(reference, elements)

    if isinstance(operation, str):
        _ramp_legacy(
            elements, target, reference, operation, duration,
            do_align, no_play_tolerance, always_play)
    elif callable(operation):
        _ramp_generated(
            elements, target, reference, duration, operation,
            do_align, no_play_tolerance, always_play)
    else:
        raise TypeError(
            f"'operation' must be a str or callable, got {type(operation)}")


def _ramp_legacy(
        elements: list[str],
        target: ParameterMap[str, Voltage],
        reference: ParameterMap[str, Voltage] | None,
        operation: str,
        duration: Time | None,
        do_align: bool,
        no_play_tolerance: float,
        always_play: bool,
    ) -> None:
    """Plays a pre-existing operation from the OPX config with runtime scaling.

    Amplitude is computed as target - reference (or target if no reference) and
    applied via qua.amp(). Duration stretching uses the QUA variable directly.
    Both are classical logic executed on the FPGA at runtime.

    Args:
        elements: Element names on which the pulse is played.
        target: Voltage point to move to (per-element ParameterMap).
        reference: Voltage point to come from. If None, amplitude equals target.
        operation: Name of an existing operation in the element's OPX config.
        duration: Duration parameter in clock cycles (1cc = 4ns). If None, the
            pulse plays at its configured length.
        do_align: Whether to align elements before and after.
        no_play_tolerance: Amplitude threshold below which the pulse is skipped.
        always_play: Force playing even when amplitude is near zero.
    """
    if do_align:
        qua.align(*elements)
    for element in elements:
        if reference is not None:
            amplitude = target[element].qua - reference[element].qua
        else:
            amplitude = target[element].qua
        kwargs = {
            'pulse': operation * qua.amp(amplitude),
            'element': element
        }
        if duration is not None:
            kwargs['duration'] = duration.qua
        logging.debug(
            "Arbok_go: Moving %s from %s to %s by %s",
            element, reference, target, amplitude)
        if not isinstance(amplitude, (float, int)) or always_play:
            qua.play(**kwargs)
        elif math.isclose(amplitude, 0, abs_tol=no_play_tolerance):
            logging.debug(
                "Arbok_go: Omitting %s since amplitude %s is small (th = %s)",
                element, amplitude, no_play_tolerance)
        else:
            qua.play(**kwargs)
    if do_align:
        qua.align(*elements)


def _ramp_generated(
        elements: list[str],
        target: ParameterMap[str, Voltage],
        reference: ParameterMap[str, Voltage] | None,
        duration: Time | None,
        generator: PulseGenerator,
        do_align: bool,
        no_play_tolerance: float,
        always_play: bool,
    ) -> None:
    """Generates discrete waveforms and injects them into the OPX config.

    Two modes depending on whether waveform caching is active:

    **Cached mode** (wfc registered on sweep): Pre-generates one waveform per
    amplitude value and injects them as a ``type: array`` config entry. The
    sweep handles ``load_waveform``; this function only emits ``qua.play``.

    **Scaled mode** (default/fallback): Generates a single waveform and uses
    ``qua.amp()`` for runtime amplitude scaling.

    Args:
        elements: Element names on which the pulse is played.
        target: Voltage point to move to (per-element ParameterMap).
        reference: Voltage point to come from. If None, amplitude equals target.
        duration: Duration parameter in clock cycles (1cc = 4ns). Required.
        generator: Callable(amplitude_V, duration_ns) -> samples at 1 GHz.
        do_align: Whether to align elements before and after.
        no_play_tolerance: Amplitude threshold below which the pulse is skipped.
        always_play: Force playing even when amplitude is near zero.

    Raises:
        ValueError: If duration is None or if wfc is registered with
            incompatible duration.
    """
    if duration is None:
        raise ValueError(
            "Generator mode requires a 'duration' parameter")

    first_param = next(iter(target.values()))
    opx_config = first_param.instrument.measurement._opx_config

    dur_is_swept = duration.qua_sweeped
    if dur_is_swept:
        dur_ns = int(min(duration.get()) * 1e9)
    else:
        dur_ns = int(duration.get() * 4)

    if do_align:
        qua.align(*elements)

    for element in elements:
        amp_is_swept = target[element].qua_sweeped or (
            reference is not None and reference[element].qua_sweeped)

        wfc_active = getattr(target[element], '_wfc_active', False)

        if wfc_active and amp_is_swept:
            _validate_wfc_eligibility(dur_ns, dur_is_swept)
            _ramp_cached_element(
                opx_config, element, target, reference,
                generator, dur_ns)
        elif amp_is_swept:
            _ramp_scaled_element(
                opx_config, element, target, reference,
                generator, dur_ns, dur_is_swept, duration)
        else:
            _ramp_static_element(
                opx_config, element, target, reference,
                generator, dur_ns, dur_is_swept, duration,
                no_play_tolerance, always_play)

    if do_align:
        qua.align(*elements)


def _validate_wfc_eligibility(dur_ns: int, dur_is_swept: bool) -> None:
    """Raises if waveform caching was registered but constraints are violated."""
    if dur_is_swept:
        raise ValueError(
            "Waveform caching is incompatible with swept duration. "
            "Remove the register_waveform_load call or use a fixed duration.")
    if dur_ns > MAX_WFC_DURATION_NS:
        raise ValueError(
            f"Waveform caching requires duration <= {MAX_WFC_DURATION_NS} ns, "
            f"got {dur_ns} ns.")


def _ramp_cached_element(
        opx_config: dict,
        element: str,
        target: ParameterMap[str, Voltage],
        reference: ParameterMap[str, Voltage] | None,
        generator: PulseGenerator,
        dur_ns: int,
    ) -> None:
    """Injects array-type waveform config and emits a plain ``qua.play``.

    One waveform per amplitude value is pre-computed and stored in
    ``samples_array``. The sweep handles ``load_waveform`` before play.
    """
    op_name = build_wfc_op_name(target[element], reference, element)
    if op_name not in opx_config['elements'][element].get('operations', {}):
        amplitudes = _compute_amplitude_array(
            target[element], reference, element)
        samples_array = [
            generator(float(amp), dur_ns) for amp in amplitudes]
        _inject_wfc_config(opx_config, element, op_name, samples_array, dur_ns)

    qua.play(op_name, element)


def _ramp_scaled_element(
        opx_config: dict,
        element: str,
        target: ParameterMap[str, Voltage],
        reference: ParameterMap[str, Voltage] | None,
        generator: PulseGenerator,
        dur_ns: int,
        dur_is_swept: bool,
        duration: Time,
    ) -> None:
    """Fallback: single waveform with runtime ``qua.amp()`` scaling."""
    op_name = _build_pulse_name(target[element], reference, element, dur_ns)
    if op_name not in opx_config['elements'][element].get('operations', {}):
        samples = generator(1.0, dur_ns)
        _inject_config(opx_config, element, op_name, samples, dur_ns)

    if reference is not None:
        amplitude = target[element].qua - reference[element].qua
    else:
        amplitude = target[element].qua
    pulse_ref = op_name * qua.amp(amplitude)

    kwargs = {'pulse': pulse_ref, 'element': element}
    if dur_is_swept:
        kwargs['duration'] = duration.qua
    qua.play(**kwargs)


def _ramp_static_element(
        opx_config: dict,
        element: str,
        target: ParameterMap[str, Voltage],
        reference: ParameterMap[str, Voltage] | None,
        generator: PulseGenerator,
        dur_ns: int,
        dur_is_swept: bool,
        duration: Time,
        no_play_tolerance: float,
        always_play: bool,
    ) -> None:
    """Amplitude is fixed — bake it directly into the waveform samples."""
    if reference is not None:
        static_amp = float(
            target[element].get_raw() - reference[element].get_raw())
    else:
        static_amp = float(target[element].get_raw())

    if math.isclose(static_amp, 0, abs_tol=no_play_tolerance) and not always_play:
        logging.debug(
            "Arbok_go: Omitting %s since amplitude %s is small (th = %s)",
            element, static_amp, no_play_tolerance)
        return

    op_name = _build_pulse_name(target[element], reference, element, dur_ns)
    if op_name not in opx_config['elements'][element].get('operations', {}):
        samples = generator(static_amp, dur_ns)
        _inject_config(opx_config, element, op_name, samples, dur_ns)

    kwargs = {'pulse': op_name, 'element': element}
    if dur_is_swept:
        kwargs['duration'] = duration.qua
    qua.play(**kwargs)


def _build_pulse_name(
        target_param: Voltage,
        reference: ParameterMap[str, Voltage] | None,
        element: str,
        dur_ns: int,
    ) -> str:
    """Builds a unique operation name: <target_path>_FROM_<ref_path>_<dur>ns"""
    name = _strip_measurement_prefix(target_param.sequence_path)
    if reference is not None:
        name += f"_FROM_{_strip_measurement_prefix(reference[element].sequence_path)}"
    name += f"_{dur_ns}ns"
    return name


def _inject_config(
        opx_config: dict,
        element: str,
        op_name: str,
        samples: list[float],
        dur_ns: int,
    ) -> None:
    """Injects waveform, pulse, and operation entries into the OPX config."""
    wf_name = f"{op_name}_wf"
    pulse_name = f"{op_name}_pulse"

    opx_config.setdefault('waveforms', {})[wf_name] = {
        'type': 'arbitrary',
        'samples': list(samples),
    }
    opx_config.setdefault('pulses', {})[pulse_name] = {
        'operation': 'control',
        'length': dur_ns,
        'waveforms': {'single': wf_name},
    }
    opx_config['elements'][element].setdefault('operations', {})[op_name] = pulse_name


def _inject_wfc_config(
        opx_config: dict,
        element: str,
        op_name: str,
        samples_array: list[list[float]],
        dur_ns: int,
    ) -> None:
    """Injects a waveform-cached (type: array) entry into the OPX config.

    Args:
        opx_config: The full OPX configuration dict.
        element: Element name to attach the operation to.
        op_name: Operation name (shared with sweep's load_waveform call).
        samples_array: List of waveform sample lists (one per sweep index).
        dur_ns: Pulse duration in nanoseconds (all waveforms same length).
    """
    wf_name = f"{op_name}_wf"
    pulse_name = f"{op_name}_pulse"

    opx_config.setdefault('waveforms', {})[wf_name] = {
        'type': 'array',
        'samples_array': [list(s) for s in samples_array],
    }
    opx_config.setdefault('pulses', {})[pulse_name] = {
        'operation': 'control',
        'length': dur_ns,
        'waveforms': {'single': wf_name},
    }
    opx_config['elements'][element].setdefault(
        'operations', {})[op_name] = pulse_name


def _compute_amplitude_array(
        target_param: Voltage,
        reference: ParameterMap[str, Voltage] | None,
        element: str,
    ) -> np.ndarray:
    """Computes the amplitude array for all sweep indices.

    Finds the sweep containing the target/reference parameter and extracts
    the raw voltage values for each index.

    Args:
        target_param: The swept target voltage parameter.
        reference: Optional reference ParameterMap.
        element: Element key for reference lookup.

    Returns:
        Array of amplitude values (target - reference) per sweep index.
    """
    measurement = target_param.instrument.measurement
    sweep = _find_sweep_for_param(target_param, reference, element, measurement)

    target_array = np.array(sweep.config[target_param]) * target_param.scale
    if reference is not None and reference[element] in sweep.parameters:
        ref_array = (
            np.array(sweep.config[reference[element]])
            * reference[element].scale)
        return target_array - ref_array
    elif reference is not None:
        ref_value = reference[element].get_raw()
        return target_array - ref_value
    return target_array


def _find_sweep_for_param(
        target_param: Voltage,
        reference: ParameterMap[str, Voltage] | None,
        element: str,
        measurement: Measurement,
    ) -> Sweep:
    """Finds the sweep that contains the target or reference parameter."""
    for sweep in measurement.sweeps:
        if target_param in sweep.parameters:
            return sweep
        if reference is not None and reference[element] in sweep.parameters:
            return sweep
    raise ValueError(
        f"Parameter {target_param.full_name} is not swept by any axis")


def _check_voltage_point_input(
        parameter_maps: ParameterMap[str, Voltage],
        elements: list[str],
    ) -> None:
    """Validates that parameter_maps is a ParameterMap of Voltage params
    covering all requested elements."""
    if parameter_maps is None:
        print('Nothing to return!')
        return
    if not isinstance(parameter_maps, ParameterMap):
        raise TypeError(
            f"Must be of type ParameterMap. Is {type(parameter_maps)}")
    if not all([isinstance(p, Voltage) for _, p in parameter_maps.items()]):
        raise TypeError(
            "Not all parameters in the given ParameterMap are of type Voltage"
        )
    if not set(elements).issubset(parameter_maps):
        missing = set(elements) - parameter_maps.keys()
        raise ValueError(
            f"Missing elements in arbok.play parameter maps: {missing}")


def ramp(
        elements: list[str],
        target: ParameterMap[str, Voltage],
        operation: str | PulseGenerator,
        duration: Time | None = None,
        reference: ParameterMap[str, Voltage] | None = None,
        do_align: bool = True,
        no_play_tolerance: float = 1e-6,
        always_ramp: bool = False,
    ) -> None:
    """Deprecated alias for :func:`play`. Use ``arbok.play()`` instead."""
    warnings.warn(
        "arbok.ramp() is deprecated and will be removed in a future version. "
        "Use arbok.play() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    play(
        elements=elements,
        target=target,
        operation=operation,
        duration=duration,
        reference=reference,
        do_align=do_align,
        no_play_tolerance=no_play_tolerance,
        always_play=always_ramp,
    )
