import pytest
import re
from qm import generate_qua_script

from arbok_driver import Program
from arbok_driver.tests.helpers import set_sweeps_args

def test_set_sweeps(dummy_sequence) -> None:
    """"""
    dummy_sequence.set_sweeps(*set_sweeps_args(dummy_sequence))
    assert len(dummy_sequence.sweeps) == 2
    assert dummy_sequence.sweeps[0].length == 5
    assert len(dummy_sequence.sweeps[0].parameters) == 2
    assert dummy_sequence.sweep_size == 35

def test_qua_program_compilation_w_sweeps(
        dummy_sequence) -> None:
    """Tests whether the qua code is compiled correctly"""
    print(dummy_sequence.submodules)
    dummy_sequence.set_sweeps(*set_sweeps_args(dummy_sequence))
    qua_prog_str = dummy_sequence.qua_program_as_str
    # we expect 8 declares: 2x3(2 per parameter -> sweep_arr + qua_var)
    # + 2 as iterators for for loops (per sweep axis)
    assert len([m.start() for m in re.finditer('declare', qua_prog_str)]) == 8
    # we expect 3, one per parameter in total
    assert len([m.start() for m in re.finditer('assign', qua_prog_str)]) == 3
    # we expect 2 one per sweep axis
    assert len([m.start() for m in re.finditer('for_', qua_prog_str)]) == 2
