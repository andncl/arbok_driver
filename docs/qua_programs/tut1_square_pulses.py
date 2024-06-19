
# Single QUA script generated at 2024-06-19 16:00:59.744195
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    v1 = declare(int, value=0)
    with infinite_loop_():
        pause()
        align()
        play("ramp"*amp(0.5), "gate_1", duration=20)
        wait(50, "gate_1")
        play("ramp"*amp(-0.5), "gate_1", duration=20)
        assign(v1, (v1+1))
        r1 = declare_stream()
        save(v1, r1)
    with stream_processing():
        r1.buffer(1).save("dummy_squence_shots")


config = None

loaded_config = None

