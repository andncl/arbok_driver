
# Single QUA script generated at 2026-03-19 06:09:41.378656
# QUA library version: 1.2.5


from qm import CompilerOptionArguments
from qm.qua import *

with program() as prog:
    v1 = declare(int, value=0)
    with infinite_loop_():
        pause()
        assign(v1, 0)
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
        align()
        assign(v1, (v1+1))
        r0 = declare_stream()
        save(v1, r0)
        align()
    with stream_processing():
        r0.buffer(1).save("qm_driver2_mock_measurement2_shots")

config = None

loaded_config = None

