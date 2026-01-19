from dataclasses import dataclass
import pytest 

from arbok_driver import (
    ArbokDriver,
    Device,
    Measurement,
    ParameterClass,
    ReadSequence,
    SubSequence,
)
from arbok_driver.parameter_types import (
    Amplitude, Int, Voltage, ParameterMap
)
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


@dataclass(frozen = True)
class SubSequenceParameterClass(ParameterClass):
    par1: Amplitude
    par2: Amplitude
    iteration: Int
    v_home: ParameterMap[str, Voltage]

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
    measurement = Measurement(
        arbok_driver, 'dummy_measurement', dummy_device,
        sequence_config= {'iteration': {'type': Int, 'value': 9}})
    yield measurement
    arbok_driver.submodules.pop(measurement.full_name)
    arbok_driver.measurements.remove(measurement)
    del measurement

@pytest.fixture
def sub_sequence_1(dummy_measurement, dummy_device):
    """Returns dummy subsequence with a few parameters"""
    config_1 = {
        'par1': {'type': Int, 'value': int(1)},
        'par2': {'type': Int, 'value': int(10)},
        'par3': {'type': Voltage, 'value': 1.1},
        'v_home': {'type': Voltage, 'elements': {'P1': 5, 'J1': 6, }},
    }
    SubSequence.PARAMETER_CLASS = SubSequenceParameterClass
    seq1 = SubSequence(dummy_measurement, 'sub_seq1', dummy_device, config_1)
    yield seq1

@pytest.fixture
def sub_sequence_2(dummy_measurement, dummy_device):
    """Returns dummy subsequence with a few parameters"""
    config_2 = {
        'par4': {'type': Int, 'value': int(2)},
        'par5': {'type': Int, 'value': int(3)},
        'v_home': {'type': Voltage, 'elements': {'P1': 0, 'J1': 7, }},
    }
    SubSequence.PARAMETER_CLASS = SubSequenceParameterClass
    seq2 = SubSequence(dummy_measurement, 'sub_seq2', dummy_device, config_2)
    yield seq2
    seq2.__del__()

@pytest.fixture
def read_sequence_no_readouts(dummy_measurement, dummy_device):
    """Returns dummy subsequence with a few parameters"""
    config_1 = {
        'parameters': {
            'par1': {'type': Int, 'value': int(1)},
            'par2': {'type': Int, 'value': int(10)},
            'par3': {'type': Voltage, 'value': 1.1},
            'v_home': {'type': Voltage, 'elements': {'P1': 5, 'J1': 6, }},
        },
        'signals': [],
        'readout_groups': {}
    }
    ReadSequence.PARAMETER_CLASS = SubSequenceParameterClass
    seq1 = ReadSequence(dummy_measurement, 'read_seq', dummy_device, config_1)
    yield seq1