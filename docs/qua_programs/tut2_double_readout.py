
# Single QUA script generated at 2024-04-12 13:25:53.211391
# QUA library version: 1.1.7

from qm.qua import *

with program() as prog:
    v1 = declare(fixed, )
    v2 = declare(fixed, )
    v3 = declare(fixed, )
    v4 = declare(fixed, )
    v5 = declare(fixed, )
    v6 = declare(fixed, )
    v7 = declare(fixed, )
    v8 = declare(fixed, )
    v9 = declare(fixed, )
    v10 = declare(fixed, )
    v11 = declare(fixed, )
    v12 = declare(fixed, )
    v13 = declare(fixed, )
    v14 = declare(fixed, )
    with infinite_loop_():
        pause()
        align()
        measure("measure", "readout_element", None, integration.full("x", v1, ""), integration.full("y", v2, ""))
        assign(v3, (v1+v2))
        r1 = declare_stream()
        save(v1, r1)
        r2 = declare_stream()
        save(v2, r2)
        r3 = declare_stream()
        save(v3, r3)
        measure("measure", "readout_element", None, integration.full("x", v7, ""), integration.full("y", v8, ""))
        assign(v9, (v7+v8))
        r7 = declare_stream()
        save(v7, r7)
        r8 = declare_stream()
        save(v8, r8)
        r9 = declare_stream()
        save(v9, r9)
        wait(50, )
        measure("measure", "readout_element", None, integration.full("x", v4, ""), integration.full("y", v5, ""))
        assign(v6, (v4+v5))
        r4 = declare_stream()
        save(v4, r4)
        r5 = declare_stream()
        save(v5, r5)
        r6 = declare_stream()
        save(v6, r6)
        measure("measure", "readout_element", None, integration.full("x", v10, ""), integration.full("y", v11, ""))
        assign(v12, (v10+v11))
        r10 = declare_stream()
        save(v10, r10)
        r11 = declare_stream()
        save(v11, r11)
        r12 = declare_stream()
        save(v12, r12)
        assign(v13, (v3-v6))
        r13 = declare_stream()
        save(v13, r13)
        assign(v14, (v9-v12))
        r14 = declare_stream()
        save(v14, r14)
    with stream_processing():
        r1.buffer(1).save("dummy_readout2__qubit1__reference__sensor1_I_buffer")
        r1.save_all("dummy_readout2__qubit1__reference__sensor1_I")
        r2.buffer(1).save("dummy_readout2__qubit1__reference__sensor1_Q_buffer")
        r2.save_all("dummy_readout2__qubit1__reference__sensor1_Q")
        r3.buffer(1).save("dummy_readout2__qubit1__reference__sensor1_IQ_buffer")
        r3.save_all("dummy_readout2__qubit1__reference__sensor1_IQ")
        r4.buffer(1).save("dummy_readout2__qubit1__read__sensor1_I_buffer")
        r4.save_all("dummy_readout2__qubit1__read__sensor1_I")
        r5.buffer(1).save("dummy_readout2__qubit1__read__sensor1_Q_buffer")
        r5.save_all("dummy_readout2__qubit1__read__sensor1_Q")
        r6.buffer(1).save("dummy_readout2__qubit1__read__sensor1_IQ_buffer")
        r6.save_all("dummy_readout2__qubit1__read__sensor1_IQ")
        r7.buffer(1).save("dummy_readout2__qubit2__reference__sensor1_I_buffer")
        r7.save_all("dummy_readout2__qubit2__reference__sensor1_I")
        r8.buffer(1).save("dummy_readout2__qubit2__reference__sensor1_Q_buffer")
        r8.save_all("dummy_readout2__qubit2__reference__sensor1_Q")
        r9.buffer(1).save("dummy_readout2__qubit2__reference__sensor1_IQ_buffer")
        r9.save_all("dummy_readout2__qubit2__reference__sensor1_IQ")
        r10.buffer(1).save("dummy_readout2__qubit2__read__sensor1_I_buffer")
        r10.save_all("dummy_readout2__qubit2__read__sensor1_I")
        r11.buffer(1).save("dummy_readout2__qubit2__read__sensor1_Q_buffer")
        r11.save_all("dummy_readout2__qubit2__read__sensor1_Q")
        r12.buffer(1).save("dummy_readout2__qubit2__read__sensor1_IQ_buffer")
        r12.save_all("dummy_readout2__qubit2__read__sensor1_IQ")
        r13.buffer(1).save("dummy_readout2__qubit1__diff_buffer")
        r13.save_all("dummy_readout2__qubit1__diff")
        r14.buffer(1).save("dummy_readout2__qubit2__diff_buffer")
        r14.save_all("dummy_readout2__qubit2__diff")


config = None

loaded_config = None
