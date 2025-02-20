from qm import qua
from arbok_driver import ReadSequence

class AllTheQua(ReadSequence):
    
    def qua_declare(self):
        print('qua_declare')
        self.dummy_var.set(qua.declare(qua.fixed, 0.))
        self.qua_declare_atq = qua.declare(int)

    def qua_before_sweep(self):
        qua.assign(self.qua_declare_atq, 0)

    def qua_before_sequence(self, simulate: bool = False):
        qua.assign(self.qua_declare_atq, 1)

    def qua_sequence(self):
        qua.assign(self.qua_declare_atq, 2)
        qua.align(*self.elements)
        for _ , readout in self.var_readouts.items():
            readout.qua_measure_and_save()

    def qua_after_sequence(self):
        qua.assign(self.qua_declare_atq, 3)
        qua.assign(self.dummy_var.get_raw(), self.dummy_var.get_raw()+0.0001)
        qua.align()
