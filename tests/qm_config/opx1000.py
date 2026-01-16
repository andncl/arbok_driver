"""
QUA-Config supporting OPX1000
"""

sampling_rate = int(1e9) # Hz
T = 5e-3 # s

config = {
    "version": 1,
    "controllers": {
        'con1': {
            "type": "opx1000",
            "fems": {
                1: {
                    "type": "LF",
                    "analog_outputs": {
                        1: {
                            "offset": 0.0,
                            "output_mode": "direct",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "mw",
                        },
                        2: {
                            "offset": 0.0,
                            "output_mode": "direct",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "mw",
                        },
                        3: {
                            "offset": 0.0,
                            "output_mode": "direct",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "mw",
                        },                        
                        4: {
                            "offset": 0.0,
                            "output_mode": "direct",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "mw",
                        },
                    },
                    "digital_outputs": {},
                    "analog_inputs": {
                        1: {"offset": 0.0, "gain_db": 0, "sampling_rate": sampling_rate},
                        2: {"offset": 0.0, "gain_db": 0, "sampling_rate": sampling_rate},
                    },
                }
            },
        }
    },
    "elements": {
        "element_a": {
            "singleInput": {
                "port": ("con1", 1, 1),
            },
            "operations": {
                "cw": "const_pulse",
            },
        },
        "element_b": {
            "singleInput": {
                "port": ("con1", 1, 2),
            },
            "operations": {
                "readout": "readout_pulse",
            },
            "outputs": {
                "out1": ("con1", 1, 1),
                "out2": ("con1", 1, 2),
            },
            "time_of_flight": 180,
            "smearing": 0,
        },
        "element_c": {
            "singleInput": {
                "port": ("con1", 1, 3),
            },
            "operations": {
                "cw": "const_pulse",
            },
        },
        "element_d": {
            "singleInput": {
                "port": ("con1", 1, 4),
            },
            "operations": {
                "cw": "const_pulse",
            },
        },
    },
    "pulses": {
        "const_pulse": {
            "operation": "control",
            "length": 100,
            "waveforms": {
                "single": "const_wf",
            },
        },
        "readout_pulse": {
            "operation": "measurement",
            "length": int(T*1e9), # ns
            "waveforms": {
                "single": "readout_wf",
            },
            "digital_marker": "ON",
        },
    },
    "waveforms": {
        "const_wf": {"type": "constant", "device": 0.249},
        "readout_wf": {"type": "constant", "device": 0}
    },
    "digital_waveforms": {
        "ON": {"devices": [(1, 0)]},
    },
}
