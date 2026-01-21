"""Module containing fixtures for pytests"""
from dataclasses import dataclass
import pytest 

from arbok_driver import (
    ArbokDriver,
    Device,
    Measurement,
    ParameterClass,
    ReadSequence,
    SequenceParameter,
    SubSequence,
)
from arbok_driver.examples.configurations import (
    square_pulse_conf,
    square_pulse_scalable_conf,
    opx1000_config,
    divider_config
)
from arbok_driver.examples.sub_sequences import (
    SquarePulse,
    SquarePulseScalable
)
from arbok_driver.parameter_types import (
    Amplitude, Int, List, ParameterMap,  Time, Voltage
)

@dataclass(frozen = True)
class SubSequenceParameterClass(ParameterClass):
    par1: Amplitude
    par2: Amplitude
    iteration: Int
    v_home: ParameterMap[str, Voltage]

@dataclass(frozen = True)
class SubSequenceParameterClassAlt(ParameterClass):
    par4: Amplitude
    par5: Amplitude
    iteration: Int
    v_home: ParameterMap[str, Voltage]

class UserSubSequence(SubSequence):
    PARAMETER_CLASS = SubSequenceParameterClass

class UserSubSequenceAlt(SubSequence):
    PARAMETER_CLASS = SubSequenceParameterClassAlt

class UserReadSequence(ReadSequence):
    PARAMETER_CLASS = SubSequenceParameterClass

@pytest.fixture
def dummy_device():
    """Returns dummy device instance"""
    return Device(
        name = 'dummy_device',
        opx_config = opx1000_config,
        divider_config = divider_config,
    )

@pytest.fixture
def arbok_driver(dummy_device):
    """Returns ArbokDriver instance"""
    driver = ArbokDriver(name = 'arbok_driver', device = dummy_device)
    yield driver
    driver.close()

@pytest.fixture
def dummy_measurement(arbok_driver, dummy_device) -> Measurement: # type: ignore[reportInvalidTypeForm]
    """Returns dummy measurement instance"""
    measurement = Measurement(
        arbok_driver, 'dummy_measurement', dummy_device,
        sequence_config= {'iteration': {'type': Int, 'value': 9}})
    yield measurement
    arbok_driver.submodules.pop(measurement.full_name)
    arbok_driver.measurements.remove(measurement)
    del measurement

@pytest.fixture
def empty_sub_seq_1(dummy_measurement, dummy_device):
    """Returns dummy subsequence with a few parameters"""
    config_1 = {
        'par1': {'type': Int, 'value': int(1)},
        'par2': {'type': Int, 'value': int(10)},
        'par3': {'type': Voltage, 'value': 1.1},
        'v_home': {'type': Voltage, 'elements': {'P1': 5, 'J1': 6, }},
    }
    seq1 = UserSubSequence(dummy_measurement, 'sub_seq1', dummy_device, config_1)
    yield seq1

@pytest.fixture
def empty_sub_seq_2(dummy_measurement, dummy_device):
    """Returns dummy subsequence with a few parameters"""
    config_2 = {
        'par4': {'type': Int, 'value': int(2)},
        'par5': {'type': Int, 'value': int(3)},
        'v_home': {'type': Voltage, 'elements': {'P1': 0, 'J1': 7, }},
    }
    seq2 = UserSubSequenceAlt(
        dummy_measurement, 'sub_seq2', dummy_device, config_2)
    yield seq2

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
    seq1 = UserReadSequence(
        dummy_measurement, 'read_seq', dummy_device, config_1)
    yield seq1

@pytest.fixture
def measurement_parameter(dummy_measurement):
    dummy_measurement.add_parameter(
        parameter_class = SequenceParameter,
        name  = 'dummy_param',
        # config_name = 'dummy_conf',
        initial_value = 0,
        scale = 1,
        get_cmd = None,
        set_cmd = None,
    )
    dummy_measurement.dummy_param.qua_var = 'placeholder'
    return dummy_measurement.dummy_param

@pytest.fixture
def square_pulse(dummy_measurement, dummy_device):
    square_pulse = SquarePulse(
        dummy_measurement, "square_pulse", dummy_device, square_pulse_conf)
    yield square_pulse

@pytest.fixture
def square_pulse_scalable(dummy_measurement, dummy_device):
    conf = {
        "parameters": {
            'amplitude': {'type': Amplitude, 'value': 1.5},
            't_ramp': {'type': Time, 'value': int(100)},
            'sticky_elements': {'type': List, 'value': ['P1', 'P2', 'P3']},
            't_square_pulse': {'type': Time, 'value': int(1000)},
            'v_home': {
                'type': Voltage,
                'elements': {
                    'P1': 0.1,
                    'P2': -0.2,
                    'P3': 0.2
                }
            }
        }
    }
    square_pulse = SquarePulseScalable(
        dummy_measurement, "square_pulse",  dummy_device,
        square_pulse_scalable_conf
        )
    yield square_pulse
