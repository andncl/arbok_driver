import copy
import re
import pytest
import numpy as np
from qm import generate_qua_script

from arbok_driver import SubSequence, Sample, SequenceParameter
from arbok_driver.tests.helpers import set_sweeps_args

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

def test_qua_program_compilation_wo_sweeps(
        program_sequence) -> None:
    program_sequence.set_sweeps(*set_sweeps_args(program_sequence))
    qua_program = program_sequence.seq1.get_qua_program()
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