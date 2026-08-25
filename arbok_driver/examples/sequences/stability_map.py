"""Module containing generic StabilityMap class"""
from dataclasses import dataclass
from qm import qua
from arbok_driver import arbok, ReadSequence, ParameterClass
from arbok_driver.parameter_types import Time, ParameterMap, String, Voltage

@dataclass(frozen=True)
class StabilityMapParameters(ParameterClass):
    """Parameter class for StabilityMap read sequence"""
    t_pre_chop: Time
    gate_elements: String
    v_home: ParameterMap[str, Voltage]
    v_level: ParameterMap[str, Voltage]

class StabilityMap(ReadSequence):
    """
    Class containing qua sequence to perform a stability map measurement
    """
    PARAMETER_CLASS = StabilityMapParameters
    arbok_params: StabilityMapParameters
    def __init__(
            self,
            parent,
            name: str,
            sequence_config: dict
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
            sequence_config = sequence_config
        )
        self.elements = list(self.arbok_params.gate_elements.get())
        self.arbok_params.v_home

    def fpga_sequence(self):
        """Hardware-agnostic stability map sequence."""
        arbok.align(*self.elements)
        arbok.play(
            elements=self.arbok_params.gate_elements.get(),
            reference=self.arbok_params.v_home,
            target=self.arbok_params.v_level,
            operation='unit_ramp',
        )
        arbok.wait(self.arbok_params.t_pre_chop.hw_var, *self.elements)
        arbok.align(*self.elements)

        for _, readout in self.readout_groups["chop"].items():
            readout.qua_measure_and_save()
        arbok.align(*self.elements)

        arbok.reset_sticky_elements(self.arbok_params.gate_elements.get())

    def fpga_sequence__qua(self):
        """QUA-backend-specific stability map sequence."""
        qua.align(*self.elements)
        arbok.ramp(
            elements= self.arbok_params.gate_elements.get(),
            reference = self.arbok_params.v_home,
            target = self.arbok_params.v_level,
            operation = 'unit_ramp',
            )
        qua.wait(self.arbok_params.t_pre_chop.hw_var, *self.elements)
        qua.align(*self.elements)

        for _, readout in self.readout_groups["chop"].items():
            readout.qua_measure_and_save()
        qua.align(*self.elements)

        arbok.reset_sticky_elements(self.arbok_params.gate_elements.get())
