"""Module containing generic StabilityMap class"""
from dataclasses import dataclass
from qm import qua
from arbok_driver import qua_helpers, Device, ReadSequence, parameter_types
from arbok_driver.parameter_types import Time, ParameterMap

@dataclass
class StabilityMapParameters:
    """Parameter class for StabilityMap read sequence"""
    t_pre_chop: Time
    v_home: ParameterMap
    v_level: ParameterMap

class StabilityMap(ReadSequence):
    """
    Class containing qua sequence to perform a stability map measurement
    """
    PARAMETER_CLASS = StabilityMapParameters
    def __init__(
            self,
            parent,
            name: str,
            device: Device,
            sequence_config: dict | None = None
    ):
        """
        Constructor method for 'MixedDownUpInit' class

        Args:
            name (str): name of sequence
            device  (Device): Device class for physical device
            sequence_config (dict): config containing pulse parameters
        """
        super().__init__(
            parent = parent,
            name = name,
            device = device,
            sequence_config = sequence_config
        )
        self.elements = list(self.gate_elements())
        self.arbok_params.v_home

    def qua_declare(self):
        """
        Setup the python callback
        """
        super().qua_declare()

    def qua_sequence(self):
        qua.align(*self.elements)

        ### Go to point in voltage space
        qua_helpers.arbok_go(
            sub_sequence= self,
            elements= self.gate_elements(),
            from_volt = 'v_home',
            to_volt = 'v_level',
            operation = 'unit_ramp',
            align_after = 'elements'
            )
        qua.wait(self.t_pre_chop(), *self.elements)
        qua.align(*self.elements)

        ### Conduct chopped readout(s)
        for _, readout in self.readout_groups["chop"].items():
            readout.qua_measure_and_save()
        qua.align(*self.elements)

        ### Reset elements to home voltage
        qua_helpers.reset_elements(self.gate_elements(), self)
