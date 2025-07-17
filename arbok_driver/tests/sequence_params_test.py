import pytest
import tempfile

from arbok_driver import SubSequence

import logging
logging.basicConfig(
    filename = 'logs/sequence_params_test.txt',
    filemode = 'w',
    encoding = 'utf-8',
    level = logging.DEBUG
)

square_conf2 = {
    'sticky_elements': {
        'value': ['gate_1', 'gate_2', 'gate_3', 'gate_4'],
        'unit': 'gate label'
    },
    'vHome': {
        'unit': 'V',
        "label": 'Default voltage point during the sequence',
        'elements': {
            'gate_1': 0,
            'gate_2': 0,
            'gate_3': 0,
            'gate_4': 0,
        }
    },
    'vSquare': {
        'unit': 'V',
        "label": 'Voltage amplitude of square pulse',
        'elements': {
            'gate_1': 0.1,
            'gate_2': -0.05,
            'gate_3': 0.08,
            'gate_4': 0.25,
        }
    },
    't_square_pulse': {
        'value': 100,
        'unit': 'cycles'
    },
    'ramp_time': {
        'value': 20,
        'unit': 'cycles'
    },
}


expected_output = """square_conf2:
	parameter      value
--------------------------------------------------------------------------------
IDN             :	None 
ramp_time       :	20 (cycles)
sticky_elements :	['gate_1', 'gate_2', 'gate_3', 'gate_4'] (gate label)
t_square_pulse  :	100 (cycles)
vHome_gate_1    :	0 (V)
vHome_gate_2    :	0 (V)
vHome_gate_3    :	0 (V)
vHome_gate_4    :	0 (V)
vSquare_gate_1  :	0.1 (V)
vSquare_gate_2  :	-0.05 (V)
vSquare_gate_3  :	0.08 (V)
vSquare_gate_4  :	0.25 (V)"""

def compare_multiline_strings(string1, string2):
    lines1 = string1.strip().splitlines()
    lines2 = string2.strip().splitlines()

    # Ensure both strings have the same number of lines
    assert len(lines1) == len(lines2), "Number of lines mismatch"

    for line_num, (line1, line2) in enumerate(zip(lines1, lines2), start=1):
        assert line1 == line2, f"Line {line_num} differs:\n'{line1}'\nvs\n'{line2}'"

def test_parameters(dummy_device, capfd) -> None:
    sequenceBase = SubSequence('square_conf2', dummy_device, square_conf2)
    sequenceBase.print_readable_snapshot()
    out, err = capfd.readouterr()
    compare_multiline_strings(out, expected_output)
