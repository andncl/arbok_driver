
# Single QUA script generated at 2024-06-19 16:01:00.014451
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    v1 = declare(int, value=0)
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
        assign(v1, (v1+1))
        r1 = declare_stream()
        save(v1, r1)
    with stream_processing():
        r1.buffer(1).save("dummy_sequence2_shots")


config = None

loaded_config = None

