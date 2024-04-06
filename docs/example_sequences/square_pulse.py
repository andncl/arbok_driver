"""Module containing generic sequence for a adiabatic sequence"""
from qm import qua
from arbok_driver import SubSequence, Sample, qua_helpers

class SquarePulse(SubSequence):
    """
    Class containing parameters and sequence for a square pulse
    """
    def __init__(self, name: str,sample: Sample, seq_config: dict):
        """
        Constructor method for 'SquarePulse' class
        
        Args:
            name (str): name of sequence
            sample  (Sample): Sample class for physical device
            config (dict): config containing pulse parameters
        """
        super().__init__(name, sample, seq_config)
        ### The section below is unique to this specific sequence


    def qua_sequence(self):
        qua.align()
        qua.play('ramp'*qua.amp(self.amplitude()), self.element())
        qua.wait(self.t_square_pulse(), self.element())
        qua.play('ramp'*qua.amp(-self.amplitude()), self.element())

