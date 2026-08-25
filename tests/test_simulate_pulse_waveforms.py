"""
Tests for `SequenceBase.simulate_pulse_waveforms`.

Unlike `simulate_waveforms`, this simulates a single (sub)sequence in isolation
and zero pads its elements to a common length, so that the results of several
sequences can be concatenated into one pre-computed waveform. That is what the
gapless gate-set-tomography needs to pre-calculate a whole gate sequence.
"""
from dataclasses import dataclass
import logging

import numpy as np
import pytest

from arbok_driver import arbok, ParameterClass, SubSequence
from arbok_driver.backends.sim_backend import SimBackend
from arbok_driver.parameter_types import Int

LONG_ELEMENT = 'P1'
SHORT_ELEMENT = 'P2'
IDLE_ELEMENT = 'J1'
ELEMENTS = [LONG_ELEMENT, SHORT_ELEMENT, IDLE_ELEMENT]

LONG_CYCLES, SHORT_CYCLES = 50, 25
LONG_NS, SHORT_NS = LONG_CYCLES*4, SHORT_CYCLES*4
LONG_AMPLITUDE, SHORT_AMPLITUDE = 0.5, 0.3
PREPARE_CYCLES = 10
PREPARE_NS = PREPARE_CYCLES*4
PREPARE_AMPLITUDE = 0.1


def constant_generator(amplitude: float, duration_ns: int) -> list[float]:
    """Returns a flat pulse, so a held sample is not zero"""
    return [amplitude]*duration_ns


@dataclass(frozen = True)
class PulseParams(ParameterClass):
    dummy: Int


class TwoPulseSequence(SubSequence):
    """Plays pulses of different length on two elements, none on a third"""
    PARAMETER_CLASS = PulseParams
    arbok_params: PulseParams

    def fpga_sequence(self):
        arbok.play_pulse(
            constant_generator, LONG_ELEMENT, LONG_AMPLITUDE, LONG_CYCLES)
        arbok.play_pulse(
            constant_generator, SHORT_ELEMENT, SHORT_AMPLITUDE, SHORT_CYCLES)


class PrepareAndPulseSequence(TwoPulseSequence):
    """Plays in `fpga_before_sequence` as well as in `fpga_sequence`"""

    def fpga_before_sequence(self):
        arbok.play_pulse(
            constant_generator, LONG_ELEMENT,
            PREPARE_AMPLITUDE, PREPARE_CYCLES)


class WaitSequence(SubSequence):
    """Idles on one element, the only pulse a hardware program can compile"""
    PARAMETER_CLASS = PulseParams
    arbok_params: PulseParams

    def fpga_sequence(self):
        arbok.wait(LONG_CYCLES, LONG_ELEMENT)


pulse_conf = {'dummy': {'type': Int, 'value': 0}}


@pytest.fixture(name='two_pulse_sequence')
def fixture_two_pulse_sequence(mock_measurement) -> TwoPulseSequence:
    """Returns a sub-sequence playing two pulses of different length"""
    return TwoPulseSequence(mock_measurement, 'two_pulses', pulse_conf)


def test_every_requested_element_has_the_same_length(two_pulse_sequence):
    """
    All returned waveforms are exactly as long as the longest element.

    Concatenating pulses per element only lines up if every element of a pulse
    covers the same time span.
    """
    waveforms = two_pulse_sequence.simulate_pulse_waveforms(elements = ELEMENTS)

    assert list(waveforms) == ELEMENTS
    assert {len(waveform) for waveform in waveforms.values()} == {LONG_NS}


def test_shorter_element_is_padded_with_zeros(two_pulse_sequence):
    """
    An element that stops playing early is padded with zeros, not held.

    Holding its last sample - what an align does - would keep a voltage applied
    into whatever is concatenated behind this pulse.
    """
    waveforms = two_pulse_sequence.simulate_pulse_waveforms(elements = ELEMENTS)

    short = waveforms[SHORT_ELEMENT]
    np.testing.assert_allclose(short[:SHORT_NS], SHORT_AMPLITUDE)
    np.testing.assert_array_equal(short[SHORT_NS:], np.zeros(LONG_NS - SHORT_NS))


def test_untouched_element_is_all_zeros(two_pulse_sequence):
    """An element the sequence never plays on holds zeros for the whole pulse"""
    waveforms = two_pulse_sequence.simulate_pulse_waveforms(elements = ELEMENTS)

    np.testing.assert_array_equal(
        waveforms[IDLE_ELEMENT], np.zeros(LONG_NS))


def test_played_samples_are_the_ones_of_the_generator(two_pulse_sequence):
    """The samples come from the pulse the sequence plays"""
    waveforms = two_pulse_sequence.simulate_pulse_waveforms(elements = ELEMENTS)

    np.testing.assert_allclose(
        waveforms[LONG_ELEMENT], np.full(LONG_NS, LONG_AMPLITUDE))


def test_all_played_elements_are_returned_by_default(two_pulse_sequence):
    """Without an element list every element the sequence played is returned"""
    waveforms = two_pulse_sequence.simulate_pulse_waveforms()

    assert sorted(waveforms) == sorted([LONG_ELEMENT, SHORT_ELEMENT])


def test_dropped_element_is_warned_about(mock_measurement, caplog):
    """
    An element that is played but not requested is warned about.

    It still defines how long the pulse took, so silently dropping it would
    stretch the other elements without any hint.
    """
    sequence = TwoPulseSequence(mock_measurement, 'dropped', pulse_conf)

    with caplog.at_level(logging.WARNING):
        waveforms = sequence.simulate_pulse_waveforms(
            elements = [SHORT_ELEMENT])

    assert LONG_ELEMENT in caplog.text
    assert list(waveforms) == [SHORT_ELEMENT]
    ### The dropped element still set the length
    assert len(waveforms[SHORT_ELEMENT]) == LONG_NS


def test_before_sequence_hook_is_simulated(mock_measurement):
    """
    The declare and before_sequence hooks run, not only the sequence hook.

    Pulse durations and amplitudes are commonly assigned there, so skipping
    them would simulate a different pulse than the hardware plays.
    """
    sequence = PrepareAndPulseSequence(
        mock_measurement, 'prepare_and_pulse', pulse_conf)

    waveforms = sequence.simulate_pulse_waveforms(elements = ELEMENTS)

    np.testing.assert_allclose(
        waveforms[LONG_ELEMENT][:PREPARE_NS], PREPARE_AMPLITUDE)
    assert len(waveforms[LONG_ELEMENT]) == PREPARE_NS + LONG_NS


def test_requested_hooks_can_be_narrowed(mock_measurement):
    """Only the given hooks are dispatched"""
    sequence = PrepareAndPulseSequence(
        mock_measurement, 'sequence_hook_only', pulse_conf)

    waveforms = sequence.simulate_pulse_waveforms(
        elements = ELEMENTS, hooks = ('sequence',))

    assert len(waveforms[LONG_ELEMENT]) == LONG_NS


def test_padding_value_is_configurable(two_pulse_sequence):
    """A different pad value is used for both short and untouched elements"""
    waveforms = two_pulse_sequence.simulate_pulse_waveforms(
        elements = ELEMENTS, pad_value = 0.2)

    np.testing.assert_allclose(waveforms[IDLE_ELEMENT], 0.2)
    np.testing.assert_allclose(waveforms[SHORT_ELEMENT][SHORT_NS:], 0.2)


def test_backend_is_restored(arbok_driver, two_pulse_sequence):
    """
    Simulating does not leave the simulation backend active.

    The sequence is simulated in the middle of building a program, so both the
    driver's backend and the active backend have to survive it.
    """
    backend_before = arbok_driver.backend
    active_before = arbok.get_active_backend()

    two_pulse_sequence.simulate_pulse_waveforms(elements = ELEMENTS)

    assert arbok_driver.backend is backend_before
    assert arbok.get_active_backend() is active_before
    assert not isinstance(arbok_driver.backend, SimBackend)


def test_program_still_compiles_after_simulating(mock_measurement):
    """
    The simulation leaves the measurement in a compilable state.

    A sequence that only waits is used here, since a program is compiled for
    the hardware and a generator callable is not a hardware operation.
    """
    sequence = WaitSequence(mock_measurement, 'waiting', pulse_conf)
    waveforms = sequence.simulate_pulse_waveforms(elements = ELEMENTS)

    program = mock_measurement.get_program_as_str(recompile = True)

    assert len(waveforms[LONG_ELEMENT]) == LONG_NS
    assert f"wait({LONG_CYCLES}, '{LONG_ELEMENT}')" in program
