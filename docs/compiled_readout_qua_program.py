
# Single QUA script generated at 2024-04-06 12:24:17.984397
# QUA library version: 1.1.6

from qm.qua import *

with program() as prog:
    v1 = declare(int, )
    v2 = declare(fixed, )
    v3 = declare(fixed, )
    v4 = declare(fixed, )
    v5 = declare(fixed, )
    v6 = declare(fixed, )
    v7 = declare(fixed, )
    v8 = declare(fixed, )
    v9 = declare(int, )
    with infinite_loop_():
        pause()
        with for_(v1,0,(v1<1.125),(v1+0.25)):
            align()
            play("ramp"*amp(v1), "gate_1")
            wait(100, "gate_1")
            play("ramp"*amp((0-v1)), "gate_1")
            align()
            measure("measure", "readout_element", None, integration.full("x", v2, ""), integration.full("y", v3, ""))
            assign(v4, (v2+v3))
            r1 = declare_stream()
            save(v2, r1)
            r2 = declare_stream()
            save(v3, r2)
            r3 = declare_stream()
            save(v4, r3)
            wait(50, )
            measure("measure", "readout_element", None, integration.full("x", v5, ""), integration.full("y", v6, ""))
            assign(v7, (v5+v6))
            r4 = declare_stream()
            save(v5, r4)
            r5 = declare_stream()
            save(v6, r5)
            r6 = declare_stream()
            save(v7, r6)
            assign(v8, (v4-v7))
            r7 = declare_stream()
            save(v8, r7)
    with stream_processing():
        r1.buffer(5).save("dummy_readout_qubit1__ref__sensor1_I_buffer")
        r1.save_all("dummy_readout_qubit1__ref__sensor1_I")
        r2.buffer(5).save("dummy_readout_qubit1__ref__sensor1_Q_buffer")
        r2.save_all("dummy_readout_qubit1__ref__sensor1_Q")
        r3.buffer(5).save("dummy_readout_qubit1__ref__sensor1_IQ_buffer")
        r3.save_all("dummy_readout_qubit1__ref__sensor1_IQ")
        r4.buffer(5).save("dummy_readout_qubit1__read__sensor1_I_buffer")
        r4.save_all("dummy_readout_qubit1__read__sensor1_I")
        r5.buffer(5).save("dummy_readout_qubit1__read__sensor1_Q_buffer")
        r5.save_all("dummy_readout_qubit1__read__sensor1_Q")
        r6.buffer(5).save("dummy_readout_qubit1__read__sensor1_IQ_buffer")
        r6.save_all("dummy_readout_qubit1__read__sensor1_IQ")
        r7.buffer(5).save("dummy_readout_qubit1__diff_buffer")
        r7.save_all("dummy_readout_qubit1__diff")


config = None

loaded_config = None

