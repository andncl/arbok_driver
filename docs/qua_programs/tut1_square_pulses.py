
# Single QUA script generated at 2024-04-12 13:24:54.204208
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    with infinite_loop_():
        pause()
        align()
        play("ramp"*amp(0.5), "gate_1", duration=20)
        wait(50, "gate_1")
        play("ramp"*amp(-0.5), "gate_1", duration=20)


config = None

loaded_config = None

