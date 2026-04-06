
# Single QUA script generated at 2026-04-05 07:48:59.254730
# QUA library version: 1.2.5


from qm import CompilerOptionArguments
from qm.qua import *

with program() as prog:
    v1 = declare(fixed, )
    v2 = declare(int, value=0)
    v3 = declare(int, )
    with infinite_loop_():
        pause()
        assign(v2, 0)
        assign(v3, 0)
        with while_((v3<10)):
            assign(v1, (0.0+Cast.mul_fixed_by_int(0.00999,v3)))
            align()
            align("gate_1", "gate_2", "gate_3", "gate_4")
            align("gate_1", "gate_2", "gate_3", "gate_4")
            play("unit_ramp"*amp(0.2), "gate_1", duration=20)
            play("unit_ramp"*amp(-0.1), "gate_2", duration=20)
            play("unit_ramp"*amp((v1-0)), "gate_3", duration=20)
            play("unit_ramp"*amp(0.25), "gate_4", duration=20)
            align("gate_1", "gate_2", "gate_3", "gate_4")
            wait(100, "gate_1", "gate_2", "gate_3", "gate_4")
            align("gate_1", "gate_2", "gate_3", "gate_4")
            play("unit_ramp"*amp(-0.2), "gate_1", duration=20)
            play("unit_ramp"*amp(0.1), "gate_2", duration=20)
            play("unit_ramp"*amp((0-v1)), "gate_3", duration=20)
            play("unit_ramp"*amp(-0.25), "gate_4", duration=20)
            align("gate_1", "gate_2", "gate_3", "gate_4")
            align()
            assign(v2, (v2+1))
            r0 = declare_stream()
            save(v2, r0)
            align()
            assign(v3, (v3+1))
    with stream_processing():
        r0.buffer(1).save("qm_driver_meas_scaled_square_shots")

config = None

loaded_config = None

