"""Module containing configurations for SquarePulse(Scalable) classes"""
from arbok_driver.parameter_types import (
    Amplitude, List, String, Time, Voltage
)

from arbok_driver.examples.sub_sequences import SquarePulse, SquarePulseScalable

square_pulse_conf = {
    "sequence": SquarePulse,
    "parameters": {
        'amplitude': {'type': Amplitude, 'value': 1.5},
        'element': {'type': String, 'value': 'P1'},
        't_ramp': {'type': Time, 'value': int(100)},
        't_square_pulse': {'type': Time, 'value': int(1000)}
    }
}

square_pulse_scalable_conf = {
    "sequence": SquarePulseScalable,
    "parameters": {
        'amplitude': {'type': Amplitude, 'value': 1.5},
        't_ramp': {'type': Time, 'value': int(100)},
        'sticky_elements': {'type': List, 'value': ['P1', 'P2', 'P3']},
        't_square_pulse': {'type': Time, 'value': int(1000)},
        'v_home': {
            'type': Voltage,
            'elements': {
                'P1': 0.0,
                'P2': 0.0,
                'P3': 0.0
            }
        },
        'v_square': {
            'type': Voltage,
            'elements': {
                'P1': 0.1,
                'P2': -0.2,
                'P3': 0.2
            }
        }
    }
}