
# Single QUA script generated at 2024-04-09 13:32:30.000334
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    v1 = declare(int, )
    v2 = declare(int, )
    a1 = declare(int, value=[10, 20, 30, 40])
    v3 = declare(int, )
    a2 = declare(int, value=[10, 20, 30, 40])
    v4 = declare(int, )
    v5 = declare(int, )
    with infinite_loop_():
        pause()
        with for_each_((v2,v3),(a1,a2)):
            with for_(v1,0,(v1<1.125),(v1+0.25)):
                align()
                play("ramp"*amp(v1), "gate_1", duration=v3)
                wait(v2, "gate_1")
                play("ramp"*amp((0-v1)), "gate_1", duration=v3)


config = None

loaded_config = None

