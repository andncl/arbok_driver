import pytest
import copy

import numpy as np
from qcodes.instrument import Instrument

from arbok_driver import Sweep
from arbok_driver import SequenceParameter

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
sweep_dict = {
    dummy_instrument.Par1: np.ones((10)),
    dummy_instrument.Par2: np.zeros((10))
    }

sweep_dict_with_array_mismatch = copy.copy(sweep_dict)
sweep_dict_with_array_mismatch[dummy_instrument.Par1] = np.zeros((11))
sweep_dict_with_wrong_key = copy.copy(sweep_dict)
sweep_dict_with_wrong_key['no_param'] = np.ones((10))

def test_sweep_instanciation() -> None:
    """ Test default instanciation """
    sweep = Sweep(sweep_dict)
    assert sweep.length == 10
    assert len(sweep.parameters) == 2
    assert len(sweep.config_to_register) == 1
    sweep = Sweep(sweep_dict, register_all = True)
    assert len(sweep.config_to_register) == 2
    sweep.config_to_register = [dummy_instrument.Par1]
    assert len(sweep.config_to_register) == 1
    with pytest.raises(KeyError):
        sweep.parameters_to_register = ['no_param']
    with pytest.raises(AttributeError):
        sweep.length = 4
    with pytest.raises(ValueError):
        _ = Sweep(sweep_dict_with_array_mismatch)
    with pytest.raises(TypeError):
        _ = Sweep(sweep_dict_with_wrong_key)
    
