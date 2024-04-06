
# Single QUA script generated at 2024-04-06 16:53:00.317319
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    v1 = declare(int, )
    v2 = declare(int, )
    with infinite_loop_():
        pause()
        with for_(v1,0,(v1<1.125),(v1+0.25)):
            align()
            play("ramp"*amp(v1), "gate_1")
            wait(100, "gate_1")
            play("ramp"*amp((0-v1)), "gate_1")


config = None

loaded_config = None

