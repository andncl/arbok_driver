import pytest
from qcodes.instrument import Instrument

from arbok_driver import SequenceParameter

@pytest.fixture
def seq_param():
    dummy_inst = Instrument('dummy_inst')
    dummy_inst.add_parameter(
        parameter_class = SequenceParameter,
        name  = 'dummy_param',
        config_name = 'dummy_conf',
        initial_value = 0,
        element = 'P1',
        get_cmd = None,
        set_cmd = None,
    )
    dummy_inst.dummy_param.qua_var = 'placeholder'
    return dummy_inst.dummy_param

def test_sequence_parameter_call(seq_param):
    assert seq_param() == 0
    seq_param.qua_sweeped = True
    assert seq_param.qua_var == 'placeholder'
    with pytest.raises(ValueError):
        seq_param((3,))