import pytest

from arbok_driver import SequenceParameter

@pytest.fixture
def seq_param(dummy_measurement):
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

def test_sequence_parameter_call(seq_param):
    assert seq_param.qua_var == 'placeholder'
    # with pytest.raises(ValueError):
    #     seq_param((3,))