from arbok_driver.parameter_types import Voltage, Time, String
from arbok_driver.examples.sub_sequences import SquarePulse

square_pulse_config = {
    'sequence': SquarePulse,
    'parameters': {
        'amplitude': {
            'type': Voltage,
            'value': 0.1,
        },
        't_square_pulse': {
            'type': Time,
            'value': 100,
        },
        't_ramp': {
            'type': Time,
            'value': 200,
        },
        'element': {
            'type': String,
            'value': 'gate_1',
        }
    }
}
