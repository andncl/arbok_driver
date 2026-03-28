"""Module containing a minimal voltage divider config """
opx_scale = 2
divider_config = {
    'P1': {
        'division': 3*opx_scale,
    },
    'P2': {
        'division': 3*opx_scale,
    },
    'P3': {
        'division': 3*opx_scale,
    },
    'gate_2': {
        'division': 1*opx_scale,
    },
    'readout_element': {
        'division': 1*opx_scale
    }
}
