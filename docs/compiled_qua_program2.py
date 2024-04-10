
# Single QUA script generated at 2024-04-09 15:13:31.976860
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    with infinite_loop_():
        pause()
        align("gate_1", "gate_2", "gate_3", "gate_4")
        align("gate_1", "gate_2", "gate_3", "gate_4")
        play("unit_ramp"*amp(0.2), "gate_1", duration=20)
        play("unit_ramp"*amp(-0.1), "gate_2", duration=20)
        play("unit_ramp"*amp(0.08), "gate_3", duration=20)
        play("unit_ramp"*amp(0.25), "gate_4", duration=20)
        align("gate_1", "gate_2", "gate_3", "gate_4")
        wait(100, "gate_1", "gate_2", "gate_3", "gate_4")
        align("gate_1", "gate_2", "gate_3", "gate_4")
        play("unit_ramp"*amp(-0.2), "gate_1", duration=20)
        play("unit_ramp"*amp(0.1), "gate_2", duration=20)
        play("unit_ramp"*amp(-0.08), "gate_3", duration=20)
        play("unit_ramp"*amp(-0.25), "gate_4", duration=20)
        align("gate_1", "gate_2", "gate_3", "gate_4")


config = None

loaded_config = None

