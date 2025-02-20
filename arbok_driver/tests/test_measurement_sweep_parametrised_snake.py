#!/usr/bin/env python
import os
import tempfile

from arbok_driver import ArbokDriver, Sample, ReadSequence
from arbok_driver.measurement import Measurement
from types import SimpleNamespace

from all_the_qua import AllTheQua
from arbok_driver.parameter_types import Voltage
import qcodes as qc
from qm_config.opx1000 import config

# get some parameters which we can sweep
measurement_config = {
    'parameters': {
        'v_set_home': {
            'type': Voltage,
            'elements': { 'output': 0, 'loopback': 0 }
        },
    },
}

sample = SimpleNamespace(**{'elements' : [ 'output', 'loopback' ], 'divider_config' : {} })
sample.config = config
arbok_driver = ArbokDriver('arbok_driver', sample)

measurement = Measurement(
    parent = arbok_driver,
    name = 'measurement_name',
    sample = sample,
    sequence_config = measurement_config
)

from arbok_driver.tests.var_readout import VarReadout
available_abstract_readouts = {
    'var_readout': VarReadout
}
from arbok_driver.tests.var_readout_config import var_readout_config
atq = AllTheQua(measurement, 'atq', sample, var_readout_config, available_abstract_readouts = available_abstract_readouts)

measurement.qc_measurement_name = 'sweep_measurement'
measurement.qc_experiment = qc.dataset.load_or_create_experiment('experiment.name', 'sample.name')

import numpy as np
v_start = 0.1
v_range = np.linspace(-v_start, v_start, 100)
v_arr = np.array([0, 1, 10, 100], dtype=float)

# sweeps = [{'v_set_home_P1': v_range, 'snake': True},
#         {'v_set_home_J1': v_arr},
#         {'v_set_home_P2': 32, 'snake': False},
#         ]
sweeps = [
    {'v_set_home_output': v_range, 'snake': True},
        ]

measurement.set_sweeps(*sweeps)
# measurement.register_gettables(keywords=[('atq_stream')])

tmp_dir = tempfile.gettempdir()
file_path = os.path.join(tmp_dir, "arbok_test", "sweep_param_snake_test.qua")
os.makedirs(os.path.dirname(file_path), exist_ok=True)

measurement.print_qua_program_to_file(file_path)

# sweep_list_arg = [{arbok_driver.iteration: np.arange(1)}]
# run_loop = measurement.get_measurement_loop_function(sweep_list_arg)

# arbok_driver.connect_opx(host_ip = '192.168.88.254', port = 9510, log_level = 'DEBUG')
# measurement.compile_qua_and_run()

# try:
#     dataset = run_loop()
# except KeyboardInterrupt:
#     print('Dumping execution report:')
#     arbok_driver.qm_job.execution_report()
