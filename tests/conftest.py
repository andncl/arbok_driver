from dataclasses import dataclass
import pytest 

from arbok_driver import ArbokDriver, Device, SubSequence, Measurement, parameter_types
from .dummy_opx_config import dummy_qua_config

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

@dataclass
class MeasurementParameterClass:
    iteration: parameter_types.Int

@dataclass
class SubSequenceParameterClass:
    par1: parameter_types.Amplitude

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
    driver.close()

@pytest.fixture
def dummy_measurement(arbok_driver, dummy_device):
    """Returns dummy measurement instance"""
    CustomMeasurement = Measurement
    CustomMeasurement.PARAMETER_CLASS = MeasurementParameterClass
    measurement = Measurement(arbok_driver, 'dummy_measurement', dummy_device)
    yield measurement
    arbok_driver.submodules.pop(measurement.full_name)
    arbok_driver.measurements.remove(measurement)
    del measurement

@pytest.fixture
def sub_sequence_1(dummy_measurement, dummy_device):
    """Returns dummy subsequence with a few parameters"""
    config_1 = {
        'par1': {'type': parameter_types.Int, 'value': int(1)},
        'par2': {'type': parameter_types.Int, 'value': int(10)},
        'par3': {'type': parameter_types.Voltage, 'value': 1.1},
        'vHome': {'type': parameter_types.Voltage,
        'elements': {'P1': 5, 'J1': 6, }},
    }
    SubSequence.PARAMETER_CLASS = SubSequenceParameterClass
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
    SubSequence.PARAMETER_CLASS = SubSequenceParameterClass
    seq2 = SubSequence(dummy_measurement, 'sub_seq2', dummy_device, config_2)
    yield seq2
    seq2.__del__()
