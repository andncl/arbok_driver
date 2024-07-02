
# Single QUA script generated at 2024-06-27 17:39:01.069504
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    v1 = declare(fixed, )
    v2 = declare(int, )
    v3 = declare(int, )
    v4 = declare(int, value=0)
    v5 = declare(int, )
    v6 = declare(int, )
    with infinite_loop_():
        pause()
        assign(v2, 10)
        assign(v3, 10)
        with for_(v5,0,(v5<4),(v5+1)):
            align()
            assign(v1, 0.1)
            with for_(v6,0,(v6<5),(v6+1)):
                align()
                align()
                play("ramp"*amp(v1), "gate_1", duration=v3)
                wait(v2, "gate_1")
                play("ramp"*amp((0-v1)), "gate_1", duration=v3)
                assign(v4, (v4+1))
                r1 = declare_stream()
                save(v4, r1)
                assign(v1, (v1+0.225))
            assign(v2, (v2+10))
            assign(v3, (v3+10))
    with stream_processing():
        r1.buffer(1).save("dummy_squence_shots")


config = None

loaded_config = None

