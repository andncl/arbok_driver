"""
Tests for `arbok.load_waveform_table` and `arbok.play_waveform_table`.

The waveform table plays one pre-computed waveform out of a cached table per
element, selected at runtime by an index variable. In contrast to the waveform
caching driven by a sweep (see `test_waveform_caching`), the samples are given
explicitly, which is what a sequence pre-calculating its whole pulse needs.
"""
from dataclasses import dataclass

import numpy as np
import pytest

from arbok_driver import arbok, ParameterClass, SubSequence
from arbok_driver.backends.sim_backend import SimBackend
from arbok_driver.parameter_types import Int
from arbok_driver.sweep import MAX_WFC_WAVEFORMS

ELEMENTS = ['P1', 'P2']
OPERATION = 'cached_pulse'
WAVEFORM_NS = 40
NR_WAVEFORMS = 3

WAVEFORMS = {
    element: [
        np.full(WAVEFORM_NS, 0.1*(index + 1) + 0.01*position)
        for index in range(NR_WAVEFORMS)
    ]
    for position, element in enumerate(ELEMENTS)
}


@dataclass(frozen = True)
class TableParams(ParameterClass):
    waveform_index: Int


class WaveformTableSequence(SubSequence):
    """Plays one waveform of the table, selected by a hardware variable"""
    PARAMETER_CLASS = TableParams
    arbok_params: TableParams

    def fpga_before_sequence(self):
        arbok.load_waveform_table(
            elements = ELEMENTS,
            operation = OPERATION,
            waveforms = WAVEFORMS,
            index = self.arbok_params.waveform_index.hw_var,
            hardware_config = self.measurement.hardware_config,
        )

    def fpga_sequence(self):
        arbok.play_waveform_table(elements = ELEMENTS, operation = OPERATION)


table_conf = {'waveform_index': {'type': Int, 'value': 0}}


@pytest.fixture(name='table_sequence')
def fixture_table_sequence(mock_measurement) -> WaveformTableSequence:
    """Returns a sequence playing a waveform table, registered for compilation"""
    return WaveformTableSequence(mock_measurement, 'table_seq', table_conf)


@pytest.fixture(name='sim_backend')
def fixture_sim_backend() -> SimBackend:
    """Activates a simulation backend for the duration of a test"""
    sim = SimBackend()
    arbok.set_active_backend(sim)
    yield sim
    arbok.set_active_backend(None)


# ──────────────────────────────────────────────────────────────────────────
# Hardware program
# ──────────────────────────────────────────────────────────────────────────

def test_one_load_and_play_per_element(mock_measurement, table_sequence):
    """
    Every element loads the selected waveform and plays it once.

    The whole point of the table is that no classical logic is needed between
    the pulses it replaces.
    """
    program = mock_measurement.get_program_as_str(recompile = True)

    assert program.count(f"load_waveform(pulse='{OPERATION}'") \
        == len(ELEMENTS)
    for element in ELEMENTS:
        assert f"play('{OPERATION}', '{element}')" in program


def test_waveform_is_loaded_before_it_is_played(mock_measurement, table_sequence):
    """
    Every load happens before the first play.

    Selecting a waveform costs FPGA time, which is why it goes into
    `fpga_before_sequence` and not between the played pulses.
    """
    program = mock_measurement.get_program_as_str(recompile = True)
    body = program.split('with program()')[1].split('config =')[0]

    last_load = body.rfind('load_waveform(')
    first_play = body.find(f"play('{OPERATION}'")
    assert -1 < last_load < first_play, \
        f"the waveforms are not all loaded before the pulse:\n{body}"


def test_waveform_is_selected_by_the_swept_index(
        mock_measurement, table_sequence):
    """
    A swept index reaches the program as a variable, not as a constant.

    That is how one program plays every waveform of the table.
    """
    mock_measurement.set_sweeps({
        table_sequence.arbok_params.waveform_index: np.arange(NR_WAVEFORMS)})

    program = mock_measurement.get_program_as_str(recompile = True)

    assert program.count('waveform_index=v') == len(ELEMENTS), \
        f"the waveforms are not selected by a variable:\n{program}"


def test_samples_are_injected_per_element(mock_measurement, table_sequence):
    """
    Each element gets its own waveform array holding all of its waveforms.

    A waveform name is global to the config while the operation selecting it is
    registered per element, so the arrays cannot be shared.
    """
    mock_measurement.get_program_as_str(recompile = True)
    config = mock_measurement.hardware_config

    for element in ELEMENTS:
        waveform = config['waveforms'][f'{OPERATION}_{element}_wf']
        assert waveform['type'] == 'array'
        assert len(waveform['samples_array']) == NR_WAVEFORMS
        np.testing.assert_allclose(
            waveform['samples_array'][1], WAVEFORMS[element][1])
        assert config['pulses'][f'{OPERATION}_{element}_pulse']['length'] \
            == WAVEFORM_NS
        assert config['elements'][element]['operations'][OPERATION] \
            == f'{OPERATION}_{element}_pulse'


# ──────────────────────────────────────────────────────────────────────────
# Simulation backend
# ──────────────────────────────────────────────────────────────────────────

def test_simulation_plays_the_selected_waveform(sim_backend):
    """
    On the simulation backend the samples of the selected waveform are played.

    Nothing is uploaded there, so the table is handed to the backend and the
    index is resolved right away.
    """
    index = sim_backend.declare(int, value = 2)
    with sim_backend.program_context():
        arbok.load_waveform_table(
            elements = ELEMENTS, operation = OPERATION, waveforms = WAVEFORMS,
            index = index, hardware_config = {})
        arbok.play_waveform_table(elements = ELEMENTS, operation = OPERATION)
    waveforms = sim_backend.get_waveforms()

    for element in ELEMENTS:
        np.testing.assert_allclose(
            waveforms[element], WAVEFORMS[element][2])


def test_simulation_accepts_a_plain_index(sim_backend):
    """A python int selects a waveform just like a hardware variable"""
    with sim_backend.program_context():
        arbok.load_waveform_table(
            elements = ELEMENTS, operation = OPERATION, waveforms = WAVEFORMS,
            index = 0, hardware_config = {})
        arbok.play_waveform_table(elements = ELEMENTS, operation = OPERATION)
    waveforms = sim_backend.get_waveforms()

    for element in ELEMENTS:
        np.testing.assert_allclose(
            waveforms[element], WAVEFORMS[element][0])


def test_simulation_follows_a_reloaded_index(sim_backend):
    """Loading again between two pulses selects another waveform"""
    index = sim_backend.declare(int, value = 0)
    with sim_backend.program_context():
        arbok.load_waveform_table(
            elements = ELEMENTS, operation = OPERATION, waveforms = WAVEFORMS,
            index = index, hardware_config = {})
        arbok.play_waveform_table(elements = ELEMENTS, operation = OPERATION)
        index.value = 1
        arbok.load_waveform_table(
            elements = ELEMENTS, operation = OPERATION, waveforms = WAVEFORMS,
            index = index, hardware_config = {})
        arbok.play_waveform_table(elements = ELEMENTS, operation = OPERATION)
    waveforms = sim_backend.get_waveforms()

    for element in ELEMENTS:
        np.testing.assert_allclose(
            waveforms[element],
            np.concatenate([WAVEFORMS[element][0], WAVEFORMS[element][1]]))


def test_playing_an_unknown_operation_is_rejected(sim_backend):
    """Playing without loading first cannot know what to play"""
    with sim_backend.program_context():
        with pytest.raises(TypeError, match='requires a callable'):
            arbok.play_waveform_table(
                elements = ELEMENTS, operation = 'never_loaded')


# ──────────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────────

def test_missing_element_is_rejected():
    """An element without a waveform would be left without a pulse"""
    with pytest.raises(ValueError, match='Missing elements'):
        arbok.load_waveform_table(
            elements = ELEMENTS, operation = OPERATION,
            waveforms = {ELEMENTS[0]: WAVEFORMS[ELEMENTS[0]]},
            index = 0, hardware_config = {})


def test_differing_number_of_waveforms_is_rejected():
    """Every element has to hold a waveform for every index"""
    with pytest.raises(ValueError, match='same number of waveforms'):
        arbok.load_waveform_table(
            elements = ELEMENTS, operation = OPERATION,
            waveforms = {
                ELEMENTS[0]: WAVEFORMS[ELEMENTS[0]],
                ELEMENTS[1]: WAVEFORMS[ELEMENTS[1]][:1],
            },
            index = 0, hardware_config = {})


def test_differing_waveform_length_is_rejected():
    """
    All waveforms of a table need the exact same length.

    They are played by one pulse, which has a single length. Shorter ones have
    to be padded by the caller, which is a deliberate decision - padding here
    would silently change what is played.
    """
    with pytest.raises(ValueError, match='same length'):
        arbok.load_waveform_table(
            elements = [ELEMENTS[0]], operation = OPERATION,
            waveforms = {ELEMENTS[0]: [
                np.zeros(WAVEFORM_NS), np.zeros(WAVEFORM_NS + 4)]},
            index = 0, hardware_config = {})


def test_too_many_waveforms_are_rejected():
    """The hardware holds a limited number of waveforms per array"""
    with pytest.raises(ValueError, match=f'at most {MAX_WFC_WAVEFORMS}'):
        arbok.load_waveform_table(
            elements = [ELEMENTS[0]], operation = OPERATION,
            waveforms = {
                ELEMENTS[0]: [np.zeros(WAVEFORM_NS)]*(MAX_WFC_WAVEFORMS + 1)},
            index = 0, hardware_config = {})


def test_empty_table_is_rejected():
    """Without a waveform there is nothing to load"""
    with pytest.raises(ValueError, match='does not hold any waveform'):
        arbok.load_waveform_table(
            elements = [ELEMENTS[0]], operation = OPERATION,
            waveforms = {ELEMENTS[0]: []}, index = 0, hardware_config = {})
