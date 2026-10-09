"""
Tests for `arbok.play` with a generator returning I/Q samples.

A generator returning a plain list of samples drives a DC element, one
returning `{'I': [...], 'Q': [...]}` an up-converted (mixInputs / MWInput)
one. Nothing has to be declared at the call site: the shape of the generator
output decides which kind of pulse is built, in all three modes of the
generator path - amplitude baked in, amplitude scaled at runtime, and
amplitude cached as one waveform per sweep index.
"""
import copy
from dataclasses import dataclass

import numpy as np
import pytest

from arbok_driver import arbok, ParameterClass, SubSequence
from arbok_driver.parameter_types import ParameterMap, Time, Voltage

IQ_ELEMENT = 'qe1'
"""An element of the test config driven by mixInputs"""

PULSE_NS = 200


def iq_ramp_generator(amplitude_v: float, duration_ns: int) -> dict:
    """Linear ramp to amplitude_v on I, its negative on Q."""
    envelope = np.linspace(0, amplitude_v, duration_ns)
    return {'I': envelope.tolist(), 'Q': (-envelope).tolist()}


def dc_ramp_generator(amplitude_v: float, duration_ns: int) -> list:
    """Linear ramp to amplitude_v on a single channel."""
    return np.linspace(0, amplitude_v, duration_ns).tolist()


@dataclass(frozen = True)
class IQPlayParams(ParameterClass):
    v_target: ParameterMap[str, Voltage]
    t_pulse: Time


class IQPlaySequence(SubSequence):
    """Plays a generated I/Q pulse on an up-converted element"""
    PARAMETER_CLASS = IQPlayParams
    arbok_params: IQPlayParams

    def fpga_sequence(self):
        arbok.play(
            elements = [IQ_ELEMENT],
            target = self.arbok_params.v_target,
            operation = iq_ramp_generator,
            duration = self.arbok_params.t_pulse,
        )


iq_conf = {
    'v_target': {'type': Voltage, 'elements': {IQ_ELEMENT: 0.05}},
    't_pulse': {'type': Time, 'value': PULSE_NS//4},
}


@pytest.fixture(name = 'iq_measurement')
def fixture_iq_measurement(mock_measurement):
    """Measurement holding a sequence that plays a generated I/Q pulse"""
    mock_measurement._opx_config = copy.deepcopy(mock_measurement.device.config)
    IQPlaySequence(mock_measurement, 'iq_seq', iq_conf)
    return mock_measurement


GENERATED = 'v_target'
"""The generated operations carry the name of the swept voltage point"""


def _generated_waveforms(config, channel):
    """Returns the generated waveforms of one quadrature, by name"""
    return {
        name: waveform for name, waveform in config['waveforms'].items()
        if GENERATED in name and name.endswith(f'_{channel}_wf')
    }


def _generated_play_lines(program):
    """Returns the lines of the program playing a generated operation"""
    return [
        line for line in program.splitlines()
        if 'play(' in line and GENERATED in line
    ]


# ──────────────────────────────────────────────────────────────────────────
# Fixed amplitude - baked into the samples
# ──────────────────────────────────────────────────────────────────────────

def test_both_quadratures_are_injected(iq_measurement):
    """
    A pulse with a fixed amplitude becomes one arbitrary waveform per
    quadrature, with the amplitude baked in.
    """
    iq_measurement.get_qua_program_as_str(recompile = True)
    config = iq_measurement.opx_config

    for channel, sign in (('I', 1), ('Q', -1)):
        waveforms = _generated_waveforms(config, channel)
        assert len(waveforms) == 1, \
            f"expected one {channel} waveform, got {sorted(waveforms)}"
        waveform = next(iter(waveforms.values()))
        assert waveform['type'] == 'arbitrary'
        assert len(waveform['samples']) == PULSE_NS
        assert waveform['samples'][-1] == pytest.approx(sign*0.05, abs = 1e-6)


def test_pulse_points_at_both_quadratures(iq_measurement):
    """One pulse holds both waveforms, so both play as one operation"""
    iq_measurement.get_qua_program_as_str(recompile = True)
    config = iq_measurement.opx_config

    pulses = {
        name: pulse for name, pulse in config['pulses'].items()
        if GENERATED in name}
    assert len(pulses) == 1
    pulse = next(iter(pulses.values()))
    assert set(pulse['waveforms']) == {'I', 'Q'}
    assert pulse['length'] == PULSE_NS


def test_fixed_amplitude_plays_without_amp(iq_measurement):
    """Nothing is swept, so no classical scaling is needed at runtime"""
    program = iq_measurement.get_qua_program_as_str(recompile = True)

    play_lines = _generated_play_lines(program)
    assert play_lines
    assert not any('amp(' in line for line in play_lines)


# ──────────────────────────────────────────────────────────────────────────
# Swept amplitude - scaled at runtime
# ──────────────────────────────────────────────────────────────────────────

def test_swept_amplitude_scales_both_quadratures(mock_measurement):
    """
    Without waveform caching a swept amplitude falls back to `amp()`.

    A single scalar scales both quadratures of a mixInputs pulse, so the unit
    waveform is generated once per channel.
    """
    mock_measurement._opx_config = copy.deepcopy(mock_measurement.device.config)
    sequence = IQPlaySequence(mock_measurement, 'iq_seq', iq_conf)
    mock_measurement.set_sweeps(
        {sequence.arbok_params.v_target[IQ_ELEMENT]: np.linspace(0.01, 0.1, 10)})

    program = mock_measurement.get_qua_program_as_str(recompile = True)
    config = mock_measurement.opx_config

    for channel in ('I', 'Q'):
        waveforms = _generated_waveforms(config, channel)
        assert len(waveforms) == 1
        assert next(iter(waveforms.values()))['type'] == 'arbitrary'

    play_lines = _generated_play_lines(program)
    assert any('amp(' in line for line in play_lines)


# ──────────────────────────────────────────────────────────────────────────
# Swept amplitude - cached as one waveform per index
# ──────────────────────────────────────────────────────────────────────────

def test_caching_injects_an_array_per_quadrature(mock_measurement):
    """
    A cached I/Q pulse holds one array waveform per quadrature.

    Both arrays carry a trace per sweep index, in sweep order, so the index
    selects a consistent pair.
    """
    mock_measurement._opx_config = copy.deepcopy(mock_measurement.device.config)
    sequence = IQPlaySequence(mock_measurement, 'iq_seq', iq_conf)
    amplitudes = np.linspace(0.01, 0.1, 10)
    mock_measurement.set_sweeps(
        {sequence.arbok_params.v_target[IQ_ELEMENT]: amplitudes})
    mock_measurement.sweeps[0].register_waveform_load(
        sequence.arbok_params.v_target)

    mock_measurement.get_qua_program_as_str(recompile = True)
    config = mock_measurement.opx_config

    scale = sequence.arbok_params.v_target[IQ_ELEMENT].scale
    for channel, sign in (('I', 1), ('Q', -1)):
        waveforms = _generated_waveforms(config, channel)
        assert len(waveforms) == 1, \
            f"expected one {channel} waveform, got {sorted(waveforms)}"
        waveform = next(iter(waveforms.values()))
        assert waveform['type'] == 'array'
        assert len(waveform['samples_array']) == len(amplitudes)
        for index, amplitude in enumerate(amplitudes):
            assert waveform['samples_array'][index][-1] \
                == pytest.approx(sign*amplitude*scale, abs = 1e-6)


def test_caching_loads_once_for_both_quadratures(mock_measurement):
    """
    `load_waveform` selects by pulse, so one call covers both quadratures.

    The index therefore cannot pick the I of one amplitude and the Q of
    another.
    """
    mock_measurement._opx_config = copy.deepcopy(mock_measurement.device.config)
    sequence = IQPlaySequence(mock_measurement, 'iq_seq', iq_conf)
    mock_measurement.set_sweeps(
        {sequence.arbok_params.v_target[IQ_ELEMENT]: np.linspace(0.01, 0.1, 10)})
    mock_measurement.sweeps[0].register_waveform_load(
        sequence.arbok_params.v_target)

    program = mock_measurement.get_qua_program_as_str(recompile = True)

    assert program.count('load_waveform') == 1
    play_lines = _generated_play_lines(program)
    assert play_lines
    assert not any('amp(' in line for line in play_lines)


# ──────────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────────

def test_single_trace_on_an_iq_element_is_rejected(mock_measurement):
    """
    A DC generator on an up-converted element is caught at compilation.

    The hardware rejects it too, but with an error far away from the
    generator that caused it.
    """
    mock_measurement._opx_config = copy.deepcopy(mock_measurement.device.config)

    class DcOnIQSequence(IQPlaySequence):
        ### PARAMETER_CLASS is deliberately not inherited, see SequenceBase
        PARAMETER_CLASS = IQPlayParams

        def fpga_sequence(self):
            arbok.play(
                elements = [IQ_ELEMENT],
                target = self.arbok_params.v_target,
                operation = dc_ramp_generator,
                duration = self.arbok_params.t_pulse,
            )

    DcOnIQSequence(mock_measurement, 'dc_on_iq_seq', iq_conf)
    with pytest.raises(ValueError, match = 'mixInputs/MWInput'):
        mock_measurement.get_qua_program_as_str(recompile = True)


def test_iq_trace_on_a_dc_element_is_rejected(mock_measurement):
    """An I/Q generator on a single input element is caught the same way"""
    mock_measurement._opx_config = copy.deepcopy(mock_measurement.device.config)

    class IQOnDcSequence(IQPlaySequence):
        PARAMETER_CLASS = IQPlayParams

        def fpga_sequence(self):
            arbok.play(
                elements = ['P1'],
                target = self.arbok_params.v_target,
                operation = iq_ramp_generator,
                duration = self.arbok_params.t_pulse,
            )

    IQOnDcSequence(
        mock_measurement, 'iq_on_dc_seq',
        {'v_target': {'type': Voltage, 'elements': {'P1': 0.05}},
         't_pulse': {'type': Time, 'value': PULSE_NS//4}})
    with pytest.raises(ValueError, match = 'singleInput element'):
        mock_measurement.get_qua_program_as_str(recompile = True)
