from arbok_driver.parameter_types import Voltage, Time, String

square_pulse_config = {
    'parameters': {
        'amplitude': {
            'type': Voltage,
            'value': 0.1,
        },
        't_square_pulse': {
            'type': Time,
            'value': 100,
        },
        'element': {
            'type': String,
            'value': 'gate_1',
        }
    }
}
