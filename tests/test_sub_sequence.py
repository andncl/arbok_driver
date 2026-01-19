import re
import pytest

from arbok_driver import SequenceParameter
from arbok_driver.parameter_types import Time, Voltage
from .helpers import set_sweeps_args

def test_sub_seq_param_init(empty_sub_seq_1, empty_sub_seq_2) -> None:
    """Tests if parameters are correctly initialized from config"""
    assert empty_sub_seq_1.par1.get() == 1
    assert empty_sub_seq_2.par4.get() == 2
    assert len(empty_sub_seq_1.parameters) == 6
    assert len(empty_sub_seq_2.parameters) == 5
    assert isinstance(empty_sub_seq_1.par1.get(), int)

def test_parent_child_sequence_behaviour(
        parent_sub_sequence, empty_sub_seq_1) -> None:
    """Tests the behaviour of nested sub sequences"""
    assert parent_sub_sequence.sub_seq1.par2.get() == 10
    assert parent_sub_sequence.sub_seq2.v_home_P1.get() == 0
    assert parent_sub_sequence.sub_seq1.measurement == parent_sub_sequence
    with pytest.raises(KeyError):
        parent_sub_sequence.add_subsequence(empty_sub_seq_1)
        print(parent_sub_sequence.submodules)

def test_qua_program_compilation_wo_sweeps(
        dummy_measurement) -> None:
    """Tests if any sub sequence within a sequence that has sweeps compiles 
    correctly to QUA code considering those sweeps """
    dummy_measurement.set_sweeps(*set_sweeps_args(dummy_measurement))
    qua_prog_str = dummy_measurement.dummy_parent_sub.get_qua_program_as_str()
    # we expect 8 declares: 2x3(2 per parameter -> sweep_arr + qua_var) 
    # + 2 as iterators for for loops (per sweep axis)
    assert len([m.start() for m in re.finditer('declare', qua_prog_str)]) == 8
    # we expect 3, one per parameter in total
    assert len([m.start() for m in re.finditer('assign', qua_prog_str)]) == 3
    # we expect 2 one per sweep axis
    assert len([m.start() for m in re.finditer('for_', qua_prog_str)]) == 2
    #breakpoint()
    qua_prog_str = dummy_measurement.dummy_parent_sub.sub_seq1.get_qua_program_as_str()
    assert len([m.start() for m in re.finditer('declare', qua_prog_str)]) == 8
    assert len([m.start() for m in re.finditer('assign', qua_prog_str)]) == 3
    assert len([m.start() for m in re.finditer('for_', qua_prog_str)]) == 2


def test_add_qc_params_from_config(empty_sub_seq_1) -> None:
    """Test adding qc params by config"""
    empty_sub_seq_1.add_qc_params_from_config({
        'par8': {'type': Time, 'value': int(8)},
        'v_read': {'type': Voltage, 'elements': {'P1': 0.3, 'J1': 7, }},
        })
    assert isinstance(empty_sub_seq_1.par8, SequenceParameter)
    assert empty_sub_seq_1.par8() == 8
    assert empty_sub_seq_1.vRead_J1() == 7
    with pytest.raises(KeyError):
        empty_sub_seq_1.add_qc_params_from_config({
            'par69': {'type': Time, 'toast': int(8)},
            })

def test_find_measurement(mock_program, dummy_measurement) -> None:
    """Tests if parent sequence is found from sub sequences"""
    mock_program.add_measurement(dummy_measurement)
    parent = mock_program.dummy_measurement.measurement
    assert parent == mock_program.dummy_measurement
    parent = mock_program.dummy_measurement.dummy_parent_sub.measurement
    assert parent == mock_program.dummy_measurement