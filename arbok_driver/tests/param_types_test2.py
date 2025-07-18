# import pytest
import tempfile

from arbok_driver import ArbokDriver, Sequence, SubSequence
from arbok_driver.parameter_types import Voltage, Time, String
import numpy as np

from qm import qua

class SquarePulse(SubSequence):
    """
    Class containing parameters and sequence for a simple square pulse
    """

    def qua_sequence(self):
        """Macro that will be played within the qua.program() context"""
        qua.align()
        qua.play('ramp'*qua.amp(self.amplitude()), self.element(), duration = self.ramp_time())
        qua.wait(self.t_square_pulse(), self.element())
        qua.play('ramp'*qua.amp(-self.amplitude()), self.element(), duration = self.ramp_time())

square_conf = {
    'amplitude': {
        'value': 0.5,
        'type': Voltage,
    },
    't_square_pulse': {
        'value': 100,
        'type': Time
    },
    'element': {
        'type': String,
        'value': 'gate_1',
        'unit': 'gate label'
    },
    'ramp_time': {
        'value': 20,
        'type': Time
    },
}

opx_scale = 2
divider_config = {
    'gate_1': {
        'division': 1*opx_scale,
    },
    'gate_2': {
        'division': 1*opx_scale,
    },
    'readout_element': {
        'division': 1*opx_scale
    }
}

from arbok_driver import Device
from arbok_driver.tests.dummy_opx_config import dummy_qua_config
dummy_device = Device('dummy_device', dummy_qua_config, divider_config)


# def test_parameters(dummy_device, capfd) -> None:
qm_driver = ArbokDriver('qm_driver', dummy_device)
dummy_sequence = Sequence(qm_driver, 'dummy_squence', dummy_device)

square_pulse = SquarePulse(dummy_sequence, 'square_pulse', dummy_device, square_conf)

try:
    print(square_pulse.t_square_pulse.set(100.1))
    raise Exception("test should fail on in validator, but didn't")
except:
    print("validator test failed as expected")

dummy_sequence.set_sweeps(
    {
        square_pulse.amplitude: np.linspace(0.1, 1, 5)
    }
)

dummy_sequence.set_sweeps(
    {
        square_pulse.t_square_pulse: np.linspace(1, 4, 2, dtype = int) # this should stop the test from working
    }
)

try:
    dummy_sequence.set_sweeps(
        {
            square_pulse.t_square_pulse: np.linspace(0.1, 1, 5)
        }
    )
    raise Exception("test should fail on in validator, but didn't")
except ValueError:
    print("array validator test failed as expected")

dummy_sequence.reset()

square_pulse.t_square_pulse.set(50)
try:
    square_pulse.t_square_pulse.set(np.linspace(0.1, 1, 5))
    raise Exception("test should fail on in validator, but didn't")
except TypeError:
    print("array validator test failed as expected")


from qcodes.validators import Numbers, Sequence, Ints

square_conf2 = {
    'vHome': {
        'type' : Voltage,
        'unit': 'v label 3',
        "label": 'Default voltage point during the sequence',
        'elements': {
            'gate_1': 0,
            'gate_2': 0,
            'gate_3': 0,
            'gate_4': 0,
        }
    },
    'amplitude2': {
        'value': 0.5,
        'type': Voltage,
        'unit': 'v label 2'
    },
    't_square_pulse2': {
        'value': 100,
        'type': Time,
        'qua_type': qua.fixed,
        'validator': Numbers()
    },
    'amplitude3': {
        'value': 0.5,
        'unit': 'v label 2'
    },
}

square_pulse2 = SquarePulse(dummy_sequence, 'square_pulse2', dummy_device, square_conf2)
if square_pulse2.vHome_gate_1.unit != 'v label 3':
    raise Exeception('unit override error')
if square_pulse2.amplitude3.unit != 'v label 2':
    raise Exeception('unit override 2 error')

no_type = {
    'amplitude2': {
        'value': 0.5,
        'unit': 'v label 2'
    },
    'vHome': {
        'unit': 'v label 3',
        "label": 'Default voltage point during the sequence',
        'elements': {
            'gate_1': 0,
            'gate_2': 0,
            'gate_3': 0,
            'gate_4': 0,
        }
    },
}

square_pulse3 = SquarePulse(dummy_sequence, 'no_type', dummy_device, no_type)
