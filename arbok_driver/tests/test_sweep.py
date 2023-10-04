import pytest
import copy

import numpy as np
from qcodes.instrument import Instrument

from arbok_driver import Sweep
from arbok_driver import SequenceParameter




@pytest.fixture
def mock_instrument() -> Instrument:
    dummy_instrument = Instrument("dummy_instrument")
    dummy_instrument.add_parameter(
        parameter_class = SequenceParameter,
        name  = 'Par1',
        element = "P1",
        config_name = 'dummy',
    )
    dummy_instrument.add_parameter(
        parameter_class = SequenceParameter,
        name  = 'Par2',
        element = "P1",
        config_name = 'dummy',
    )
    yield dummy_instrument
    dummy_instrument.__del__()

@pytest.fixture
def sweep_dict(mock_instrument) -> dict:
    sweep_dict = {
        mock_instrument.Par1: np.ones((10)),
        mock_instrument.Par2: np.zeros((10))
        }
    return sweep_dict

@pytest.fixture
def sweep_dict_with_array_mismatch(sweep_dict, mock_instrument) -> dict:
    sweep_dict_new = copy.copy(sweep_dict)
    sweep_dict_new[mock_instrument.Par1] = np.zeros((11))
    return sweep_dict_new

@pytest.fixture
def sweep_dict_with_wrong_key(sweep_dict) -> dict:
    sweep_dict_new = copy.copy(sweep_dict)
    sweep_dict_new['no_param'] = np.ones((10))
    return sweep_dict_new

def test_sweep_instanciation(
        sweep_dict,
        sweep_dict_with_array_mismatch,
        sweep_dict_with_wrong_key) -> None:
    sweep = Sweep(sweep_dict)
    assert sweep.length == 10
    assert len(sweep.parameters) == 2
    assert len(sweep.config_to_register) == 1
    sweep = Sweep(sweep_dict, register_all = True)
    assert len(sweep.config_to_register) == 2
    with pytest.raises(KeyError):
        sweep.config_to_register = ['no_param']
    with pytest.raises(AttributeError):
        sweep.length = 4
    with pytest.raises(ValueError):
        _ = Sweep(sweep_dict_with_array_mismatch)
    with pytest.raises(TypeError):
        _ = Sweep(sweep_dict_with_wrong_key)
    
