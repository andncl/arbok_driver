import pytest 

from arbok_driver import ArbokDriver, Device, SubSequence, Sequence
from arbok_driver.tests.dummy_opx_config import dummy_qua_config

opx_scale = 2
divider_config = {
    'gate_1': {
        'division': 1*opx_scale,
    },
    'gate_2': {
        'division': 1*opx_scale,
    },
    'readout_element': {
        'division': 1*opx_scale
    }
}

@pytest.fixture
def dummy_device():
    """Returns dummy device instance"""
    return Device('dummy_device', dummy_qua_config, divider_config)

@pytest.fixture
def arbok_driver(dummy_device):
    """Returns ArbokDriver instance"""
    driver = ArbokDriver('arbok_driver', dummy_device)
    yield driver
    driver.__del__()
    del driver

@pytest.fixture
def dummy_sequence(arbok_driver, dummy_device):
    """Returns dummy sequence instance"""
    sequence = Sequence(arbok_driver, 'dummy_sequence', dummy_device)
    return sequence
    sequence.__del__()
    del sequence

@pytest.fixture
def sub_sequence_1(dummy_sequence, dummy_device):
    """Returns dummy subsequence with a few parameters"""
    config_1 = {
        'par1': {'unit': 'cycles', 'value': int(1)},
        'par2': {'unit': 'cycles', 'value': int(10)},
        'par3': {'unit': 'cycles', 'value': 1.1},
        'vHome': {'unit': 'V', 'elements': {'P1': 5, 'J1': 6, }},
    }
    seq1 = SubSequence(dummy_sequence, 'sub_seq1', dummy_device, config_1)
    yield seq1
    #seq1.__del__()

@pytest.fixture
def sub_sequence_2(dummy_sequence, dummy_device):
    """Returns dummy subsequence with a few parameters"""
    config_2 = {
        'par4': {'unit': 'cycles', 'value': int(2)},
        'par5': {'unit': 'cycles', 'value': int(3)},
        'vHome': {'unit': 'V', 'elements': {'P1': 0, 'J1': 7, }},
    }
    seq2 = SubSequence(dummy_sequence, 'sub_seq2', dummy_device, config_2)
    yield seq2
    seq2.__del__()
