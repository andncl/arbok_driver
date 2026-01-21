"""Module testing the behaviour of the SubSequence class"""
import pytest

from arbok_driver import SequenceParameter
from arbok_driver.parameter_types import Time, Voltage
from .helpers import set_sweeps_args
from .conftest import (
    SquarePulse, UserSubSequence, UserSubSequenceAlt,
    square_pulse_conf, square_pulse_scalable_conf
)

nested_measurement_config = {
    'square': {
        'sequence': SquarePulse,
        'config': square_pulse_conf
    },
    'top_level_seq1': {
        'sub_sequences': {
            'nested_square': {
                'config': square_pulse_conf
            }
        }
    },
    'top_level_seq2': {
        'sub_sequences': {
            'second_level_seq': {
                'sub_sequences': {
                    'third_level_square1': {
                        'config': square_pulse_conf
                    },
                    'third_level_square2': {
                        'config': square_pulse_conf
                    },
                }
            }
        }
    }
}

def test_sub_seq_param_init(empty_sub_seq_1, empty_sub_seq_2) -> None:
    """Tests if parameters are correctly initialized from config"""
    assert empty_sub_seq_1.par1.get() == 1
    assert empty_sub_seq_2.par4.get() == 2
    assert len(empty_sub_seq_1.parameters) == 5
    assert len(empty_sub_seq_2.parameters) == 4
    assert len(empty_sub_seq_1.arbok_params) == 4
    assert len(empty_sub_seq_2.arbok_params) == 4
    assert empty_sub_seq_1.par1.get() == 1

def test_parent_child_sequence_behaviour(dummy_measurement) -> None:
    """Tests the behaviour of nested sub sequences"""
    dummy_measurement.add_subsequences_from_dict(nested_measurement_config)
    assert len(dummy_measurement.sub_sequences) == 3
    assert len(dummy_measurement.submodules) == 3
    assert len(dummy_measurement.top_level_seq2.sub_sequences) == 1
    assert len(
        dummy_measurement.top_level_seq2.second_level_seq.sub_sequences) == 2
    second_level_seq = dummy_measurement.top_level_seq2.second_level_seq
    assert second_level_seq.third_level_square1.element.get() == "P1"
    assert len(second_level_seq.parameters) == 0
    assert second_level_seq.third_level_square1.measurement == dummy_measurement

def test_add_qc_params_from_config(empty_sub_seq_1) -> None:
    """Test adding qc params by config"""
    empty_sub_seq_1.add_qc_params_from_config({
        'par8': {'type': Time, 'value': int(8)},
        'v_read': {'type': Voltage, 'elements': {'P1': 0.3, 'J1': 7, }},
        })
    assert isinstance(empty_sub_seq_1.par8, SequenceParameter)
    assert empty_sub_seq_1.par8() == 8
    assert empty_sub_seq_1.v_read_J1() == 7
    with pytest.raises(ValueError):
        empty_sub_seq_1.add_qc_params_from_config({
            'par69': {'type': Time, 'toast': int(8)},
            })

def test_find_measurement(dummy_measurement) -> None:
    dummy_measurement.add_subsequences_from_dict(nested_measurement_config)
    second_level_seq = dummy_measurement.top_level_seq2.second_level_seq
    assert second_level_seq.measurement == dummy_measurement
    assert second_level_seq.third_level_square2.measurement == dummy_measurement
    assert second_level_seq.third_level_square2.parent == second_level_seq
