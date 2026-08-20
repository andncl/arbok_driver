"""Test module for arbok.ramp generator mode (pulse_generator path)."""
import copy
import re
from dataclasses import dataclass

import numpy as np
import pytest
from qm import generate_qua_script, qua

from arbok_driver import arbok, Measurement, ParameterClass, SubSequence
from arbok_driver.parameter_types import Time, Voltage, ParameterMap
from arbok_driver.arbok.play import _build_pulse_name, _inject_config


@dataclass(frozen=True)
class RampGenParams(ParameterClass):
    v_target: ParameterMap[str, Voltage]
    v_home: ParameterMap[str, Voltage]
    t_ramp: Time


class RampGenSequence(SubSequence):
    PARAMETER_CLASS = RampGenParams
    arbok_params: RampGenParams

    def qua_sequence(self):
        arbok.ramp(
            elements=['P1', 'P2'],
            target=self.arbok_params.v_target,
            reference=self.arbok_params.v_home,
            operation=linear_ramp_generator,
            duration=self.arbok_params.t_ramp,
        )


ramp_gen_conf = {
    'sequence': RampGenSequence,
    'parameters': {
        'v_target': {'type': Voltage, 'elements': {'P1': 0.05, 'P2': -0.03}},
        'v_home': {'type': Voltage, 'elements': {'P1': 0.0, 'P2': 0.0}},
        't_ramp': {'type': Time, 'value': 250},  # 250cc = 1000ns
    }
}


def linear_ramp_generator(amplitude_v: float, duration_ns: int) -> list[float]:
    """Simple linear ramp from 0 to amplitude_v over duration_ns samples."""
    return np.linspace(0, amplitude_v, duration_ns).tolist()


# --- Unit tests for helper functions ---

class TestInjectConfig:
    def test_adds_waveform_pulse_and_operation(self):
        config = {
            'elements': {'P1': {'operations': {}}},
            'waveforms': {},
            'pulses': {},
        }
        samples = np.linspace(0, 0.05, 100).tolist()
        _inject_config(config, 'P1', 'my_op_100ns', samples, 100)

        assert 'my_op_100ns_wf' in config['waveforms']
        assert config['waveforms']['my_op_100ns_wf'] == {
            'type': 'arbitrary', 'samples': samples}
        assert 'my_op_100ns_pulse' in config['pulses']
        assert config['pulses']['my_op_100ns_pulse'] == {
            'operation': 'control', 'length': 100,
            'waveforms': {'single': 'my_op_100ns_wf'}}
        assert config['elements']['P1']['operations']['my_op_100ns'] == 'my_op_100ns_pulse'

    def test_creates_missing_dicts(self):
        config = {'elements': {'J1': {}}}
        _inject_config(config, 'J1', 'op', [0.1, 0.2], 2)
        assert 'waveforms' in config
        assert 'pulses' in config
        assert config['elements']['J1']['operations']['op'] == 'op_pulse'


# --- Integration tests using QUA compilation ---

@pytest.fixture
def ramp_gen_measurement(mock_measurement):
    """Measurement with a RampGenSequence sub-sequence."""
    mock_measurement._opx_config = copy.deepcopy(
        mock_measurement.device.config)
    RampGenSequence(mock_measurement, 'ramp_seq', ramp_gen_conf)
    return mock_measurement


def test_generator_produces_play_without_amp_when_fixed(ramp_gen_measurement):
    """When amplitude is not swept, the compiled QUA should play the operation
    without qua.amp() — amplitude is baked into the waveform."""
    prog_str = ramp_gen_measurement.get_qua_program_as_str(recompile=True)
    # Should contain play statements referencing generated operations
    assert 'ramp_seq' in prog_str
    assert '1000ns' in prog_str
    # No amp() calls since nothing is swept
    play_lines = [l for l in prog_str.splitlines() if 'play(' in l]
    for line in play_lines:
        if '1000ns' in line:
            assert 'amp(' not in line


def test_generator_config_injection(ramp_gen_measurement):
    """Verifies waveform/pulse/operation entries are added to opx_config."""
    ramp_gen_measurement.get_qua_program_as_str(recompile=True)
    config = ramp_gen_measurement.opx_config

    # Check that generated waveforms exist
    gen_wfs = [k for k in config['waveforms'] if '1000ns' in k]
    assert len(gen_wfs) == 2  # one per element (P1, P2)

    # Verify waveform sample count matches duration
    for wf_name in gen_wfs:
        assert len(config['waveforms'][wf_name]['samples']) == 1000

    # Verify pulses reference the waveforms
    gen_pulses = [k for k in config['pulses'] if '1000ns' in k]
    assert len(gen_pulses) == 2
    for p_name in gen_pulses:
        assert config['pulses'][p_name]['length'] == 1000


def test_generator_waveform_values_match_amplitude(ramp_gen_measurement):
    """Waveform samples should encode the actual voltage difference (DAC-level,
    i.e. after divider compensation: user_voltage * divider)."""
    ramp_gen_measurement.get_qua_program_as_str(recompile=True)
    config = ramp_gen_measurement.opx_config

    # P1: target=0.05, home=0.0, divider=6 → DAC amplitude=0.05*6=0.3
    p1_wfs = [k for k in config['waveforms'] if 'v_target_P1' in k]
    assert len(p1_wfs) == 1
    samples = config['waveforms'][p1_wfs[0]]['samples']
    assert samples[-1] == pytest.approx(0.3, abs=1e-6)
    assert samples[0] == pytest.approx(0.0, abs=1e-6)


def test_generator_skips_zero_amplitude(mock_measurement):
    """Elements with zero target-reference difference should be skipped."""
    mock_measurement._opx_config = copy.deepcopy(
        mock_measurement.device.config)
    zero_conf = {
        'sequence': RampGenSequence,
        'parameters': {
            'v_target': {'type': Voltage, 'elements': {'P1': 0.0, 'P2': 0.05}},
            'v_home': {'type': Voltage, 'elements': {'P1': 0.0, 'P2': 0.0}},
            't_ramp': {'type': Time, 'value': 250},
        }
    }
    RampGenSequence(mock_measurement, 'zero_seq', zero_conf)
    prog_str = mock_measurement.get_qua_program_as_str(recompile=True)
    config = mock_measurement.opx_config

    # P1 should have no generated operation (amplitude is 0)
    p1_ops = config['elements']['P1']['operations']
    assert not any('zero_seq' in k for k in p1_ops)
    # P2 should have a generated operation
    p2_ops = config['elements']['P2']['operations']
    assert any('zero_seq' in k for k in p2_ops)


def test_generator_requires_duration(mock_measurement):
    """Generator mode must raise ValueError when duration is None."""
    mock_measurement._opx_config = copy.deepcopy(
        mock_measurement.device.config)
    conf = {
        'v_target': {'type': Voltage, 'elements': {'P1': 0.1}},
        'v_home': {'type': Voltage, 'elements': {'P1': 0.0}},
    }

    @dataclass(frozen=True)
    class NoDurParams(ParameterClass):
        v_target: ParameterMap[str, Voltage]
        v_home: ParameterMap[str, Voltage]

    class NoDurSeq(SubSequence):
        PARAMETER_CLASS = NoDurParams
        arbok_params: NoDurParams

        def qua_sequence(self):
            arbok.ramp(
                elements=['P1'],
                target=self.arbok_params.v_target,
                reference=self.arbok_params.v_home,
                operation=linear_ramp_generator,
                duration=None,
            )

    NoDurSeq(mock_measurement, 'nodur_seq', conf)
    with pytest.raises(ValueError, match="duration"):
        mock_measurement.get_qua_program_as_str(recompile=True)


def test_generator_with_swept_amplitude(mock_measurement):
    """When amplitude is swept, QUA output should contain amp() calls."""
    mock_measurement._opx_config = copy.deepcopy(
        mock_measurement.device.config)
    sweep_conf = {
        'sequence': RampGenSequence,
        'parameters': {
            'v_target': {'type': Voltage, 'elements': {'P1': 0.05, 'P2': 0.03}},
            'v_home': {'type': Voltage, 'elements': {'P1': 0.0, 'P2': 0.0}},
            't_ramp': {'type': Time, 'value': 250},
        }
    }
    seq = RampGenSequence(mock_measurement, 'sweep_seq', sweep_conf)
    # Sweep v_target_P1
    mock_measurement.set_sweeps(
        {seq.arbok_params.v_target['P1']: np.linspace(0.01, 0.1, 10)})
    prog_str = mock_measurement.get_qua_program_as_str(recompile=True)

    # P1 should use amp() since it's swept
    play_lines = [l for l in prog_str.splitlines() if 'play(' in l]
    p1_plays = [l for l in play_lines if 'v_target_P1' in l]
    assert any('amp(' in l for l in p1_plays)


def test_generator_with_swept_duration(mock_measurement):
    """When duration is swept, QUA output should pass duration to play()."""
    mock_measurement._opx_config = copy.deepcopy(
        mock_measurement.device.config)
    sweep_conf = {
        'sequence': RampGenSequence,
        'parameters': {
            'v_target': {'type': Voltage, 'elements': {'P1': 0.05, 'P2': 0.03}},
            'v_home': {'type': Voltage, 'elements': {'P1': 0.0, 'P2': 0.0}},
            't_ramp': {'type': Time, 'value': 250},
        }
    }
    seq = RampGenSequence(mock_measurement, 'dur_sweep_seq', sweep_conf)
    # Sweep t_ramp from 100cc to 500cc → base = 100cc = 400ns
    mock_measurement.set_sweeps(
        {seq.arbok_params.t_ramp: np.array([100, 200, 300, 400, 500])})
    prog_str = mock_measurement.get_qua_program_as_str(recompile=True)
    config = mock_measurement.opx_config

    # Waveform should use shortest duration: 100cc * 4 = 400ns
    gen_wfs = [k for k in config['waveforms'] if 'dur_sweep_seq' in k]
    assert all('400ns' in k for k in gen_wfs)
    for wf_name in gen_wfs:
        assert len(config['waveforms'][wf_name]['samples']) == 400

    # play() calls should include a duration= argument
    play_lines = [l for l in prog_str.splitlines() if 'play(' in l and 'dur_sweep_seq' in l]
    assert all('duration=' in l for l in play_lines)


def test_idempotent_config_injection(mock_measurement):
    """Calling ramp twice with same params should not duplicate config entries."""
    mock_measurement._opx_config = copy.deepcopy(
        mock_measurement.device.config)

    @dataclass(frozen=True)
    class TwiceParams(ParameterClass):
        v_target: ParameterMap[str, Voltage]
        v_home: ParameterMap[str, Voltage]
        t_ramp: Time

    class TwiceSeq(SubSequence):
        PARAMETER_CLASS = TwiceParams
        arbok_params: TwiceParams

        def qua_sequence(self):
            # Call ramp twice with identical parameters
            arbok.ramp(
                elements=['P1'],
                target=self.arbok_params.v_target,
                reference=self.arbok_params.v_home,
                operation=linear_ramp_generator,
                duration=self.arbok_params.t_ramp,
            )
            arbok.ramp(
                elements=['P1'],
                target=self.arbok_params.v_target,
                reference=self.arbok_params.v_home,
                operation=linear_ramp_generator,
                duration=self.arbok_params.t_ramp,
            )

    conf = {
        'v_target': {'type': Voltage, 'elements': {'P1': 0.1}},
        'v_home': {'type': Voltage, 'elements': {'P1': 0.0}},
        't_ramp': {'type': Time, 'value': 50},
    }
    TwiceSeq(mock_measurement, 'twice_seq', conf)
    mock_measurement.get_qua_program_as_str(recompile=True)
    config = mock_measurement.opx_config

    # Should only have one waveform for this sequence despite two ramp calls
    gen_wfs = [k for k in config['waveforms'] if 'twice_seq' in k]
    assert len(gen_wfs) == 1


def test_legacy_mode_unchanged(mock_measurement):
    """String operation still works via legacy path."""
    mock_measurement._opx_config = copy.deepcopy(
        mock_measurement.device.config)

    @dataclass(frozen=True)
    class LegacyParams(ParameterClass):
        v_target: ParameterMap[str, Voltage]

    class LegacySeq(SubSequence):
        PARAMETER_CLASS = LegacyParams
        arbok_params: LegacyParams

        def qua_sequence(self):
            arbok.ramp(
                elements=['P1'],
                target=self.arbok_params.v_target,
                operation='unit_ramp',
            )

    conf = {'v_target': {'type': Voltage, 'elements': {'P1': 0.1}}}
    LegacySeq(mock_measurement, 'legacy_seq', conf)
    prog_str = mock_measurement.get_qua_program_as_str(recompile=True)
    assert 'unit_ramp' in prog_str
