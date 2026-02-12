
import pytest
from arbok_driver.examples.sub_sequences import (
    SquarePulse, SquarePulseLegacy
)
from arbok_driver.parameter_types import Amplitude, String, Time

def test_sequence_parameter_call(measurement_parameter):
    assert measurement_parameter.qua_var == 'placeholder'
    assert measurement_parameter.qua == 'placeholder'
    assert measurement_parameter() == 'placeholder'
    with pytest.raises(ValueError):
        measurement_parameter(3)

def test_parameter_gettin_in_program(dummy_measurement) -> None:
    conf = {
        "parameters": {
            'amplitude': {'type': Amplitude, 'value': 1.5},
            'element': {'type': String, 'value': 'P1'},
            't_ramp': {'type': Time, 'value': int(100)},
            't_square_pulse': {'type': Time, 'value': int(1000)}
        }
    }
    _ = SquarePulse(
        dummy_measurement, "square_pulse", conf)
    qua_prog_str = dummy_measurement.get_qua_program_as_str()
    qua_prog_str = qua_prog_str.split("program() as prog:")[1]
    dummy_measurement.submodules = {}
    dummy_measurement._sub_sequences = []
    _ = SquarePulse(
        dummy_measurement, "square_pulse", conf)
    qua_prog__legacy_str = dummy_measurement.get_qua_program_as_str(
        recompile = True)
    qua_prog__legacy_str = qua_prog__legacy_str.split("program() as prog:")[1]
    assert qua_prog__legacy_str == qua_prog_str
