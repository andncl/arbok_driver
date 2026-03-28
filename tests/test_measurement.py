import copy
from dataclasses import dataclass
import re

import numpy as np
import pytest
from qm import generate_qua_script

from arbok_driver import Measurement, SubSequence, ParameterClass
from arbok_driver.examples.configurations.hardware import (
    divider_config
)
from arbok_driver.examples.sub_sequences import (
    SquarePulseScalable, ParityInit, ParityRead
    )
from arbok_driver.examples.configurations.sequence import (
    parity_init_conf, parity_read_conf
)
from arbok_driver.parameter_types import (
    Amplitude, List, Time, Voltage,
)

@dataclass(frozen=True)
class SubSequenceParameterClass(ParameterClass):
    par1: Amplitude

class UserSubSequence(SubSequence):
    PARAMETER_CLASS = SubSequenceParameterClass

def test_measurement_init(arbok_driver) -> None:
    """Tests if sequence is correctly initialized"""
    seq = Measurement(arbok_driver, 'mock_measurement')
    assert seq.name == f'{arbok_driver.name}_mock_measurement'

def test_measurement_sub_sequence_addition(mock_measurement) -> None:
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
        parent = mock_measurement,
        name = 'seq1',
        sequence_config = config_1
        )
    assert len(mock_measurement.submodules) == 1
    assert len(mock_measurement.sub_sequences) == 1
    assert mock_measurement.sub_sequences[0] == seq1
    assert hasattr(mock_measurement, 'seq1')
    assert mock_measurement.seq1 == seq1

def test_set_sweeps(empty_sub_seq_1, mock_measurement) -> None:
    """Tests if sweeps are correctly set"""
    mock_measurement.set_sweeps(
        {empty_sub_seq_1.par1: np.arange(10)},
        {empty_sub_seq_1.par2: np.arange(5)}
        )
    assert len(mock_measurement.sweeps) == 2
    assert mock_measurement.sweeps[0].length == 10
    assert mock_measurement.sweeps[1].length == 5
    assert len(mock_measurement.sweeps[0].parameters) == 1
    assert mock_measurement.sweep_size == 50

def test_set_uneven_sweeps(empty_sub_seq_1, mock_measurement) -> None:
    with pytest.raises(ValueError):
        mock_measurement.set_sweeps(
            {
                empty_sub_seq_1.par1: np.arange(10),
                empty_sub_seq_1.par2: np.arange(5)
            }
            )
        
def test_non_dict_sweeps(empty_sub_seq_1, mock_measurement) -> None:
    with pytest.raises(TypeError):
        mock_measurement.set_sweeps(6, 'test')

def test_non_sequence_parameter_sweeps(empty_sub_seq_1, mock_measurement) -> None:
    with pytest.raises(TypeError):
        mock_measurement.set_sweeps({'test': np.arange(10)})

def test_zero_length_sweeps(empty_sub_seq_1, mock_measurement) -> None:
    with pytest.raises(ValueError):
        mock_measurement.set_sweeps({empty_sub_seq_1.par1: np.arange(0)})

def test_warning_for_duplicate_value_sweeps(
        empty_sub_seq_1, mock_measurement) -> None:
    with pytest.warns(UserWarning):
        mock_measurement.set_sweeps({empty_sub_seq_1.par1: [1, 1, 2, 3, 4]})

def test_qua_program_compilation_w_linear_sweeps(
        empty_sub_seq_1, mock_measurement) -> None:
    """Tests whether the qua code is compiled correctly"""
    mock_measurement.set_sweeps(
        {empty_sub_seq_1.par1: np.arange(0, 10, 1)},
        {empty_sub_seq_1.v_home_P1: np.arange(-0.1, 0.1, 0.01)}
        )
    qua_prog_str = mock_measurement.get_qua_program_as_str()
    qua_prog = mock_measurement.get_qua_program()
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
        empty_sub_seq_1, mock_measurement) -> None:
    """Tests whether the qua code is compiled correctly"""
    mock_measurement.set_sweeps(
        {empty_sub_seq_1.par2: np.arange(0, 10, 1)},
        {empty_sub_seq_1.v_home_P1: np.random.rand(8)}
        )
    qua_prog_str = mock_measurement.get_qua_program_as_str()
    qua_prog = mock_measurement.get_qua_program()
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
        square_pulse, mock_measurement) -> None:
    qua_prog_str = mock_measurement.get_qua_program_as_str()
    qua_prog = mock_measurement.get_qua_program()
    qua_prog_str = generate_qua_script(qua_prog)
    print(qua_prog_str)
    assert len(re.findall(r'"ramp"\*amp', qua_prog_str)) == 2

@pytest.mark.parametrize("nr_gates", [0, 1, 2, 4])
def test_qua_program_compilation_scalable_square_pulse(
    mock_measurement,
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
        mock_measurement,
        f"square_pulse_{nr_gates}",
        init_conf,
    )
    for i in range(nr_gates):
        gate = f"P{i}"
        if gate in divider_config:
            scale = divider_config[gate]['division']
        else:
            scale = 1
        assert square_pulse.arbok_params.v_home[gate].qua == 0
        assert square_pulse.arbok_params.v_square[gate].qua == 0.1 * (1 + i)*scale
    qua_prog_str = mock_measurement.get_qua_program_as_str()
    nr_of_plays = len(
        list(re.finditer(r'"unit_ramp"\*amp', qua_prog_str))
    )
    assert nr_of_plays == 2 * nr_gates

    
def test_add_subsequences_from_dict(mock_measurement) -> None:
    mock_measurement.add_subsequences_from_dict(
        {
            'paraity_init_even': {'config': parity_init_conf},
            'parity_read_even': {'config': parity_read_conf},
            'parity_init_odd': {
                'config': parity_init_conf
            },
            'parity_read_odd': {
                'sequence': ParityRead,
                'config': parity_read_conf
            }
        }
    )
    assert len(mock_measurement.sub_sequences) == 4
    qua_prog_str = mock_measurement.get_qua_program_as_str()
