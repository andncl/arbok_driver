import pytest 
import numpy as np

from arbok_driver import Sample, SubSequence, Program
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
def program_sequence(dummy_sample, sub_sequence_1, sub_sequence_2):
    program_sequence = Program('program_sequence', dummy_sample)
    program_sequence.add_subsequence(sub_sequence_1)
    program_sequence.add_subsequence(sub_sequence_2)
    yield program_sequence
    program_sequence.__del__()