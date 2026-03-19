
# Single QUA script generated at 2026-03-19 06:08:17.748244
# QUA library version: 1.2.5


from qm import CompilerOptionArguments
from qm.qua import *

with program() as prog:
    v1 = declare(fixed, )
    v2 = declare(int, )
    a1 = declare(int, value=[10, 20, 30, 40])
    v3 = declare(int, )
    a2 = declare(int, value=[10, 20, 30, 40])
    v4 = declare(int, value=0)
    v5 = declare(int, )
    v6 = declare(int, )
    with infinite_loop_():
        pause()
        assign(v4, 0)
        assign(v5, 0)
        with while_((v5<5)):
            assign(v1, (0.1+Cast.mul_fixed_by_int(0.224775,v5)))
            align()
            assign(v6, 0)
            with while_((v6<4)):
                assign(v2, a1[v6])
                assign(v3, a2[v6])
                align()
                play("ramp"*amp(v1), "gate_1", duration=v3)
                wait(v2, "gate_1")
                play("ramp"*amp(v1), "gate_1", duration=v3)
                align()
                assign(v4, (v4+1))
                r0 = declare_stream()
                save(v4, r0)
                align()
                assign(v6, (v6+1))
            assign(v5, (v5+1))
    with stream_processing():
        r0.buffer(1).save("qm_driver_dummy_squence_shots")

config = None

loaded_config = None

