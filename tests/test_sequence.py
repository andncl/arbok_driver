import copy
from dataclasses import dataclass
import re

import numpy as np
import pytest
from qm import generate_qua_script

from arbok_driver import Measurement, SubSequence, ParameterClass
from arbok_driver.examples.sub_sequences import SquarePulseScalable
from arbok_driver.parameter_types import (
    Amplitude, List, Time, Voltage,
)

@dataclass
class SubSequenceParameterClass(ParameterClass):
    par1: Amplitude

class UserSubSequence(SubSequence):
    PARAMETER_CLASS = SubSequenceParameterClass

def test_measurement_init(arbok_driver, dummy_device) -> None:
    """Tests if sequence is correctly initialized"""
    seq = Measurement(arbok_driver, 'dummy_measurement', dummy_device)
    assert seq.name == f'{arbok_driver.name}_dummy_measurement'

def test_measurement_sub_sequence_addition(
        dummy_measurement, dummy_device) -> None:
    """Tests if subsequence is correctly added to sequence"""
    config_1 = {
        'parameters':{
            'par1': {'type': Time, 'value': int(100)},
            'par2': {'type': Time, 'value': int(10)},
            'par3': {'type': Voltage, 'value': 1.1},
            'v_home': {'type': Amplitude, 'elements': {
                'P1': 0.5, 'J1': 0.6, }},
        }
    }
    # SubSequence.PARAMETER_CLASS = SubSequenceParameterClass
    seq1 = UserSubSequence(
        parent = dummy_measurement,
        name = 'seq1',
        device = dummy_device,
        sequence_config = config_1
        )
    assert len(dummy_measurement.submodules) == 1
    assert len(dummy_measurement.sub_sequences) == 1
    assert dummy_measurement.sub_sequences[0] == seq1
    assert hasattr(dummy_measurement, 'seq1')
    assert dummy_measurement.seq1 == seq1

def test_set_sweeps(empty_sub_seq_1, dummy_measurement) -> None:
    """Tests if sweeps are correctly set"""
    dummy_measurement.set_sweeps(
        {empty_sub_seq_1.par1: np.arange(10)},
        {empty_sub_seq_1.par2: np.arange(5)}
        )
    assert len(dummy_measurement.sweeps) == 2
    assert dummy_measurement.sweeps[0].length == 10
    assert dummy_measurement.sweeps[1].length == 5
    assert len(dummy_measurement.sweeps[0].parameters) == 1
    assert dummy_measurement.sweep_size == 50

def test_qua_program_compilation_w_linear_sweeps(
        empty_sub_seq_1, dummy_measurement) -> None:
    """Tests whether the qua code is compiled correctly"""
    dummy_measurement.set_sweeps(
        {empty_sub_seq_1.par1: np.arange(0, 10, 1)},
        {empty_sub_seq_1.v_home_P1: np.arange(-0.1, 0.1, 0.1)}
        )
    qua_prog_str = dummy_measurement.get_qua_program_as_str()
    qua_prog = dummy_measurement.get_qua_program()
    qua_prog_str = generate_qua_script(qua_prog)
    # we expect 5 declares: 2x2 (2 per parameter -> iterator + qua_var)
    # + 1 to track the shots (always there!)
    assert len(re.findall(r'declare\(', qua_prog_str)) == 5
    # we expect 8:
    # 4 =2x2 (2 per parameter, initial val and increment)
    # +2 for shot tracker (init and increment)
    # +2 for each sweep axis
    assert len(re.findall('assign', qua_prog_str)) == 8
    # we expect 2 one per sweep axis
    assert len(re.findall('while_', qua_prog_str))== 2

def test_qua_program_compilation_w_non_linear_sweeps(
        empty_sub_seq_1, dummy_measurement) -> None:
    """Tests whether the qua code is compiled correctly"""
    dummy_measurement.set_sweeps(
        {empty_sub_seq_1.par2: np.arange(0, 10, 1)},
        {empty_sub_seq_1.v_home_P1: np.random.rand(8)}
        )
    qua_prog_str = dummy_measurement.get_qua_program_as_str()
    qua_prog = dummy_measurement.get_qua_program()
    qua_prog_str = generate_qua_script(qua_prog)
    # we expect 5 declares: 2x2 (2 per parameter -> iterator + qua_var)
    # +1 extra for declaring the explicit array (of non-lin sweep)
    # + 1 to track the shots (always there!)
    assert len(re.findall(r'declare\(', qua_prog_str)) == 6
    # we expect 8:
    # 4 =2x2 (2 per parameter, initial val and increment)
    # +2 for shot tracker (init and increment)
    # +2 for each sweep axis
    assert len(re.findall('assign', qua_prog_str)) == 8
    # we expect 2 one per sweep axis
    assert len(re.findall('while_', qua_prog_str)) == 2

def test_qua_program_compilation_simple_square_pulse(
        square_pulse, dummy_measurement) -> None:
    qua_prog_str = dummy_measurement.get_qua_program_as_str()
    qua_prog = dummy_measurement.get_qua_program()
    qua_prog_str = generate_qua_script(qua_prog)
    print(qua_prog_str)
    assert len(re.findall(r'"ramp"\*amp', qua_prog_str)) == 2

@pytest.mark.parametrize("nr_gates", [0, 1, 2, 4])
def test_qua_program_compilation_scalable_square_pulse(
    dummy_measurement,
    dummy_device,
    nr_gates,
    ) -> None:
    conf = {
        "parameters": {
            't_ramp': {'type': Time, 'value': int(100)},
            'sticky_elements': {'type': List, 'value': []},
            't_square_pulse': {'type': Time, 'value': int(1000)},
            'v_home': {'type': Voltage, 'elements': {}},
            'v_square': {'type': Voltage, 'elements': {}}
        }
    }
    init_conf = copy.deepcopy(conf)
    init_conf["parameters"]["v_home"]["elements"] = {
        f"P{i}": 0 for i in range(nr_gates)
    }
    init_conf["parameters"]["v_square"]["elements"] = {
        f"P{i}": 0.1 * (1 + i) for i in range(nr_gates)
    }
    init_conf["parameters"]["sticky_elements"]["value"] = [
        f"P{i}" for i in range(nr_gates)
    ]
    square_pulse = SquarePulseScalable(
        dummy_measurement,
        f"square_pulse_{nr_gates}",
        dummy_device,
        init_conf,
    )
    qua_prog_str = dummy_measurement.get_qua_program_as_str()
    nr_of_plays = len(
        list(re.finditer(r'"unit_ramp"\*amp', qua_prog_str))
    )
    assert nr_of_plays == 2 * nr_gates
