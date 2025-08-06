import pytest
import numpy as np
from qm import generate_qua_script
from sklearn import dummy

from arbok_driver import Measurement, SubSequence
from arbok_driver.tests.helpers import set_sweeps_args

def test_sequence_init(arbok_driver, dummy_device) -> None:
    """Tests if sequence is correctly initialized"""
    seq = Measurement(arbok_driver, 'dummy_measurement', dummy_device)
    assert seq.name == f'{arbok_driver.name}_dummy_measurement'

def test_sequence_sub_sequence_addition(
        dummy_measurement, dummy_device) -> None:
    """Tests if subsequence is correctly added to sequence"""
    config_1 = {
        'par1': {'unit': 'cycles', 'value': int(1)},
        'par2': {'unit': 'cycles', 'value': int(10)},
        'par3': {'unit': 'cycles', 'value': 1.1},
        'vHome': {'unit': 'V', 'elements': {'P1': 5, 'J1': 6, }},
    }
    seq1 = SubSequence(dummy_measurement, 'seq1', dummy_device, config_1)
    assert len(dummy_measurement.submodules) == 1
    assert len(dummy_measurement.sub_sequences) == 1
    assert dummy_measurement.sub_sequences[0] == seq1
    assert hasattr(dummy_measurement, 'seq1')
    assert dummy_measurement.seq1 == seq1

def test_set_sweeps(sub_sequence_1, dummy_measurement) -> None:
    """Tests if sweeps are correctly set"""
    dummy_measurement.set_sweeps({sub_sequence_1.par1: np.arange(10)},
                              {sub_sequence_1.par2: np.arange(5)})
    assert len(dummy_measurement.sweeps) == 2
    assert dummy_measurement.sweeps[0].length == 10
    assert dummy_measurement.sweeps[1].length == 5
    assert len(dummy_measurement.sweeps[0].parameters) == 1
    assert dummy_measurement.sweep_size == 50

# def test_qua_program_compilation_w_sweeps(
#         dummy_measurement) -> None:
#     """Tests whether the qua code is compiled correctly"""
#     print(dummy_measurement.submodules)
#     dummy_measurement.set_sweeps(*set_sweeps_args(dummy_measurement))
#     qua_prog_str = dummy_measurement.get_qua_program_as_str()
#     dummy_measurement.print_qua_program_to_file('test_output.txt')
#     # we expect 8 declares: 2x3(2 per parameter -> sweep_arr + qua_var)
#     # + 2 as iterators for for loops (per sweep axis)
#     assert len([m.start() for m in re.finditer('declare', qua_prog_str)]) == 8
#     # we expect 3, one per parameter in total
#     assert len([m.start() for m in re.finditer('assign', qua_prog_str)]) == 3
#     # we expect 2 one per sweep axis
#     assert len([m.start() for m in re.finditer('for_', qua_prog_str)]) == 2
