"""
Module containing class parity spin initialization of a qubit pair
"""
from dataclasses import dataclass

from qm import qua
from qm.qua._expressions import QuaVariable
from arbok_driver import (
    arbok, ParameterClass, SequenceBase, SubSequence
)
from arbok_driver.parameter_types import (
    Time, ParameterMap, Voltage, List
)

@dataclass(frozen = True)
class ParityInitDeltaParameters(ParameterClass):
    gate_elements: List
    v_home: ParameterMap[str, Voltage]
    v_t1_point: ParameterMap[str, Voltage]
    v_pre_crossing: ParameterMap[str, Voltage]
    v_delta: ParameterMap[str, Voltage]
    t_ramp_to_t1: Time
    t_wait_at_t1: Time
    t_ramp_to_crossing: Time
    t_wait_before_crossing: Time
    t_ramp_over_crossing: Time
    t_wait_after_crossing: Time

class ParityInit(SubSequence):
    """
    Class containing parameters and sequence for parity initialization
    """
    PARAMETER_CLASS= ParityInitDeltaParameters
    arbok_params: ParityInitDeltaParameters

    def __init__(
            self,
            parent: SequenceBase,
            name: str,
            sequence_config: dict
        ):
        """
        Constructor method for 'ParityInit' class
        
        Args:
            parent (InstrumentModule | Instrument): parent sequence
            name (str): name of sequence
            device  (Device): Device class for physical device
            seq_config (dict): config containing pulse parameters
        """
        super().__init__(parent, name, sequence_config)
        self.elements = self.arbok_params.gate_elements.get()

    def qua_sequence(self):
        """QUA sequence to perform odd spin parity initialization (down-up)"""
        ### Ramping to point in the even charge state region to init GS
        arbok.ramp(
			elements= self.elements,
			reference = self.arbok_params.v_home,
			target = self.arbok_params.v_t1_point,
			duration = self.arbok_params.t_ramp_to_t1,
			operation = 'unit_ramp'
			)
        qua.wait(self.arbok_params.t_wait_at_t1.qua, *self.elements)

        ### Ramp to point close to the charge transition
        arbok.ramp(
			elements= self.elements,
			reference = self.arbok_params.v_t1_point,
			target = self.arbok_params.v_pre_crossing,
			duration = self.arbok_params.t_ramp_to_crossing,
			operation = 'unit_ramp'
			)
        qua.wait(self.arbok_params.t_wait_before_crossing.qua, *self.elements)

        ### Ramping (a)diabatically across the charge transition back into the
        ### control region
        arbok.ramp(
			elements= self.elements,
			target = self.arbok_params.v_delta,
			duration = self.arbok_params.t_ramp_over_crossing,
			operation = 'unit_ramp'
			)
        qua.wait(self.arbok_params.t_wait_after_crossing.qua, *self.elements)

        ### Ramping back to the home point resetting elements
        arbok.reset_sticky_elements(self.elements)
