# #!/usr/bin/env python
# from arbok_driver import ArbokDriver, Measurement, SubSequence
# from arbok_driver.parameter_types import Voltage, Time, String
# import numpy as np

# from helpers import qua_program_trim_gen_time, compare_qua_programs

# from qm import qua

# class SquarePulse(SubSequence):
#     """
#     Class containing parameters and sequence for a simple square pulse
#     """

#     def qua_sequence(self):
#         """Macro that will be played within the qua.program() context"""
#         qua.align()
#         qua.play('ramp'*qua.amp(self.amplitude()), self.element(), duration = self.ramp_time())
#         qua.wait(self.t_square_pulse(), self.element())
#         qua.play('ramp'*qua.amp(-self.amplitude()), self.element(), duration = self.ramp_time())

# square_conf = {
#     'amplitude': {
#         'value': 0.5,
#         'type': Voltage,
#     },
#     't_square_pulse': {
#         'value': 100,
#         'type': Time
#     },
#     'element': {
#         'type': String,
#         'value': 'gate_1',
#         'unit': 'gate label'
#     },
#     'ramp_time': {
#         'value': 20,
#         'type': Time
#     },
# }

# from arbok_driver import Device
# from arbok_driver.tests.dummy_opx_config import dummy_qua_config, divider_config

# dummy_device = Device('dummy_device', dummy_qua_config, divider_config)
# qm_driver = ArbokDriver('qm_driver', dummy_device)
# dummy_measurement = Measurement(qm_driver, 'dummy_measurement', dummy_device)

# square_pulse = SquarePulse(dummy_measurement, 'square_pulse', dummy_device, square_conf)

# dummy_measurement.set_sweeps(
#     {
#         square_pulse.amplitude: np.linspace(0.1, 1, 5)
#     }
# )

# # dummy_measurement.reset()
# qua_program = dummy_measurement.get_qua_program_as_str()
# qp1 = qua_program_trim_gen_time(qua_program)

# dummy_measurement.reset()

# qua_program2 = dummy_measurement.get_qua_program_as_str()
# qp2 = qua_program_trim_gen_time(qua_program2)

# line_differences = compare_qua_programs(qp1, qp2)
# if len(line_differences):
#     raise Exception("Programes should have been identical, but weren't")
