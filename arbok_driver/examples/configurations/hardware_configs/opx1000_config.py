"""
This file contains the quantum machine configuration for the nova sample.
"""
import os
import numpy as np

def round_to_multiple(x, base=4):
    return int(base * round(float(x)/base))

### CONSTANTS
UNIT_AMP = 0.4999
UNIT_AMP_AMPLIFIED = 2.4999

UNIT_RAMP_PULSE_DURATION = int(20)
MEASUREMENT_PULSE_DURATION = int(50e3) # 100e3
NORMALIZATION_FACTOR = MEASUREMENT_PULSE_DURATION/100e3
CONST_INTEGRATION_WEIGHT = 0.1/NORMALIZATION_FACTOR

ESR_CHIRP_LENGTH = int(100e3) # 100e3
MIN_PULSE_LENGTH =int(100)

path = os.path.dirname(os.path.abspath(__file__)) + '/'

LO_Q1 = int(13.959e9)
LO_Q2 = int(13.959e9)
LO_Q3 = int(13.959e9)
LO_Q4 = int(13.959e9)
LO_Q5 = int(13.959e9)
LO_Q6 = int(13.959e9)
LO_Q7 = int(13.959e9)
LO_Q8 = int(13.959e9)

IQampQ1 = 0.2
IQamp_max = 0.2

### CONTROLLERS
con1 = 'con1'

mw_fem = 1
lf_fem1 = 2
lf_fem2 = 4
lf_fem3 = 5
lf_fem4 = 7

sampling_rate = int(1e9)


import random

qubits = [f"Q{i}" for i in range(1, 13)]

# Larmor frequencies: 1e6 to 100e6 (ints)
larmor_freqs = {
    q: random.randint(int(1e6), int(100e6))
    for q in qubits
}

# Sideband (keeping your single entry)
sideband_freqs = {
    "qe1": random.randint(int(1e6), int(100e6))
}

# 2π times: 1e2 to 1e3 (floats or ints depending on your needs)
t_2pi_times = {  # in ns
    q: random.uniform(1e2, 1e3)
    for q in qubits
}

# Amplitudes: 0.8 to 1.0
amp_x_gate = {
    q: random.uniform(0.8, 1.0)
    for q in qubits
}

opx1000_config = {
    #'version': 1,
    'controllers': {
        con1: {
            "type": "opx1000",
            "fems": {
                mw_fem: {
                    "type": "MW",
                    "analog_outputs": {
                        2: {
                                #"sampling_rate": sampling_rate,
                                "band": 3,
                                "full_scale_power_dbm": -10,
                                "upconverters": {
                                    1: {"frequency": int(8.4e9)},
                                },
                            },
                    },
                    "digital_outputs": {},
                },
                lf_fem1: {
                    "type": "LF",
                    "analog_outputs": {
                        1: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        2: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        3: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        4: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        5: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        6: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        7: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        8: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                    },
                    "digital_outputs": {
                        1: {},
                        2: {},
                        3: {},
                        4: {},
                        5: {},
                        6: {},
                        7: {},
                        8: {},
                    },
                    'analog_inputs': {
                        1: {'offset': 0},  # nothing
                        2: {'offset': 0},  # nothing
                    },
                },
                lf_fem2: {
                    "type": "LF",
                    "analog_outputs": {
                        1: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        2: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        3: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        4: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        5: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        6: {
                            "offset": 0.5,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        7: {
                            "offset": 0.5,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        8: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                    },
                    "digital_outputs": {
                        1: {},
                        2: {},
                        3: {},
                        4: {},
                        5: {},
                        6: {},
                        7: {},
                        8: {},
                    },
                    'analog_inputs': {
                        1: {'offset': 0},  # nothing
                        2: {'offset': 0},  # nothing
                    },
                },
                lf_fem3: {
                    "type": "LF",
                    "analog_outputs": {
                        1: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        2: {
                            "offset": 0.4,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        3: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        4: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        5: {
                            "offset": 0.0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        6: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        7: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        8: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                    },
                    "digital_outputs": {
                        1: {},
                        2: {},
                        3: {},
                        4: {},
                        5: {},
                        6: {},
                        7: {},
                        8: {},
                    },
                    'analog_inputs': {
                        1: {'offset': 0},  # nothing
                        2: {'offset': 0},  # nothing
                    },
                },
                lf_fem4: {
                    "type": "LF",
                    "analog_outputs": {
                        1: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        2: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        3: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        4: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        5: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        6: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        7: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                        8: {
                            "offset": 0,
                            "output_mode": "amplified",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "pulse",
                        },
                    },
                    "digital_outputs": {
                        1: {},
                        2: {},
                        3: {},
                        4: {},
                        5: {},
                        6: {},
                        7: {},
                        8: {},
                    },
                    'analog_inputs': {
                        1: {'offset': 0},  # nothing
                        2: {'offset': 0},  # nothing
                    },
                },
            },
        }
    },
    'elements': {
        'P1': {
            'singleInput': {'port': (con1, lf_fem3, 1)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P2': {
            'singleInput': {'port': (con1, lf_fem4, 4)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P3': {
            'singleInput': {'port': (con1, lf_fem4, 3)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P4': {
            'singleInput': {'port': (con1, lf_fem4, 2)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P5': {
            'singleInput': {'port': (con1, lf_fem4, 1)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P6': {
            'singleInput': {'port': (con1, lf_fem1, 5)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P7': {
            'singleInput': {'port': (con1, lf_fem1, 6)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P8': {
            'singleInput': {'port': (con1, lf_fem1, 7)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P9': {
            'singleInput': {'port': (con1, lf_fem1, 8)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P10': {
            'singleInput': {'port': (con1, lf_fem4, 2)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P11': {
            'singleInput': {'port': (con1, lf_fem2, 6)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'P12': {
            'singleInput': {'port': (con1, lf_fem2, 7)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },



       'J1': {
        'singleInput': {'port': (con1, lf_fem1, 1)},
        'sticky': {
            'analog': True, 
            'digital': False, 
            'duration': 100
        },
        'operations': {
            'unit_ramp': 'unit_ramp_pulse_2_5',
        },
        },

        'J2': {
            'singleInput': {'port': (con1, lf_fem1, 2)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'J3': {
            'singleInput': {'port': (con1, lf_fem1, 3)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'J4': {
            'singleInput': {'port': (con1, lf_fem1, 4)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'J5': {
            'singleInput': {'port': (con1, lf_fem2, 1)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'J6': {
            'singleInput': {'port': (con1, lf_fem2, 2)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'J7': {
            'singleInput': {'port': (con1, lf_fem2, 3)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'J8': {
            'singleInput': {'port': (con1, lf_fem3, 7)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'J9': {
            'singleInput': {'port': (con1, lf_fem3, 4)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'J10': {
            'singleInput': {'port': (con1, lf_fem3, 3)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'J11': {
            'singleInput': {'port': (con1, lf_fem3, 2)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
            },
        },

        'SET1': {
            'singleInput': {
                'port': (con1, lf_fem2, 8)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 400
            },
            'outputs': {
                'output1': (con1, lf_fem2, 1)
            },
            'digitalInputs':{
                'digital_input1':{
                    'port': (con1, lf_fem2, 1),
                    'delay': 24,
                    'buffer': 0
                    }
               },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
                'step':'stepPulse',
                'measure': 'measure_pulse',
                'measure_1us': 'measure_pulse_1us',
            },
            'time_of_flight': 180,
            'smearing': 0,
            'intermediate_frequency': 0,
        },

        'SET2': {
            'singleInput': {
                'port': (con1, lf_fem3, 8)},
            'sticky':{
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'outputs': {
                'output1': (con1, lf_fem3, 1)
            },
            'digitalInputs':{
                'digital_input1':{
                    'port': (con1, lf_fem3, 1),
                    'delay': 24,
                    'buffer': 0
                    }
               },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
                'step':'stepPulse',
                'measure': 'measure_pulse',
                'measure_1us': 'measure_pulse_1us',
            },
            'time_of_flight': 180,
            'smearing': 0,
            'intermediate_frequency': 0,
        },

        'SET3': {
            'singleInput': {'port': (con1, lf_fem2, 4)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'outputs': {
                'output1': (con1, lf_fem2, 2)
            },
            'digitalInputs':{
                'digital_input1':{
                    'port': (con1, lf_fem2, 2),
                    'delay': 24,
                    'buffer': 0
                    }
               },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
                'step':'stepPulse',
                'measure': 'measure_pulse',
                'measure_1us': 'measure_pulse_1us',
                'measure_1ms': 'measure_pulse_1ms',
            },
            'time_of_flight': 180,
            'smearing': 0,
            'intermediate_frequency': 0,
        },

        'SET4': {
            'singleInput': {'port': (con1, lf_fem3, 6)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'outputs': {
                'output1': (con1, lf_fem3, 2)
            },
            'digitalInputs':{
                'digital_input1':{
                    'port': (con1, lf_fem3, 2),
                    'delay': 24,
                    'buffer': 0
                    }
               },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
                'step':'stepPulse',
                'measure': 'measure_pulse',
                'measure_1us': 'measure_pulse_1us',
                'measure_1ms': 'measure_pulse_1ms',
            },
            'time_of_flight': 180,
            'smearing': 0,
            'intermediate_frequency': 0,
        },

        'SET5': {
            'singleInput': {'port': (con1, lf_fem4, 5)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'outputs': {
                'output1': (con1, lf_fem4, 1)
            },
            'digitalInputs':{
                'digital_input1':{
                    'port': (con1, lf_fem4, 1),
                    'delay': 24,
                    'buffer': 0
                    }
               },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
                'step':'stepPulse',
                'measure': 'measure_pulse',
                'measure_1us': 'measure_pulse_1us',
                'measure_1ms': 'measure_pulse_1ms',
            },
            'time_of_flight': 180,
            'smearing': 0,
            'intermediate_frequency': 0,
        },

        'SET6': {
            'singleInput': {'port': (con1, lf_fem4, 8)},
            'sticky': {
                'analog': True, 
                'digital': False, 
                'duration': 100
            },
            'outputs': {
                'output1': (con1, lf_fem4, 2)
            },
            'digitalInputs':{
                'digital_input1':{
                    'port': (con1, lf_fem4, 2),
                    'delay': 24,
                    'buffer': 0
                    }
               },
            'operations': {
                'unit_ramp': 'unit_ramp_pulse_2_5',
                'step':'stepPulse',
                'measure': 'measure_pulse',
                'measure_1us': 'measure_pulse_1us',
                'measure_1ms': 'measure_pulse_1ms',
            },
            'time_of_flight': 180,
            'smearing': 0,
            'intermediate_frequency': 0,
        },

        "qe1": {
            'mixInputs': {
                'I': (con1, lf_fem3, 5),
                'Q': (con1, lf_fem3, 7),
                'lo_frequency': LO_Q1,
                'mixer': 'mixer_qe1'
            },
            'digitalInputs': {
                "switch1": {
                    "port": (con1, lf_fem3, 1),
                    "delay": 76,
                    "buffer": 4,
                },
            },
            'intermediate_frequency': sideband_freqs['qe1'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q1_pi_pulse',
                'control_pi2': 'ESR_Q1_pi2_pulse',
                'control_minus_pi2': 'ESR_Q1_pi2_pulse_minus',

            },
        },

        'Q1': {
            # MWInput corresponds to an OPX physical output port
            "MWInput": {
                "port": (con1, mw_fem, 2),
                "upconverter": 1,
            },
            'intermediate_frequency': larmor_freqs['Q1'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q1_pi_pulse',
                'control_pi2': 'ESR_Q1_pi2_pulse',
                'control_minus_pi2': 'ESR_Q1_pi2_pulse_minus',

            },
        },
        'Y1': {
            "MWInput": {
                "port": (con1, mw_fem, 2),
                "upconverter": 1,
            },
            'intermediate_frequency': larmor_freqs['Q1'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q1_pi_pulse',
                'control_pi2': 'ESR_Q1_pi2_pulse',
                'control_minus_pi2': 'ESR_Q1_pi2_pulse_minus',

            },
        },
        'Q2': {
            "MWInput": {
                "port": (con1, mw_fem, 2),
                "upconverter": 1,
            },
            'intermediate_frequency': larmor_freqs['Q2'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q2_pi_pulse',
                'control_pi2': 'ESR_Q2_pi2_pulse',
                'control_minus_pi2': 'ESR_Q2_pi2_pulse_minus',

            },
        },
        'Y2': {
            "MWInput": {
                "port": (con1, mw_fem, 2),
                "upconverter": 1,
            },
            'intermediate_frequency': larmor_freqs['Q2'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q2_pi_pulse',
                'control_pi2': 'ESR_Q2_pi2_pulse',
                'control_minus_pi2': 'ESR_Q2_pi2_pulse_minus',

            },
        },
        'Q3': {
            "MWInput": {
                "port": (con1, mw_fem, 2),
                "upconverter": 1,
            },
            'intermediate_frequency': larmor_freqs['Q3'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q3_pi_pulse',
                'control_pi2': 'ESR_Q3_pi2_pulse',
                'control_minus_pi2': 'ESR_Q3_pi2_pulse_minus',

            },
        },
        'Q4': {
            "MWInput": {
                "port": (con1, mw_fem, 2),
                "upconverter": 1,
            },
            'intermediate_frequency': larmor_freqs['Q4'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q4_pi_pulse',
                'control_pi2': 'ESR_Q4_pi2_pulse',
                'control_minus_pi2': 'ESR_Q4_pi2_pulse_minus',

            },
        },
        'Q5': {
            "MWInput": {
                "port": (con1, mw_fem, 2),
                "upconverter": 1,
            },
            'intermediate_frequency': larmor_freqs['Q5'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q5_pi_pulse',
                'control_pi2': 'ESR_Q5_pi2_pulse',
                'control_minus_pi2': 'ESR_Q5_pi2_pulse_minus',

            },
        },
        'Q6': {
            "MWInput": {
                "port": (con1, mw_fem, 2),
                "upconverter": 1,
            },
            'intermediate_frequency': larmor_freqs['Q6'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q6_pi_pulse',
                'control_pi2': 'ESR_Q6_pi2_pulse',
                'control_minus_pi2': 'ESR_Q6_pi2_pulse_minus',

            },
        },
        'Q7': {
            "MWInput": {
                "port": (con1, mw_fem, 2),
                "upconverter": 1,
            },
            'intermediate_frequency': larmor_freqs['Q7'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q7_pi_pulse',
                'control_pi2': 'ESR_Q7_pi2_pulse',
                'control_minus_pi2': 'ESR_Q7_pi2_pulse_minus',

            },
        },
        'Q8': {
            "MWInput": {
                "port": (con1, mw_fem, 2),
                "upconverter": 1,
            },
            'intermediate_frequency': larmor_freqs['Q8'],
            'operations': {
                'control': 'ESR_const_pulse',
                'chirp': 'ESR_chirp_pulse',
                'control_pi': 'ESR_Q8_pi_pulse',
                'control_pi2': 'ESR_Q8_pi2_pulse',
                'control_minus_pi2': 'ESR_Q8_pi2_pulse_minus',

            },
        },
    },

    'pulses': {
        'trigger_pulse':{
            'operation': 'measurement',
            'length':1000,
            'digital_marker': 'ON',
        },

        'measure_pulse': {
            'operation': 'measurement',
            'length': MEASUREMENT_PULSE_DURATION,
            'waveforms': {
                    'single': 'zero_wf'
                },
            'digital_marker': 'ON',
            'integration_weights': {
                'x': 'cos',
                'y': 'sin',
                'x_const': 'x_const',
                'y_const': 'y_const',
                'x_test': 'cos_test',
                'y_test': 'sin_test'
                }
        },
        'measure_pulse_1us': {
            'operation': 'measurement',
            'length': int(1e3),
            'waveforms': {
                    'single': 'zero_wf'
                },
            'digital_marker': 'ON',
            'integration_weights': {
                'x': 'cos',
                'y': 'sin',
                'x_const': 'x_const_1us',
                'y_const': 'y_const',
                'x_test': 'cos_test',
                'y_test': 'sin_test'
                }
        },
        'measure_pulse_1ms': {
            'operation': 'measurement',
            'length': int(1e6),
            'waveforms': {
                    'single': 'zero_wf'
                },
            'digital_marker': 'ON',
            'integration_weights': {
                'x_const_1ms': 'x_const_1ms',
                'y_const_1ms': 'y_const_1ms',
                }
        },
         'unit_ramp_pulse': {
            'operation': 'control',
            'length': UNIT_RAMP_PULSE_DURATION,
            'waveforms': {
                'single': 'unit_ramp_wf',
            }
        },
         'unit_ramp_pulse_2_5': {
            'operation': 'control',
            'length': UNIT_RAMP_PULSE_DURATION,
            'waveforms': {
                'single': 'unit_ramp_2_5_wf',
            }
        },
        "stepPulse": {
            "operation": "control",
            "length": 1000,
            "waveforms": {"single": "step_wf"},
        },
        "const_pulse": {
            "operation": "control",
            "length": int(10000),
            "waveforms": {
                "I": "const_wf",
                "Q": "zero_wf",
            },
        },
        'ESR_const_pulse': {
            'operation': 'control',
            'length': MIN_PULSE_LENGTH,
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf',
                'Q': 'max_amp_wf'
            }
        },
        'ESR_chirp_pulse': {
            'operation': 'control',
            'length': ESR_CHIRP_LENGTH,
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'q1_ctrl_wf',
                'Q': 'q1_ctrl_wf'
            }
        },
        'ESR_Q1_pi_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q1']/2),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q1',
                'Q': 'max_amp_wf_Q1'
            }
        },
        'ESR_Q1_pi2_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q1']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q1',
                'Q': 'max_amp_wf_Q1'
            }
        },
        'ESR_Q1_pi2_pulse_minus': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q1']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q1_minus',
                'Q': 'max_amp_wf_Q1_minus'
            }
        },
        'ESR_Q2_pi_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q2']/2),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q2',
                'Q': 'max_amp_wf_Q2'
            }
        },
        'ESR_Q2_pi2_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q2']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q2',
                'Q': 'max_amp_wf_Q2'
            }
        },
        'ESR_Q2_pi2_pulse_minus': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q2']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q2_minus',
                'Q': 'max_amp_wf_Q2_minus'
            }
        },
        'ESR_Q3_pi_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q3']/2),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q3',
                'Q': 'max_amp_wf_Q3'
            }
        },
        'ESR_Q3_pi2_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q3']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q3',
                'Q': 'max_amp_wf_Q3'
            }
        },
        'ESR_Q3_pi2_pulse_minus': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q3']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q3_minus',
                'Q': 'max_amp_wf_Q3_minus'
            }
        },
        'ESR_Q4_pi_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q4']/2),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q4',
                'Q': 'max_amp_wf_Q4'
            }
        },
        'ESR_Q4_pi2_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q4']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q4',
                'Q': 'max_amp_wf_Q4'
            }
        },
        'ESR_Q4_pi2_pulse_minus': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q4']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q4_minus',
                'Q': 'max_amp_wf_Q4_minus'
            }
        },
        'ESR_Q5_pi_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q5']/2),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q5',
                'Q': 'max_amp_wf_Q5'
            }
        },
        'ESR_Q5_pi2_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q5']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q5',
                'Q': 'max_amp_wf_Q5'
            }
        },
        'ESR_Q5_pi2_pulse_minus': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q5']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q5_minus',
                'Q': 'max_amp_wf_Q5_minus'
            }
        },
        'ESR_Q6_pi_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q6']/2),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q6',
                'Q': 'max_amp_wf_Q6'
            }
        },
        'ESR_Q6_pi2_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q6']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q6',
                'Q': 'max_amp_wf_Q6'
            }
        },
        'ESR_Q6_pi2_pulse_minus': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q6']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q6_minus',
                'Q': 'max_amp_wf_Q6_minus'
            }
        },
        'ESR_Q7_pi_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q7']/2),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q7',
                'Q': 'max_amp_wf_Q7'
            }
        },
        'ESR_Q7_pi2_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q7']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q7',
                'Q': 'max_amp_wf_Q7'
            }
        },
        'ESR_Q7_pi2_pulse_minus': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q7']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q7_minus',
                'Q': 'max_amp_wf_Q7_minus'
            }
        },
        'ESR_Q8_pi_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q8']/2),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q8',
                'Q': 'max_amp_wf_Q8'
            }
        },
        'ESR_Q8_pi2_pulse': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q8']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q8',
                'Q': 'max_amp_wf_Q8'
            }
        },
        'ESR_Q8_pi2_pulse_minus': {
            'operation': 'control',
            'length': round_to_multiple(t_2pi_times['Q8']/4),
            'digital_marker': 'ON',
            'waveforms': {
                'I': 'max_amp_wf_Q8_minus',
                'Q': 'max_amp_wf_Q8_minus'
            }
        },
        'constPulse': {
            'operation': 'control',
            'length': 10000,  # in ns
            'waveforms': {
                'I': 'const_wf',
                'Q': 'zero_wf',
            },
            'digital_marker': 'ON',
        },
    },

    'waveforms': {
        'zero_wf': {
            'type': 'constant',
            'sample': 0.0
        },
        "const_wf": {
            "type": "constant",
            "sample": 0.2
        },
        "step_wf": {
            'type': 'constant',
            'sample': UNIT_AMP
            },
        'unit_ramp_wf':{
            'type':'arbitrary',
            'samples': np.linspace(0, UNIT_AMP, UNIT_RAMP_PULSE_DURATION).tolist()
            },
        'unit_ramp_2_5_wf':{
            'type':'arbitrary',
            'samples': np.linspace(0, UNIT_AMP_AMPLIFIED, UNIT_RAMP_PULSE_DURATION).tolist()
            },
        'q1_ctrl_wf': {
            'type': 'constant',
            'sample': IQampQ1
        },
        'max_amp_wf': {
            'type': 'constant',
            'sample': IQamp_max
        },
        'max_amp_wf_Q1': {
            'type': 'constant',
            'sample': IQamp_max*amp_x_gate['Q1']
        },
        'max_amp_wf_Q1_minus': {
            'type': 'constant',
            'sample': -IQamp_max*amp_x_gate['Q1']
        },
        'max_amp_wf_Q2': {
            'type': 'constant',
            'sample': IQamp_max*amp_x_gate['Q2']
        },
        'max_amp_wf_Q2_minus': {
            'type': 'constant',
            'sample': -IQamp_max*amp_x_gate['Q2']
        },
        'max_amp_wf_Q3': {
            'type': 'constant',
            'sample': IQamp_max*amp_x_gate['Q3']
        },
        'max_amp_wf_Q3_minus': {
            'type': 'constant',
            'sample': -IQamp_max*amp_x_gate['Q3']
        },
        'max_amp_wf_Q4': {
            'type': 'constant',
            'sample': IQamp_max*amp_x_gate['Q4']
        },
        'max_amp_wf_Q4_minus': {
            'type': 'constant',
            'sample': -IQamp_max*amp_x_gate['Q4']
        },
        'max_amp_wf_Q5': {
            'type': 'constant',
            'sample': IQamp_max*amp_x_gate['Q5']
        },
        'max_amp_wf_Q5_minus': {
            'type': 'constant',
            'sample': -IQamp_max*amp_x_gate['Q5']
        },
        'max_amp_wf_Q6': {
            'type': 'constant',
            'sample': IQamp_max*amp_x_gate['Q6']
        },
        'max_amp_wf_Q6_minus': {
            'type': 'constant',
            'sample': -IQamp_max*amp_x_gate['Q6']
        },
        'max_amp_wf_Q7': {
            'type': 'constant',
            'sample': IQamp_max*amp_x_gate['Q7']
        },
        'max_amp_wf_Q7_minus': {
            'type': 'constant',
            'sample': -IQamp_max*amp_x_gate['Q7']
        },
        'max_amp_wf_Q8': {
            'type': 'constant',
            'sample': IQamp_max*amp_x_gate['Q8']
        },
        'max_amp_wf_Q8_minus': {
            'type': 'constant',
            'sample': -IQamp_max*amp_x_gate['Q8']
        },
    },

    'digital_waveforms': {
        'ON': {
            'samples': [(1, 0)]
        },
    },

    'integration_weights': {
        'cos': {
            'cosine': [(1, MEASUREMENT_PULSE_DURATION)],
            'sine': [(0, MEASUREMENT_PULSE_DURATION)],
        },
        'sin': {
            'cosine': [(0, MEASUREMENT_PULSE_DURATION)],
            'sine': [(1, MEASUREMENT_PULSE_DURATION)],
        },
        'x_const': {
            'cosine': [(CONST_INTEGRATION_WEIGHT, MEASUREMENT_PULSE_DURATION)],
            'sine': [(0, MEASUREMENT_PULSE_DURATION)],
        },
        'x_const_1us': {
            'cosine': [(1/1000, MEASUREMENT_PULSE_DURATION)],
            'sine': [(0, MEASUREMENT_PULSE_DURATION)],
        },
        'y_const': {
            'cosine': [(0, MEASUREMENT_PULSE_DURATION)],
            'sine': [(CONST_INTEGRATION_WEIGHT, MEASUREMENT_PULSE_DURATION)],
        },
        'x_const_1ms': {
            'cosine': [(CONST_INTEGRATION_WEIGHT, int(1e6))],
            'sine': [(0, int(1e6))],
        },
        'y_const_1ms': {
            'cosine': [(0, int(1e6))],
            'sine': [(CONST_INTEGRATION_WEIGHT, int(1e6))],
        },
    },
    'mixers': {
        'mixer_qe1': [
            {
                'intermediate_frequency': sideband_freqs['qe1'],
                'lo_frequency': LO_Q1,
                'correction': [1.0, 0.0, 0.0, 1.0]
            },
        ],
        'mixer_q1': [
            {
                'intermediate_frequency': larmor_freqs['Q1'],
                'lo_frequency': LO_Q1,
                'correction': [1.0, 0.0, 0.0, 1.0]
            },
        ],
        'mixer_y1': [
            {
                'intermediate_frequency': larmor_freqs['Q1'],
                'lo_frequency': LO_Q1,
                'correction': [0.0, 1.0, 1.0, 0.0]
            },
        ],
        'mixer_q2': [
            {
                'intermediate_frequency': larmor_freqs['Q2'],
                'lo_frequency': LO_Q2,
                'correction': [1.0, 0.0, 0.0, 1.0]
            },
        ],
        'mixer_y2': [
            {
                'intermediate_frequency': larmor_freqs['Q2'],
                'lo_frequency': LO_Q1,
                'correction': [0.0, 1.0, 1.0, 0.0]
            },
        ],
        'mixer_q3': [
            {
                'intermediate_frequency': larmor_freqs['Q3'],
                'lo_frequency': LO_Q3,
                'correction': [1.0, 0.0, 0.0, 1.0]
            },
        ],
        'mixer_q4': [
            {
                'intermediate_frequency': larmor_freqs['Q4'],
                'lo_frequency': LO_Q4,
                'correction': [1.0, 0.0, 0.0, 1.0]
            },
        ],
        'mixer_q5': [
            {
                'intermediate_frequency': larmor_freqs['Q5'],
                'lo_frequency': LO_Q5,
                'correction': [1.0, 0.0, 0.0, 1.0]
            },
        ],
        'mixer_q6': [
            {
                'intermediate_frequency': larmor_freqs['Q6'],
                'lo_frequency': LO_Q6,
                'correction': [1.0, 0.0, 0.0, 1.0]
            },
        ],
        'mixer_q7': [
            {
                'intermediate_frequency': larmor_freqs['Q7'],
                'lo_frequency': LO_Q7,
                'correction': [1.0, 0.0, 0.0, 1.0]
            },
        ],
        'mixer_q8': [
            {
                'intermediate_frequency': larmor_freqs['Q8'],
                'lo_frequency': LO_Q8,
                'correction': [1.0, 0.0, 0.0, 1.0]
            },
        ],
    }
}
