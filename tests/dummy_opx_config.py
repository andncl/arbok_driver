import numpy as np

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

unit_ramp_devices = np.linspace(0, 0.5, 20).tolist()

dummy_qua_config = {
    'version': 1,
    'controllers': {
        'con1': {
            'type': 'opx1',
            'analog_outputs': {
                1: {'offset': 0},
                2: {'offset': 0},
            },
            'digital_outputs': {
                1: {},
                2: {},
            },
            'analog_inputs': {
                1: {'offset': 0},
                2: {'offset': 0},
            },
        }
    },
    'elements': {
        'E1': {
            'singleInput': {
                'port': ('con1', 1)},
            'hold_offset': {'duration': 100},
            'operations': {
                'const': 'const_pulse',
                'step':'step_pulse',
                'unit_ramp_20ns': 'unit_ramp_pulse_20ns',
            },
        },
        'E2': {
            'singleInput': {
                'port': ('con1', 2)},
            'hold_offset': {'duration': 100},
            'operations': {
                'const': 'const_pulse',
                'step':'step_pulse',
                'unit_ramp_20ns': 'unit_ramp_pulse_20ns',
            },
        },
    },
    'pulses': {
        'const_pulse': {
            'operation': 'control',
            'length': 1000,
            'waveforms': {'single': 'const_wf'}
        },
        "step_pulse": {
            "operation": "control",
            "length": 1000,
            "waveforms": {"single": "step_wf"},
        },
        'unit_ramp_pulse_20ns': {
            'operation': 'control',
            'length': 20,
            'waveforms': {'single': 'unit_ramp_wf_20ns'},
        },
    },
    'waveforms': {
        'const_wf': {
            'type': 'constant',
            'device': 0.49
        },
        "step_wf": {
            'type': 'constant',
            'device': 0.5
            },
        'unit_ramp_wf_20ns':{
            'type':'arbitrary',
            'devices': unit_ramp_devices
        }
    },
    'digital_waveforms': {
        'ON': {
            'devices': [(1, 0)]
        },
    },
    'integration_weights': {
        "cos": {
            "cosine": [(1.0, 1000)],
            "sine": [(0.0, 1000)]
        },
        "sin": {
            "cosine": [(0.0, 1000)],
            "sine": [(1.0, 1000)],
        },
    },
    'mixers': {
        'mixer_qubit': [
            {'intermediate_frequency': 50e6, 'lo_frequency': 5e9,
            'correction': [1.0, 0.0, 0.0, 1.0]}
        ],
        'mixer_RR': [
            {'intermediate_frequency': 50e6, 'lo_frequency': 5e9,
            'correction': [1.0, 0.0, 0.0, 1.0]}
        ],
    }
}
