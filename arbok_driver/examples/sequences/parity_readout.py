"""Module containing ReadSequence implementing PSB readout"""
from dataclasses import dataclass

from qm import qua
from arbok_driver import (
    arbok, ParameterClass, SequenceBase, ReadSequence
)
from arbok_driver.parameter_types import (
    Time, ParameterMap,  Voltage, List
)

@dataclass(frozen = True)
class ParityReadParameters(ParameterClass):
    v_home: ParameterMap[str, Voltage]
    v_read: ParameterMap[str, Voltage]
    v_reference: ParameterMap[str, Voltage]
    gate_elements: List
    readout_elements: List
    t_wait_home_before: Time
    t_wait_pre_read: Time
    t_ramp_to_reference: Time
    t_ramp_to_read: Time
    t_wait_post_read: Time
    t_wait_after_reset: Time

class ParityRead(ReadSequence):
    """
    Class containing parameters and sequence for spin parity readout
    Args:
        param_config (dict): Dict containing all program parameters 
    """
    PARAMETER_CLASS= ParityReadParameters
    arbok_params: ParityReadParameters

    def __init__(
            self,
            parent: SequenceBase,
            name: str,
            sequence_config: dict,
    ):
        """
        Constructor method for 'ParityRead' class
        
        Args:
            parent (SequenceBase): Parent instrument module
                or instrument
            name (str): name of the sequence
            sequence_config (dict): Configuration for sequence
        """
        super().__init__(
            parent = parent,
            name = name,
            sequence_config = sequence_config,
            )
        self.elements = list(self.arbok_params.gate_elements.get())
        self.elements += list(self.arbok_params.readout_elements.get())

    def qua_declare(self):
        """
        Declares variables before execution of the main program. All mandatory
        qua variables for auto generated readouts from the config are introduced
        by the parent class (super)
        """
        return super().qua_declare()

    def qua_sequence(self):
        """
        QUA sequence to perform spin parity readout
        
        The sequence is as follows:
            1. Move to REFERENCE measurement point
            2. Take physical REFERENCE measurement
            3. Move to READ measurement point
            4. Take physical READ measurement
        """
        qua.align()
        qua.align(*self.elements)
        qua.wait(self.arbok_params.t_wait_home_before.qua, *self.elements)
        ### Move to REFERENCE measurement point
        arbok.ramp(
            elements = self.arbok_params.gate_elements.get(),
            reference = self.arbok_params.v_home,
            target = self.arbok_params.v_reference,
            duration = self.t_ramp_to_reference,
            operation = 'unit_ramp',
            )
        qua.wait(self.arbok_params.t_wait_pre_read.qua, *self.elements)
        qua.align(*self.elements)
        ### Take physical REFERENCE measurement
        for _, readout in self.readout_groups["ref"].items():
            readout.qua_measure()
        qua.align(*self.elements)
        qua.wait(self.t_wait_post_read.qua, *self.elements)

        ### Move to READ measurement point
        arbok.ramp(
            elements = self.arbok_params.gate_elements.get(),
            reference = self.arbok_params.v_reference,
            target = self.arbok_params.v_read,
            duration = self.arbok_params.t_ramp_to_read,
            operation = 'unit_ramp',
            )
        qua.wait(self.arbok_params.t_wait_pre_read.qua, *self.elements)
        qua.align(*self.elements)
        ### take physical READ measurement
        for _, readout in self.readout_groups["read"].items():
            readout.qua_measure()
        qua.align(*self.elements)
        qua.align()

        ### Process raw data in abstract readouts
        for _, readout in self.readout_groups["diff"].items():
            readout.qua_measure()
        for _, readout in self.readout_groups["state"].items():
            readout.qua_measure()
        qua.align(*self.elements)
        qua.wait(self.arbok_params.t_wait_post_read.qua, *self.elements)

        ### Reset elements
        arbok.reset_sticky_elements(self.arbok_params.gate_elements.get())
        qua.wait(self.arbok_params.t_wait_after_reset.qua, *self.elements)
        qua.align(*self.elements)

        ### Apply feedback if given in configuration
        if 'set_feedback' in self.readout_groups:
            for _, readout in self.readout_groups["set_feedback"].items():
                readout.qua_measure()
        qua.align()

    def qua_after_sequence(self):
        """Saves variables to the respective streams after the sequence"""
        self.measurement.qua_check_step_requirements(self.save_variables)

    def save_variables(self):
        """Saves all variables to the respective streams"""
        for _, readout in self.abstract_readouts.items():
            readout.qua_save_variables()
