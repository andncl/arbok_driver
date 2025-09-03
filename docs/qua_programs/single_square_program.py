
# Single QUA script generated at 2025-09-03 16:51:02.305902
# QUA library version: 1.2.1

from qm import CompilerOptionArguments
from qm.qua import *

with program() as prog:
    v1 = declare(int, value=0)
    with infinite_loop_():
        pause()
        assign(v1, 0)
        align()
        play("ramp"*amp(0.1), "gate_1", duration=200)
        wait(100, "gate_1")
        play("ramp"*amp(-0.1), "gate_1", duration=200)
        align()
        assign(v1, (v1+1))
        r0 = declare_stream()
        save(v1, r0)
        align()
    with stream_processing():
        r0.buffer(1).save("mock_driver_mock_measurement_shots")


config = None

loaded_config = None

