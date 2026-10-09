"""
Tests for the `IQDrive` example sequence and its pulse generators.

The example is the reference for generating an up-converted pulse in python,
so it is checked end to end: that the envelope reaches the config as two
quadratures, and that sweeping the amplitude caches one envelope per point.
"""
import copy

import numpy as np
import pytest

from arbok_driver.examples.sequences.iq_drive import (
    IQDrive,
    drag_iq_envelope,
    gaussian_iq_envelope,
    iq_drive_conf,
)

DRIVE_ELEMENT = 'qe1'
"""The mixInputs element the example drives"""

DRIVE_NS = iq_drive_conf['parameters']['t_drive']['value']*4
AMPLITUDES = np.linspace(0.0, 0.2, 11)


@pytest.fixture(name = 'drive')
def fixture_drive(mock_measurement) -> IQDrive:
    """Returns the example drive, registered for compilation"""
    mock_measurement._opx_config = copy.deepcopy(mock_measurement.device.config)
    return IQDrive(mock_measurement, 'iq_drive', iq_drive_conf)


def _generated(config, section, channel):
    """Returns the generated entries of one quadrature, by name"""
    suffix = f'_{channel}_wf'
    return {
        name: entry for name, entry in config[section].items()
        if 'v_drive' in name and name.endswith(suffix)
    }


# ──────────────────────────────────────────────────────────────────────────
# Pulse generators
# ──────────────────────────────────────────────────────────────────────────

def test_gaussian_envelope_peaks_at_the_amplitude():
    samples = gaussian_iq_envelope(0.1, DRIVE_NS)

    assert np.iscomplexobj(samples)
    assert len(samples) == DRIVE_NS
    assert samples.real.max() == pytest.approx(0.1, rel = 1e-3)
    np.testing.assert_allclose(samples.imag, 0)


def test_drag_envelope_fills_both_quadratures():
    """The quadrature component is the derivative of the in-phase one"""
    samples = drag_iq_envelope()(0.1, DRIVE_NS)

    assert np.any(samples.imag)
    ### The derivative of a symmetric envelope is antisymmetric
    assert samples.imag[:DRIVE_NS//2].sum() == pytest.approx(
        -samples.imag[-(DRIVE_NS//2):].sum(), abs = 1e-9)


def test_drag_phase_rotates_the_quadratures():
    """A phase of pi/2 swaps the roles of I and Q"""
    x_axis = drag_iq_envelope(phase_rad = 0.0)(0.1, DRIVE_NS)
    y_axis = drag_iq_envelope(phase_rad = np.pi/2)(0.1, DRIVE_NS)

    np.testing.assert_allclose(y_axis.real, -x_axis.imag, atol = 1e-12)
    np.testing.assert_allclose(y_axis.imag, x_axis.real, atol = 1e-12)


def test_every_generator_has_the_same_length(drive):
    """
    All generators of the module are interchangeable.

    A pulse has one length whatever its shape, which is what lets the
    sequence take the generator as an argument.
    """
    for generator in (gaussian_iq_envelope, drag_iq_envelope()):
        assert len(generator(0.1, DRIVE_NS)) == DRIVE_NS


# ──────────────────────────────────────────────────────────────────────────
# Compiled sequence
# ──────────────────────────────────────────────────────────────────────────

def test_drive_injects_both_quadratures(drive, mock_measurement):
    """A complex envelope reaches the config as an I and a Q waveform"""
    mock_measurement.get_qua_program_as_str(recompile = True)
    config = mock_measurement.opx_config

    for channel in ('I', 'Q'):
        waveforms = _generated(config, 'waveforms', channel)
        assert len(waveforms) == 1, \
            f"expected one {channel} waveform, got {sorted(waveforms)}"
        waveform = next(iter(waveforms.values()))
        assert waveform['type'] == 'arbitrary'
        assert len(waveform['samples']) == DRIVE_NS

    pulse = next(
        entry for name, entry in config['pulses'].items() if 'v_drive' in name)
    assert set(pulse['waveforms']) == {'I', 'Q'}
    assert pulse['length'] == DRIVE_NS


def test_drive_takes_another_generator(mock_measurement):
    """The rotation axis is chosen by handing over another generator"""
    mock_measurement._opx_config = copy.deepcopy(mock_measurement.device.config)
    IQDrive(
        mock_measurement, 'iq_drive', iq_drive_conf,
        pulse_generator = drag_iq_envelope(phase_rad = np.pi/2))

    mock_measurement.get_qua_program_as_str(recompile = True)
    config = mock_measurement.opx_config

    ### A y rotation puts the Gaussian on Q, so neither quadrature is empty
    for channel in ('I', 'Q'):
        waveform = next(iter(_generated(config, 'waveforms', channel).values()))
        assert any(waveform['samples'])


def test_swept_amplitude_is_cached_per_point(mock_measurement):
    """
    Registering the caching pre-computes one envelope per amplitude.

    That is the amplitude-Rabi of the module docstring: both quadratures
    become a `type: array` waveform selected by one index.
    """
    mock_measurement._opx_config = copy.deepcopy(mock_measurement.device.config)
    drive = IQDrive(mock_measurement, 'iq_drive', iq_drive_conf)
    mock_measurement.set_sweeps(
        {drive.arbok_params.v_drive[DRIVE_ELEMENT]: AMPLITUDES})
    mock_measurement.register_waveform_caching(drive.arbok_params.v_drive)

    program = mock_measurement.get_qua_program_as_str(recompile = True)
    config = mock_measurement.opx_config

    for channel in ('I', 'Q'):
        waveform = next(iter(_generated(config, 'waveforms', channel).values()))
        assert waveform['type'] == 'array'
        assert len(waveform['samples_array']) == len(AMPLITUDES)

    ### One load covers both quadratures, and the pulse needs no amp()
    assert program.count('load_waveform') == 1
    play_lines = [
        line for line in program.splitlines()
        if 'play(' in line and 'v_drive' in line]
    assert play_lines
    assert not any('amp(' in line for line in play_lines)


def test_cached_envelopes_follow_the_sweep(mock_measurement):
    """Waveform n of the array is the envelope of sweep point n"""
    mock_measurement._opx_config = copy.deepcopy(mock_measurement.device.config)
    drive = IQDrive(mock_measurement, 'iq_drive', iq_drive_conf)
    mock_measurement.set_sweeps(
        {drive.arbok_params.v_drive[DRIVE_ELEMENT]: AMPLITUDES})
    mock_measurement.register_waveform_caching(drive.arbok_params.v_drive)

    mock_measurement.get_qua_program_as_str(recompile = True)
    config = mock_measurement.opx_config

    scale = drive.arbok_params.v_drive[DRIVE_ELEMENT].scale
    samples_array = next(iter(
        _generated(config, 'waveforms', 'I').values()))['samples_array']
    for index, amplitude in enumerate(AMPLITUDES):
        assert max(samples_array[index]) == pytest.approx(
            amplitude*scale, rel = 1e-3, abs = 1e-9)


def test_drive_simulates_as_two_quadratures(drive):
    """
    The same generator drives the simulation backend.

    Nothing is uploaded there, so the envelope is evaluated right away - which
    is how the pulse can be inspected without hardware.
    """
    waveforms = drive.simulate_pulse_waveforms(elements = [DRIVE_ELEMENT])

    samples = waveforms[DRIVE_ELEMENT]
    assert np.iscomplexobj(samples)
    assert len(samples) == DRIVE_NS
    scale = drive.arbok_params.v_drive[DRIVE_ELEMENT].scale
    assert samples.real.max() == pytest.approx(0.1*scale, rel = 1e-3)
