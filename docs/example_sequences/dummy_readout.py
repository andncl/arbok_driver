""" Module containing PSB 6 dot readout """
from qm import qua
from arbok_driver import ReadSequence, Sample, qua_helpers
from .average_readout import Average
from .difference import Difference

class DummyReadout(ReadSequence):
    """
    Class containing parameters and sequence for a dummy read sequnce
    """
    def __init__(
            self,
            parent,
            name: str,
            sample: Sample,
            sequence_config: dict,
        ):
        """
        Constructor method for 'DummyReadout' class
        
        Args:
            name (str): name of the sequence
            sample (Sample): Sample being used
            sequence_config (dict): Dict configuring sequence
        """
        super().__init__(
            parent, name, sample, sequence_config,
            {'difference': Difference},
            {'average': Average}
            )

    def qua_sequence(self):
        """QUA sequence to perform mixed down up initialization"""
        qua.align()

        ref_points = [x for x in self.readout_points.values() if x.point_name == 'reference']
        for readout_point in ref_points:
            readout_point.qua_measure_and_save()

        qua.wait(self.t_between_measurements())
        read_points = [x for x in self.readout_points.values() if x.point_name == 'read']
        for readout_point in read_points:
            readout_point.qua_measure_and_save()

        for _ , readout in self.difference.items():
            readout.qua_measure_and_save()

