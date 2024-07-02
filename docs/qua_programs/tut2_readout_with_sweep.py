
# Single QUA script generated at 2024-06-28 14:43:55.603324
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    v1 = declare(int, )
    v2 = declare(int, value=0)
    v3 = declare(fixed, )
    v4 = declare(fixed, )
    v5 = declare(fixed, )
    v6 = declare(fixed, )
    v7 = declare(fixed, )
    v8 = declare(fixed, )
    v9 = declare(fixed, )
    v10 = declare(int, )
    with infinite_loop_():
        pause()
        assign(v1, 10)
        with for_(v10,0,(v10<9),(v10+1)):
            align()
            align()
            measure("measure", "readout_element", None, integration.full("x", v3, ""), integration.full("y", v4, ""))
            assign(v5, (v3+v4))
            r2 = declare_stream()
            save(v3, r2)
            r3 = declare_stream()
            save(v4, r3)
            r4 = declare_stream()
            save(v5, r4)
            wait(v1, )
            measure("measure", "readout_element", None, integration.full("x", v6, ""), integration.full("y", v7, ""))
            assign(v8, (v6+v7))
            r5 = declare_stream()
            save(v6, r5)
            r6 = declare_stream()
            save(v7, r6)
            r7 = declare_stream()
            save(v8, r7)
            assign(v9, (v5-v8))
            r8 = declare_stream()
            save(v9, r8)
            assign(v2, (v2+1))
            r1 = declare_stream()
            save(v2, r1)
            assign(v1, (v1+10))
    with stream_processing():
        r1.buffer(1).save("dummy_squence_shots")
        r2.buffer(9).save("dummy_readout__qubit1__reference__sensor1_I_buffer")
        r3.buffer(9).save("dummy_readout__qubit1__reference__sensor1_Q_buffer")
        r4.buffer(9).save("dummy_readout__qubit1__reference__sensor1_IQ_buffer")
        r5.buffer(9).save("dummy_readout__qubit1__read__sensor1_I_buffer")
        r6.buffer(9).save("dummy_readout__qubit1__read__sensor1_Q_buffer")
        r7.buffer(9).save("dummy_readout__qubit1__read__sensor1_IQ_buffer")
        r8.buffer(9).save("dummy_readout__qubit1__diff_buffer")


config = None

loaded_config = None

