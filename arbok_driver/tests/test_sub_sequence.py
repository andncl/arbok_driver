import pytest
import copy
import numpy as np
from qm import generate_qua_script
from arbok_driver import SubSequence, Sample

from arbok_driver.tests.dummy_opx_config import dummy_qua_config

config_1 = {
    'par1': {'unit': 'cycles', 'value': int(1)},
    'par2': {'unit': 'cycles', 'value': int(10)},
    'par3': {'unit': 'cycles', 'value': 1.1},
    'vHome': {'unit': 'V', 'elements': {'P1': 5, 'J1': 6, }},
}

config_2 = {
    'par4': {'unit': 'cycles', 'value': int(2)},
    'par5': {'unit': 'cycles', 'value': int(3)},
    'vHome': {'unit': 'V', 'elements': {'P1': 0, 'J1': 7, }},
}

dummy_sample = Sample('dummy_sample', dummy_qua_config)
sub_sequence_1 = SubSequence('seq1', dummy_sample, config_1)
sub_sequence_2 = SubSequence('seq2', dummy_sample, config_2)
parent_sequence = SubSequence('parent', dummy_sample, {})
parent_sequence.add_subsequence(sub_sequence_1)
parent_sequence.add_subsequence(sub_sequence_2)
set_sweeps_args = [
    {
        parent_sequence.seq1.par1: np.zeros((5)),
        parent_sequence.seq2.par4: np.zeros((5)),
    },
    {
        parent_sequence.seq1.vHome_J1: np.zeros((7))
    },
]

def test_sequence_init() -> None:
    assert sub_sequence_1.par1.get() == 1
    assert sub_sequence_2.par4.get() == 2
    assert len(sub_sequence_1.parameters) == 6
    assert len(sub_sequence_2.parameters) == 5
    assert isinstance(sub_sequence_1.par1.get(), int)

    assert parent_sequence.seq1.par2.get() == 10
    assert parent_sequence.seq2.vHome_P1.get() == 0
    with pytest.raises(KeyError):
        parent_sequence.add_subsequence(sub_sequence_1)

def test_set_sweeps() -> None:
    parent_sequence.set_sweeps(*set_sweeps_args)
    assert len(parent_sequence.sweeps) == 2
    assert parent_sequence.sweeps[0].length == 5
    assert len(parent_sequence.sweeps[0].parameters) == 2
    assert parent_sequence.sweep_size == 35

def test_qua_program_compilation() -> None:
    parent_sequence.set_sweeps(*set_sweeps_args)
    qua_program = parent_sequence.get_qua_program()
    qua_prog_str = generate_qua_script(qua_program, dummy_qua_config)
    print(qua_prog_str)