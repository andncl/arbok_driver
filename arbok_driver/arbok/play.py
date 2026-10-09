from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING
import logging
import math
import warnings

import numpy as np

from arbok_driver.backend import (
    IQ_CHANNELS, SINGLE_CHANNEL, WaveformSamples, as_channel_map)
from arbok_driver.parameter_types import ParameterMap, Voltage, Time
from arbok_driver.sweep import (
    MAX_WFC_WAVEFORMS, build_wfc_op_name, _strip_measurement_prefix)
from .context import get_active_backend

if TYPE_CHECKING:
    from arbok_driver.measurement import Measurement
    from arbok_driver.sweep import Sweep

# Type alias for pulse generator: (amplitude_V, duration_ns) -> samples at 1GHz
PulseGenerator = Callable[[float, int], WaveformSamples]

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
            config (legacy), or a callable(amplitude_V, duration_ns) -> samples
            at 1 GHz (1 sample per ns). Return a list of samples for a DC
            element, or ``{'I': [...], 'Q': [...]}`` (equivalently a complex
            ``I + 1j*Q``) for an up-converted (mixInputs / MWInput) one. Which
            kind of pulse is generated (and cached) follows from that return
            value, nothing has to be declared.
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


def load_waveform_table(
        elements: list[str],
        operation: str,
        waveforms: dict[str, list],
        index,
        hardware_config: dict,
    ) -> None:
    """Selects one pre-computed waveform out of a cached table per element.

    All waveforms of the table are uploaded with the program as a
    ``type: array`` waveform, and the one to play is selected at runtime by
    ``index``. Selecting costs FPGA time, playing the selected waveform does
    not, so this belongs into a hook that runs *before* the pulse - typically
    ``fpga_before_sequence`` - while :func:`play_waveform_table` goes into
    ``fpga_sequence``. The pulse itself is then free of any classical logic,
    in contrast to deciding what to play with real time branching.

    Unlike the waveform caching in :func:`play`, the table is not derived from
    a swept voltage point: the caller hands over the finished samples, so any
    pulse train can be pre-computed (e.g. a whole gate sequence).

    Args:
        elements (list): Elements on which a waveform is played.
        operation (str): Operation name to register on every element. It is
            also the name ``load_waveform`` selects the waveform with.
        waveforms (dict): Per element list of waveforms (samples at 1 GS/s).
            A waveform is a list of samples for a DC element, or
            ``{'I': [...], 'Q': [...]}`` for an up-converted one -
            equivalently a complex ``I + 1j*Q``, which is what
            ``simulate_pulse_waveforms`` returns. Every waveform of every
            element must have the same length, and all waveforms of one
            element must drive the same channels.
        index: Waveform to play, as an int or a hardware variable. Sweeping the
            parameter behind it measures one cached waveform per iteration.
        hardware_config (dict): Hardware config to inject the waveforms into.
            This is the config used to compile the program, so pass
            ``self.measurement.hardware_config``.

    Raises:
        ValueError: If the table does not cover all elements, if the waveforms
            do not all have the same length, or if there are more waveforms
            than the hardware can cache.
    """
    dur_ns, channel_arrays = _check_waveform_table(elements, waveforms)
    backend = get_active_backend()

    from arbok_driver.backends.sim_backend import SimBackend
    is_sim = isinstance(backend, SimBackend)
    for element in elements:
        if is_sim:
            ### Nothing is uploaded in a simulation, so the samples are handed
            ### to the backend directly to let it resolve the selection
            backend.register_waveform_array(
                element, operation, waveforms[element])
        elif operation not in hardware_config['elements'][element].get(
                'operations', {}):
            _inject_waveform_table_config(
                hardware_config, element, operation,
                channel_arrays[element], dur_ns)
        backend.load_waveform(operation, index, element)


def play_waveform_table(
        elements: list[str],
        operation: str,
        do_align: bool = True,
    ) -> None:
    """Plays the waveform loaded for an operation on every element.

    Requires :func:`load_waveform_table` to have run for the same elements and
    operation, which is what registers the operation and selects the waveform.

    Args:
        elements (list): Elements to play the loaded waveform on.
        operation (str): Operation name the waveform table is registered under.
        do_align (bool): Whether to align the elements before and after.
    """
    backend = get_active_backend()
    if do_align:
        backend.align(elements)
    for element in elements:
        backend.play(element, operation)
    if do_align:
        backend.align(elements)


def _check_waveform_table(
        elements: list[str],
        waveforms: dict[str, list],
    ) -> tuple[int, dict[str, dict[str, list[list[float]]]]]:
    """Validates a waveform table and normalizes it per element and channel.

    The normalized table is returned rather than re-derived at injection
    time: a pre-computed gate sequence can hold a thousand waveforms of
    thousands of samples, and converting those twice is wasted work.

    Args:
        elements: Elements the table has to cover.
        waveforms: Per element list of waveforms.

    Returns:
        tuple: Length of every waveform in the table in ns, and the table as
        element to channel to that channel's trace per index.

    Raises:
        ValueError: If an element is missing, if the table is empty, if the
            waveform lengths differ or if the table exceeds the cache size.
    """
    missing = [element for element in elements if element not in waveforms]
    if missing:
        raise ValueError(
            f"Missing elements in the waveform table: {missing}")

    lengths = set()
    counts = set()
    channel_arrays = {}
    for element in elements:
        element_waveforms = waveforms[element]
        counts.add(len(element_waveforms))
        if not element_waveforms:
            continue
        ### Normalizing also validates the channel keys and rejects
        ### quadratures of unequal length within one waveform
        channel_arrays[element] = _as_channel_arrays(element_waveforms)
        for traces in channel_arrays[element].values():
            lengths.update(len(trace) for trace in traces)
    if not counts or counts == {0}:
        raise ValueError("The waveform table does not hold any waveform")
    if len(counts) != 1:
        raise ValueError(
            f"All elements must have the same number of waveforms, got "
            f"{sorted(counts)}")
    if len(lengths) != 1:
        raise ValueError(
            f"All waveforms of a table must have the same length, got "
            f"{sorted(lengths)} samples. Pad the shorter ones with zeros.")
    nr_waveforms = counts.pop()
    if nr_waveforms > MAX_WFC_WAVEFORMS:
        raise ValueError(
            f"A waveform table holds at most {MAX_WFC_WAVEFORMS} waveforms, "
            f"got {nr_waveforms}.")
    return lengths.pop(), channel_arrays


def _inject_waveform_table_config(
        hardware_config: dict,
        element: str,
        op_name: str,
        channel_arrays: dict[str, list[list[float]]],
        dur_ns: int,
    ) -> None:
    """Injects a ``type: array`` waveform table for a single element.

    In contrast to :func:`_inject_wfc_config` the operation name is shared by
    all elements, so the waveform and pulse names carry the element name.

    Args:
        hardware_config: The full hardware (OPX) configuration dict.
        element: Element name to attach the operation to.
        op_name: Operation name (shared with the ``load_waveform`` call).
        channel_arrays: Normalized waveforms of this element, as channel to
            that channel's trace per index.
        dur_ns: Waveform length in nanoseconds (all waveforms are equal).
    """
    _check_element_channels(hardware_config, element, channel_arrays)
    pulse_name = f"{op_name}_{element}_pulse"

    waveforms = hardware_config.setdefault('waveforms', {})
    pulse_waveforms = {}
    for channel, traces in channel_arrays.items():
        wf_name = _waveform_name(f"{op_name}_{element}", channel)
        waveforms[wf_name] = {'type': 'array', 'samples_array': traces}
        pulse_waveforms[channel] = wf_name

    hardware_config.setdefault('pulses', {})[pulse_name] = {
        'operation': 'control',
        'length': dur_ns,
        'waveforms': pulse_waveforms,
    }
    hardware_config['elements'][element].setdefault(
        'operations', {})[op_name] = pulse_name


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
    backend = get_active_backend()
    if do_align:
        backend.align(elements)
    for element in elements:
        if reference is not None:
            amplitude = target[element].qua - reference[element].qua
        else:
            amplitude = target[element].qua
        dur = duration.qua if duration is not None else None
        logging.debug(
            "Arbok_go: Moving %s from %s to %s by %s",
            element, reference, target, amplitude)
        if not isinstance(amplitude, (float, int)) or always_play:
            backend.play(element, operation, amplitude, dur)
        elif math.isclose(amplitude, 0, abs_tol=no_play_tolerance):
            logging.debug(
                "Arbok_go: Omitting %s since amplitude %s is small (th = %s)",
                element, amplitude, no_play_tolerance)
        else:
            backend.play(element, operation, amplitude, dur)
    if do_align:
        backend.align(elements)


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

    When the active backend is a SimBackend, the generator callable is passed
    directly to backend.play() — no config injection is performed.

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

    backend = get_active_backend()

    from arbok_driver.backends.sim_backend import SimBackend
    if isinstance(backend, SimBackend):
        _ramp_generated_sim(
            elements, target, reference, duration, generator,
            do_align, no_play_tolerance, always_play, backend)
        return

    first_param = next(iter(target.values()))
    opx_config = first_param.instrument.measurement._hardware_config

    dur_is_swept = duration.qua_sweeped
    if dur_is_swept:
        dur_ns = int(min(duration.get()) * 1e9)
    else:
        dur_ns = int(duration.get() * 4)

    if do_align:
        backend.align(elements)

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
        backend.align(elements)


def _ramp_generated_sim(
        elements: list[str],
        target: ParameterMap[str, Voltage],
        reference: ParameterMap[str, Voltage] | None,
        duration: Time,
        generator: PulseGenerator,
        do_align: bool,
        no_play_tolerance: float,
        always_play: bool,
        backend,
    ) -> None:
    """Simulation path: passes the generator callable directly to SimBackend."""
    dur_ns = int(duration.get() * 4)

    if do_align:
        backend.align(elements)

    for element in elements:
        if reference is not None:
            amplitude = float(
                target[element].get_raw() - reference[element].get_raw())
        else:
            amplitude = float(target[element].get_raw())

        if math.isclose(amplitude, 0, abs_tol=no_play_tolerance) and not always_play:
            continue

        backend.play(element, generator, amplitude, dur_ns // 4)

    if do_align:
        backend.align(elements)


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
    """Injects array-type waveform config and emits a plain play.

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

    get_active_backend().play(element, op_name)


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
    """Fallback: single waveform with runtime amplitude scaling."""
    op_name = _build_pulse_name(target[element], reference, element, dur_ns)
    if op_name not in opx_config['elements'][element].get('operations', {}):
        samples = generator(1.0, dur_ns)
        _inject_config(opx_config, element, op_name, samples, dur_ns)

    if reference is not None:
        amplitude = target[element].qua - reference[element].qua
    else:
        amplitude = target[element].qua

    dur = duration.qua if dur_is_swept else None
    get_active_backend().play(element, op_name, amplitude, dur)


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

    dur = duration.qua if dur_is_swept else None
    get_active_backend().play(element, op_name, None, dur)


def _build_pulse_name(
        target_param: Voltage,
        reference: ParameterMap[str, Voltage] | None,
        element: str,
        dur_ns: int,
    ) -> str:
    """Builds a unique operation name: <target_path>_FROM_<ref_path>_<dur>ns"""
    name = _strip_measurement_prefix(target_param.register_name)
    if reference is not None:
        name += f"_FROM_{_strip_measurement_prefix(reference[element].register_name)}"
    name += f"_{dur_ns}ns"
    return name


def _waveform_name(base: str, channel: str) -> str:
    """Builds the config key of one channel's waveform.

    Single input waveforms keep their historic unsuffixed name, so configs
    generated before I/Q support are unchanged.

    Args:
        base: Name shared by all channels of the pulse.
        channel: Channel the waveform drives (``single``, ``I`` or ``Q``).

    Returns:
        str: Key of the waveform in the ``waveforms`` section.
    """
    if channel == SINGLE_CHANNEL:
        return f"{base}_wf"
    return f"{base}_{channel}_wf"


def _check_element_channels(
        hardware_config: dict,
        element: str,
        channels: Iterable[str],
    ) -> None:
    """Checks the generated channels against the element's input declaration.

    Playing I/Q samples on a single input element (or the other way round)
    is rejected by the hardware with a hard to read compilation error, so it
    is caught here while the offending generator is still in sight. Elements
    that declare no input at all are left alone.

    Args:
        hardware_config: The full hardware (OPX) configuration dict.
        element: Element the pulse is played on.
        channels: Channels the pulse drives, or any mapping keyed by them.

    Raises:
        ValueError: If the element's input kind cannot play these channels.
    """
    element_config = hardware_config.get('elements', {}).get(element, {})
    is_iq = set(channels) == set(IQ_CHANNELS)
    has_single = 'singleInput' in element_config
    has_iq = 'mixInputs' in element_config or 'MWInput' in element_config

    if is_iq and has_single and not has_iq:
        raise ValueError(
            f"The waveform generator returned {set(IQ_CHANNELS)} samples, but "
            f"element '{element}' is a singleInput element. Return a plain "
            f"list of samples for DC elements.")
    if not is_iq and has_iq and not has_single:
        raise ValueError(
            f"The waveform generator returned a single trace, but element "
            f"'{element}' is driven by mixInputs/MWInput. Return "
            f"{{'I': [...], 'Q': [...]}} for up-converted elements.")


def _inject_config(
        opx_config: dict,
        element: str,
        op_name: str,
        samples: WaveformSamples,
        dur_ns: int,
    ) -> None:
    """Injects waveform, pulse, and operation entries into the OPX config.

    Args:
        opx_config: The full OPX configuration dict.
        element: Element name to attach the operation to.
        op_name: Operation name to register on the element.
        samples: Generator output - one trace, or one trace per quadrature.
        dur_ns: Pulse duration in nanoseconds.
    """
    channels = as_channel_map(samples)
    _check_element_channels(opx_config, element, channels)
    pulse_name = f"{op_name}_pulse"

    waveforms = opx_config.setdefault('waveforms', {})
    pulse_waveforms = {}
    for channel, trace in channels.items():
        wf_name = _waveform_name(op_name, channel)
        waveforms[wf_name] = {'type': 'arbitrary', 'samples': trace}
        pulse_waveforms[channel] = wf_name

    opx_config.setdefault('pulses', {})[pulse_name] = {
        'operation': 'control',
        'length': dur_ns,
        'waveforms': pulse_waveforms,
    }
    opx_config['elements'][element].setdefault('operations', {})[op_name] = pulse_name


def _inject_wfc_config(
        opx_config: dict,
        element: str,
        op_name: str,
        samples_array: list[WaveformSamples],
        dur_ns: int,
    ) -> None:
    """Injects a waveform-cached (type: array) entry into the OPX config.

    For an up-converted element both quadratures become their own ``array``
    waveform. ``load_waveform`` selects by pulse, so one index still picks a
    consistent I/Q pair.

    Args:
        opx_config: The full OPX configuration dict.
        element: Element name to attach the operation to.
        op_name: Operation name (shared with sweep's load_waveform call).
        samples_array: Generator output per sweep index - each entry one trace,
            or one trace per quadrature.
        dur_ns: Pulse duration in nanoseconds (all waveforms same length).
    """
    channel_arrays = _as_channel_arrays(samples_array)
    _check_element_channels(opx_config, element, channel_arrays)
    pulse_name = f"{op_name}_pulse"

    waveforms = opx_config.setdefault('waveforms', {})
    pulse_waveforms = {}
    for channel, traces in channel_arrays.items():
        wf_name = _waveform_name(op_name, channel)
        waveforms[wf_name] = {'type': 'array', 'samples_array': traces}
        pulse_waveforms[channel] = wf_name

    opx_config.setdefault('pulses', {})[pulse_name] = {
        'operation': 'control',
        'length': dur_ns,
        'waveforms': pulse_waveforms,
    }
    opx_config['elements'][element].setdefault(
        'operations', {})[op_name] = pulse_name


def _as_channel_arrays(
        samples_array: list[WaveformSamples],
    ) -> dict[str, list[list[float]]]:
    """Transposes a list of waveforms into one list of traces per channel.

    Args:
        samples_array: Waveforms of a table, in play order.

    Returns:
        dict: Channel name to its trace per table index, order preserved.

    Raises:
        ValueError: If the table is empty or mixes single and I/Q waveforms.
    """
    if not samples_array:
        raise ValueError("The waveform table does not hold any waveform")

    channel_arrays: dict[str, list[list[float]]] = {}
    for samples in samples_array:
        channels = as_channel_map(samples)
        if not channel_arrays:
            channel_arrays = {channel: [] for channel in channels}
        elif set(channels) != set(channel_arrays):
            raise ValueError(
                f"All waveforms of a table must drive the same channels, got "
                f"{sorted(channel_arrays)} and {sorted(channels)}")
        for channel, trace in channels.items():
            channel_arrays[channel].append(trace)
    return channel_arrays


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
