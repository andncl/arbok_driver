
# Single QUA script generated at 2026-03-19 06:08:17.314374
# QUA library version: 1.2.5


from qm import CompilerOptionArguments
from qm.qua import *

with program() as prog:
    v1 = declare(int, value=0)
    with infinite_loop_():
        pause()
        assign(v1, 0)
        align()
        play("ramp"*amp(0.5), "gate_1", duration=20)
        wait(50, "gate_1")
        play("ramp"*amp(0.5), "gate_1", duration=20)
        align()
        assign(v1, (v1+1))
        r0 = declare_stream()
        save(v1, r0)
        align()
    with stream_processing():
        r0.buffer(1).save("qm_driver_dummy_squence_shots")

config = None

loaded_config = None

