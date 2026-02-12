"""Testing that the a sub-sequences parameter class is added correctly"""
import pytest
from arbok_driver import SubSequence, EmptyParameterClass
from arbok_driver.parameter_types import (
    Int, Voltage, ParameterMap
)
from .conftest import UserSubSequence

def test_missing_parameter_class() -> None:
    
    class SubSequenceNoParameterClass(SubSequence):
        pass
    assert not hasattr(SubSequenceNoParameterClass, 'arbok_params')
    assert SubSequenceNoParameterClass.PARAMETER_CLASS == EmptyParameterClass

def test_missing_parameter(dummy_measurement) -> None:
    config_1 = {
        'par2': {'type': Int, 'value': int(10)},
        'par3': {'type': Voltage, 'value': 1.1},
        'v_home': {'type': Voltage, 'elements': {'P1': 5, 'J1': 6, }},
    }
    with pytest.raises(TypeError):
        _ = UserSubSequence(
            dummy_measurement, 'sub_seq1', config_1)

def test_parameter_mapping_on_sub_sequence(empty_sub_seq_1) -> None:
    arbok_params = empty_sub_seq_1.arbok_params
    print(arbok_params.__dict__)
    assert len(arbok_params.__dict__) == 4
    assert hasattr(arbok_params, 'par1')
    assert isinstance(arbok_params.v_home, ParameterMap)
    assert not hasattr(arbok_params, 'par3')
    assert 'par3' in empty_sub_seq_1.parameters

def test_parameter_mapping_on_read_sequence(read_sequence_no_readouts) -> None:
    arbok_params = read_sequence_no_readouts.arbok_params
    print(arbok_params.__dict__)
    assert len(arbok_params.__dict__) == 4
    assert hasattr(arbok_params, 'par1')
    assert isinstance(arbok_params.v_home, ParameterMap)
    assert arbok_params.v_home["P1"].get() == 5
    assert not hasattr(arbok_params, 'par3')
    assert 'par3' in read_sequence_no_readouts.parameters
