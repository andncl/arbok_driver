from typing import Optional, Callable
import logging
import math

from qm import qua

from arbok_driver.parameter_types import ParameterMap, Voltage, Time

# Type alias for pulse generator: (amplitude_V, duration_ns) -> samples at 1GHz
PulseGenerator = Callable[[float, int], list[float]]


def ramp(
        elements: list,
        target: ParameterMap,
        operation: str | PulseGenerator,
        duration: Time | None = None,
        reference: Optional[ParameterMap | None] = None,
        do_align: bool = True,
        no_play_tolerance: float = 1e-6,
        always_ramp: bool = False,
    ):
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
        always_ramp (bool): force playing even at zero amplitude
    """
    _check_voltage_point_input(target, elements)
    if reference is not None:
        _check_voltage_point_input(reference, elements)

    if isinstance(operation, str):
        _ramp_legacy(
            elements, target, reference, operation, duration,
            do_align, no_play_tolerance, always_ramp)
    elif callable(operation):
        _ramp_generated(
            elements, target, reference, duration, operation,
            do_align, no_play_tolerance, always_ramp)
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
        always_ramp: bool,
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
        do_align: Whether to align elements before and after the ramp.
        no_play_tolerance: Amplitude threshold below which the pulse is skipped.
        always_ramp: Force playing even when amplitude is near zero.
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
        if not isinstance(amplitude, (float, int)) or always_ramp:
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
        always_ramp: bool,
    ) -> None:
    """Generates discrete waveforms and injects them into the OPX config.

    Fixed amplitude and duration are baked directly into the waveform samples,
    eliminating runtime classical logic. Only swept quantities fall back to
    runtime scaling (qua.amp for amplitude, duration kwarg for time).

    The generator is called with unit amplitude (1.0) when the voltage parameters
    are swept, or with the actual voltage difference when they are fixed. For
    swept duration, the shortest value in the sweep array is used as the base
    waveform length.

    Args:
        elements: Element names on which the pulse is played.
        target: Voltage point to move to (per-element ParameterMap).
        reference: Voltage point to come from. If None, amplitude equals target.
        duration: Duration parameter in clock cycles (1cc = 4ns). Required in
            generator mode.
        generator: Callable(amplitude_V, duration_ns) returning a list of
            waveform samples at 1 GHz (1 sample per ns).
        do_align: Whether to align elements before and after the ramp.
        no_play_tolerance: Amplitude threshold below which the pulse is skipped.
        always_ramp: Force playing even when amplitude is near zero.

    Raises:
        ValueError: If duration is None.
    """
    if duration is None:
        raise ValueError(
            "Generator mode requires a 'duration' parameter")

    # Resolve opx_config via parameter -> instrument -> measurement chain
    first_param = next(iter(target.values()))
    opx_config = first_param.instrument.measurement._opx_config

    dur_is_swept = duration.qua_sweeped
    if dur_is_swept:
        # After set_sweeps, get() returns real units (seconds for Time)
        dur_ns = int(min(duration.get()) * 1e9)
    else:
        # Before sweep, get() returns raw clock cycles (1cc = 4ns)
        dur_ns = int(duration.get() * 4)

    if do_align:
        qua.align(*elements)

    for element in elements:
        amp_is_swept = target[element].qua_sweeped or (
            reference is not None and reference[element].qua_sweeped)

        # Compute static amplitude for non-swept case
        if not amp_is_swept:
            if reference is not None:
                static_amp = float(target[element].get() - reference[element].get())
            else:
                static_amp = float(target[element].get())
            if math.isclose(static_amp, 0, abs_tol=no_play_tolerance) and not always_ramp:
                logging.debug(
                    "Arbok_go: Omitting %s since amplitude %s is small (th = %s)",
                    element, static_amp, no_play_tolerance)
                continue
            gen_amp = static_amp
        else:
            gen_amp = 1.0

        # Build unique config entry name encoding parameter paths + duration
        op_name = _build_pulse_name(target[element], reference, element, dur_ns)

        # Inject config entries (idempotent: skip if already present)
        if op_name not in opx_config['elements'][element].get('operations', {}):
            samples = generator(gen_amp, dur_ns)
            _inject_config(opx_config, element, op_name, samples, dur_ns)

        # Emit QUA play — only add runtime scaling for swept quantities
        if amp_is_swept:
            if reference is not None:
                amplitude = target[element].qua - reference[element].qua
            else:
                amplitude = target[element].qua
            pulse_ref = op_name * qua.amp(amplitude)
        else:
            pulse_ref = op_name

        kwargs = {'pulse': pulse_ref, 'element': element}
        if dur_is_swept:
            kwargs['duration'] = duration.qua
        qua.play(**kwargs)

    if do_align:
        qua.align(*elements)


def _build_pulse_name(
        target_param: Voltage,
        reference: ParameterMap[str, Voltage] | None,
        element: str,
        dur_ns: int,
    ) -> str:
    """Builds a unique operation name: <target_path>_from_<ref_path>_<dur>ns"""
    name = target_param.sequence_path
    if reference is not None:
        name += f"_from_{reference[element].sequence_path}"
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


def _check_voltage_point_input(
        parameter_maps: ParameterMap[str, Voltage],
        elements: list[str]
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
            f"Missing elements in arbok.ramp parameter maps: {missing}")
