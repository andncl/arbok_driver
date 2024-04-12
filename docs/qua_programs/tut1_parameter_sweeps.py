
# Single QUA script generated at 2024-04-12 13:24:54.314852
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    v1 = declare(int, )
    v2 = declare(int, )
    with infinite_loop_():
        pause()
        with for_(v1,0,(v1<1.125),(v1+0.25)):
            align()
            play("ramp"*amp(v1), "gate_1", duration=20)
            wait(50, "gate_1")
            play("ramp"*amp((0-v1)), "gate_1", duration=20)


config = None

loaded_config = None

