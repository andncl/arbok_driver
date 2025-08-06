import pytest 

from arbok_driver import ArbokDriver, Device, SubSequence, Measurement, parameter_types
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
    return Device(
        name = 'dummy_device',
        opx_config = dummy_qua_config,
        divider_config = divider_config,
    )

@pytest.fixture
def arbok_driver(dummy_device):
    """Returns ArbokDriver instance"""
    driver = ArbokDriver(name = 'arbok_driver', device = dummy_device)
    yield driver
    driver.__del__()
    del driver

@pytest.fixture
def dummy_measurement(arbok_driver, dummy_device):
    """Returns dummy measurement instance"""
    measurement = Measurement(arbok_driver, 'dummy_measurement', dummy_device)
    yield measurement
    measurement.__del__()
    del measurement

@pytest.fixture
def sub_sequence_1(dummy_measurement, dummy_device):
    """Returns dummy subsequence with a few parameters"""
    config_1 = {
        'par1': {'type': parameter_types.Int, 'value': int(1)},
        'par2': {'type': parameter_types.Int, 'value': int(10)},
        'par3': {'type': parameter_types.Voltage, 'value': 1.1},
        'vHome': {'type': parameter_types.Voltage, 'elements': {'P1': 5, 'J1': 6, }},
    }
    seq1 = SubSequence(dummy_measurement, 'sub_seq1', dummy_device, config_1)
    yield seq1
    #seq1.__del__()

@pytest.fixture
def sub_sequence_2(dummy_measurement, dummy_device):
    """Returns dummy subsequence with a few parameters"""
    config_2 = {
        'par4': {'type': parameter_types.Int, 'value': int(2)},
        'par5': {'type': parameter_types.Int, 'value': int(3)},
        'vHome': {'type': parameter_types.Voltage, 'elements': {'P1': 0, 'J1': 7, }},
    }
    seq2 = SubSequence(dummy_measurement, 'sub_seq2', dummy_device, config_2)
    yield seq2
    seq2.__del__()
