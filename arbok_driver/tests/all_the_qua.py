from qm import qua
from arbok_driver import SubSequence

class AllTheQua(SubSequence):
    def qua_declare(self):
        print('qua_declare')
        # comment
        self.qua_declare_atq = qua.declare(int)
        self.qua_declare_atq_stream = qua.declare_stream()

    def qua_before_sweep(self):
        qua.assign(self.qua_declare_atq, 0)

    def qua_before_sequence(self, simulate: bool = False):
        qua.assign(self.qua_declare_atq, 1)

    def qua_sequence(self):
        qua.assign(self.qua_declare_atq, 2)
        qua.align(*self.elements)

    def qua_after_sequence(self):
        qua.assign(self.qua_declare_atq, 3)
        qua.align()
        qua.save(self.qua_declare_atq, self.qua_declare_atq_stream)

    def qua_stream(self):
        self.qua_declare_atq_stream.save_all('atq_stream')
