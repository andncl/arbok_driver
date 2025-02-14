import os
import tempfile

from arbok_driver import ArbokDriver, Sample, ReadSequence
from arbok_driver.measurement import Measurement
from types import SimpleNamespace

from all_the_qua import AllTheQua
from arbok_driver.parameter_types import Voltage

# get some parameters which we can sweep
sequence_config = {
    'parameters': {
        'v_set_home': {
            'type': Voltage,
            'elements': { 'SET1': 0, 'P1': 0, 'J1': 0, 'P2': 0 }
        },
    },
}

sample = SimpleNamespace(**{ 'elements' : [ 'SET1', 'P1', 'J1', 'P2' ], 'divider_config' : {} })
arbok_driver = ArbokDriver('arbok_driver', sample)

measurement = Measurement(
    parent = arbok_driver,
    name = 'measurement_name',
    sample = sample,
    sequence_config = sequence_config
)

atq = AllTheQua(measurement, 'atq', sample)


import numpy as np
v_start = 0.1
v_range = np.linspace(-v_start, v_start, 100)
v_arr = np.array([0, 1, 10, 100], dtype=float)


sweeps = [{'v_set_home_P1': v_range},
        {'v_set_home_J1': v_arr},
        {'v_set_home_P2': 32},
        ]

measurement.set_sweeps(*sweeps)

tmp_dir = tempfile.gettempdir()
file_path = os.path.join(tmp_dir, "arbok_test", "sweep_test.qua")
os.makedirs(os.path.dirname(file_path), exist_ok=True)

measurement.print_qua_program_to_file(file_path)
