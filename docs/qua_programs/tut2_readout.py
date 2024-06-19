
# Single QUA script generated at 2024-06-19 16:02:16.257184
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    v1 = declare(int, value=0)
    v2 = declare(fixed, )
    v3 = declare(fixed, )
    v4 = declare(fixed, )
    v5 = declare(fixed, )
    v6 = declare(fixed, )
    v7 = declare(fixed, )
    v8 = declare(fixed, )
    with infinite_loop_():
        pause()
        align()
        measure("measure", "readout_element", None, integration.full("x", v2, ""), integration.full("y", v3, ""))
        assign(v4, (v2+v3))
        r2 = declare_stream()
        save(v2, r2)
        r3 = declare_stream()
        save(v3, r3)
        r4 = declare_stream()
        save(v4, r4)
        wait(50, )
        measure("measure", "readout_element", None, integration.full("x", v5, ""), integration.full("y", v6, ""))
        assign(v7, (v5+v6))
        r5 = declare_stream()
        save(v5, r5)
        r6 = declare_stream()
        save(v6, r6)
        r7 = declare_stream()
        save(v7, r7)
        assign(v8, (v4-v7))
        r8 = declare_stream()
        save(v8, r8)
        assign(v1, (v1+1))
        r1 = declare_stream()
        save(v1, r1)
    with stream_processing():
        r1.buffer(1).save("dummy_squence_shots")
        r2.buffer(1).save("dummy_readout__qubit1__reference__sensor1_I_buffer")
        r3.buffer(1).save("dummy_readout__qubit1__reference__sensor1_Q_buffer")
        r4.buffer(1).save("dummy_readout__qubit1__reference__sensor1_IQ_buffer")
        r5.buffer(1).save("dummy_readout__qubit1__read__sensor1_I_buffer")
        r6.buffer(1).save("dummy_readout__qubit1__read__sensor1_Q_buffer")
        r7.buffer(1).save("dummy_readout__qubit1__read__sensor1_IQ_buffer")
        r8.buffer(1).save("dummy_readout__qubit1__diff_buffer")


config = None

loaded_config = None

