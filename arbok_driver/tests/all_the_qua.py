from qm import qua
from arbok_driver import ReadSequence

class AllTheQua(ReadSequence):
    
    def qua_declare(self):
        print('qua_declare')
        self.dummy_var.set(qua.declare(qua.fixed, 0.))
        self.qua_declare_atq = qua.declare(int)
        super().qua_declare()

    def qua_before_sweep(self):
        qua.assign(self.qua_declare_atq, 0)

    def qua_before_sequence(self, simulate: bool = False):
        qua.assign(self.qua_declare_atq, 1)

    def qua_sequence(self):
        qua.assign(self.qua_declare_atq, 2)
        qua.align(*self.elements)
        # # This can be used to display snake scanning in the collected output stream
        # with qua.if_(self.measurement.sweeps[0].sweep_snake_var):
        #     qua.assign(self.dummy_var.get_raw(), self.dummy_var.get_raw()-0.0001)
        # with qua.else_():
        #     qua.assign(self.dummy_var.get_raw(), self.dummy_var.get_raw()+0.0001)
        # This can be used to have a continuously increasing the collected output stream 
        qua.assign(self.dummy_var.get_raw(), self.dummy_var.get_raw()+0.0001)
        # Use the following to check the swept parameter
        # qua.assign(self.dummy_var.get_raw(), self.measurement.sweeps[0].parameters[0].qua_var)
        qua.align()

    def qua_after_sequence(self):
        qua.assign(self.qua_declare_atq, 3)
        for _ , readout in self.var_readouts.items():
            readout.qua_measure_and_save()
