
# Single QUA script generated at 2024-06-27 17:39:00.985865
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    v1 = declare(fixed, )
    v2 = declare(int, value=0)
    v3 = declare(int, )
    with infinite_loop_():
        pause()
        assign(v1, 0.1)
        with for_(v3,0,(v3<5),(v3+1)):
            align()
            align()
            play("ramp"*amp(v1), "gate_1", duration=20)
            wait(50, "gate_1")
            play("ramp"*amp((0-v1)), "gate_1", duration=20)
            assign(v2, (v2+1))
            r1 = declare_stream()
            save(v2, r1)
            assign(v1, (v1+0.225))
    with stream_processing():
        r1.buffer(1).save("dummy_squence_shots")


config = None

loaded_config = None

