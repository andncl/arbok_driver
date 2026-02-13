
# Single QUA script generated at 2026-02-12 11:39:52.351283
# QUA library version: 1.2.5


from qm import CompilerOptionArguments
from qm.qua import *

with program() as prog:
    v1 = declare(int, value=0)
    with infinite_loop_():
        pause()
        assign(v1, 0)
        align()
        play("ramp"*amp(1.5), "P1", duration=100)
        wait(1000, "P1")
        play("ramp"*amp(1.5), "P1", duration=100)
        align()
        assign(v1, (v1+1))
        r0 = declare_stream()
        save(v1, r0)
        align()
    with stream_processing():
        r0.buffer(1).save("mock_driver_mock_measurement_shots")

config = None

loaded_config = None

