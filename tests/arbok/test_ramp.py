"""Test module asserting functionality of arbok.ramp"""
from dataclasses import dataclass
import re

import pytest
from qm import generate_qua_script, qua

from arbok_driver import arbok, ParameterClass, SubSequence
from arbok_driver.parameter_types import Voltage, ParameterMap

@dataclass(frozen = True)
class TestSubSequenceParameterClass(ParameterClass):
    v_home0: ParameterMap[str, Voltage]
    v_home1: ParameterMap[str, Voltage]
    v_home2: ParameterMap[str, Voltage]
    v_home3: ParameterMap[str, Voltage]

class UserSubSequence(SubSequence):
    PARAMETER_CLASS = TestSubSequenceParameterClass
    arbok_params: TestSubSequenceParameterClass
    
test_conf = {
    "sequence": UserSubSequence,
    "parameters": {
        'v_home0': {
            'type': Voltage,
            'elements': {
                'P1': 0.0,
                'P2': 0.0,
                'P3': 0.0
            }
        },
        'v_home1': {
            'type': Voltage,
            'elements': {
                'P1': 0.0,
                'P2': 0.0,
            }
        },
        'v_home2': {
            'type': Voltage,
            'elements': {
                'P1': 0.0,
                'P2': 0.0,
                'P3': 0.0
            }
        },
        'v_home3': {
            'type': Voltage,
            'elements': {
                'P1': 0.1,
                'P2': 0.2,
                'P3': 0.3
            }
        },
    }
}

def test_nr_of_ramps(square_pulse_scalable, dummy_measurement):
    prog_str = dummy_measurement.get_qua_program_as_str(recompile = True)
    assert len(list(re.finditer("unit_ramp", prog_str))) == 6

    square_pulse_scalable.arbok_params.sticky_elements.set(["P1", "P2"])
    prog_str = dummy_measurement.get_qua_program_as_str(recompile = True)
    assert len(list(re.finditer("unit_ramp", prog_str))) == 4

def test_no_ramps_for_negligible_amplitudes(
        square_pulse_scalable, dummy_measurement):
    square_pulse_scalable.arbok_params.v_square["P1"].set(0)
    square_pulse_scalable.arbok_params.v_square["P2"].set(0)
    prog_str = dummy_measurement.get_qua_program_as_str(recompile = True)
    assert len(list(re.finditer("unit_ramp", prog_str))) == 2

def test_ramp_without_origin(dummy_measurement):
    test_sequence = UserSubSequence(
        dummy_measurement, "test_sequence", test_conf
        )
    with qua.program() as prg:
        arbok.ramp(
            elements = ["P1", "P2"],
            target = test_sequence.arbok_params.v_home3,
            operation = "unit_ramp"
        )
    prg_str = generate_qua_script(prg)
    print(prg_str)
    assert len(list(re.finditer("unit_ramp", prg_str))) == 2

def test_missing_elements_in_mapping(dummy_measurement):
    test_sequence = UserSubSequence(
        dummy_measurement, "test_sequence", test_conf
        )
    with pytest.raises(ValueError):
        arbok.ramp(
            elements = ["P1", "P2", "P12"],
            target = test_sequence.arbok_params.v_home0,
            operation = "unit_ramp"
        )

def test_difference_calulated_correctly(dummy_measurement):
    test_sequence = UserSubSequence(
        dummy_measurement, "test_sequence", test_conf
        )
    with qua.program() as prg:
        arbok.ramp(
            elements = ["P1"],
            target = test_sequence.arbok_params.v_home3,
            reference = test_sequence.arbok_params.v_home0,
            operation = "unit_ramp"
        )
    prg_str = generate_qua_script(prg)
    amp = prg_str.split("amp(")[1].split(')')[0]
    assert float(amp) == pytest.approx(0.6)
