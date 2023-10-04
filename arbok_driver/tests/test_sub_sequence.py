import copy
import re
import pytest
import numpy as np
from qm import generate_qua_script

from arbok_driver import SubSequence, Sample, SequenceParameter

from arbok_driver.tests.dummy_opx_config import dummy_qua_config

@pytest.fixture
def dummy_sample():
    return Sample('dummy_sample', dummy_qua_config)

@pytest.fixture
def sub_sequence_1(dummy_sample):
    config_1 = {
        'par1': {'unit': 'cycles', 'value': int(1)},
        'par2': {'unit': 'cycles', 'value': int(10)},
        'par3': {'unit': 'cycles', 'value': 1.1},
        'vHome': {'unit': 'V', 'elements': {'P1': 5, 'J1': 6, }},
    }
    seq1 = SubSequence('seq1', dummy_sample, config_1)
    yield seq1
    seq1.__del__()

@pytest.fixture
def sub_sequence_2(dummy_sample):
    config_2 = {
        'par4': {'unit': 'cycles', 'value': int(2)},
        'par5': {'unit': 'cycles', 'value': int(3)},
        'vHome': {'unit': 'V', 'elements': {'P1': 0, 'J1': 7, }},
    }
    seq2 = SubSequence('seq2', dummy_sample, config_2)
    yield seq2
    seq2.__del__()

@pytest.fixture
def parent_sequence(dummy_sample, sub_sequence_1, sub_sequence_2):
    parent_sequence = SubSequence('parent_sequence', dummy_sample)
    parent_sequence.add_subsequence(sub_sequence_1)
    parent_sequence.add_subsequence(sub_sequence_2)
    yield parent_sequence
    parent_sequence.__del__()

@pytest.fixture
def set_sweeps_args(parent_sequence) -> list:
    set_sweeps_args = [
        {
            parent_sequence.seq1.par1: np.zeros((5)),
            parent_sequence.seq2.par4: np.zeros((5)),
        },
        {
            parent_sequence.seq1.vHome_J1: np.zeros((7))
        },
    ]
    return set_sweeps_args

def test_sequence_init(sub_sequence_1, sub_sequence_2) -> None:
    assert sub_sequence_1.par1.get() == 1
    assert sub_sequence_2.par4.get() == 2
    assert len(sub_sequence_1.parameters) == 6
    assert len(sub_sequence_2.parameters) == 5
    assert isinstance(sub_sequence_1.par1.get(), int)

def test_parent_child_sequence_behaviour(parent_sequence, sub_sequence_1) -> None:
    assert parent_sequence.seq1.par2.get() == 10
    assert parent_sequence.seq2.vHome_P1.get() == 0
    with pytest.raises(KeyError):
        parent_sequence.add_subsequence(sub_sequence_1)
        print(parent_sequence.submodules)

def test_set_sweeps(set_sweeps_args, parent_sequence) -> None:
    parent_sequence.set_sweeps(*set_sweeps_args)
    assert len(parent_sequence.sweeps) == 2
    assert parent_sequence.sweeps[0].length == 5
    assert len(parent_sequence.sweeps[0].parameters) == 2
    assert parent_sequence.sweep_size == 35

def test_qua_program_compilation_w_sweeps(
        parent_sequence, set_sweeps_args) -> None:
    parent_sequence.set_sweeps(*set_sweeps_args)
    qua_program = parent_sequence.get_qua_program()
    qua_prog_str = generate_qua_script(qua_program)
    print(qua_prog_str)
    # we expect 8 declares: 2x3(2 per parameter -> sweep_arr + qua_var) 
    # + 2 as iterators for for loops (per sweep axis)
    assert len([m.start() for m in re.finditer('declare', qua_prog_str)]) == 8
    # we expect 3, one per parameter in total
    assert len([m.start() for m in re.finditer('assign', qua_prog_str)]) == 3
    # we expect 2 one per sweep axis
    assert len([m.start() for m in re.finditer('for_', qua_prog_str)]) == 2

def test_add_qc_params_from_config(sub_sequence_1):
    sub_sequence_1.add_qc_params_from_config({
        'par8': {'unit': 'cycles', 'value': int(8)},
        'vRead': {'unit': 'V', 'elements': {'P1': 0.3, 'J1': 7, }},
        })
    assert isinstance(sub_sequence_1.par8, SequenceParameter)
    assert sub_sequence_1.par8() == 8
    assert sub_sequence_1.vRead_J1() == 7
    with pytest.raises(KeyError):
        sub_sequence_1.add_qc_params_from_config({
            'par69': {'unit': 'cycles', 'toast': int(8)},
            })