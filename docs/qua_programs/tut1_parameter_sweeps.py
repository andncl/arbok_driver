
# Single QUA script generated at 2026-03-19 06:08:17.506791
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
        with while_((v3<5)):
            assign(v1, (0.1+Cast.mul_fixed_by_int(0.224775,v3)))
            align()
            align()
            play("ramp"*amp(v1), "gate_1", duration=20)
            wait(50, "gate_1")
            play("ramp"*amp(v1), "gate_1", duration=20)
            align()
            assign(v2, (v2+1))
            r0 = declare_stream()
            save(v2, r0)
            align()
            assign(v3, (v3+1))
    with stream_processing():
        r0.buffer(1).save("qm_driver_dummy_squence_shots")

config = None

loaded_config = None

