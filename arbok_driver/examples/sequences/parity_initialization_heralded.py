"""
Module containing class for heralded parity spin initialization of a qubit pair
"""
from dataclasses import dataclass

from qm import qua
from qm.qua._expressions import QuaVariable
from arbok_driver import SequenceBase
from arbok_driver.parameter_types import Time
from .parity_initialization import ParityInit, ParityInitDeltaParameters

@dataclass(frozen = True)
class ParityInitHeraldedParameters(ParityInitDeltaParameters):
    """
    Parameters for heralded parity initialization.

    Inherits all voltage points and timings of the bare `ParityInit` and adds a
    single settle time that is applied once initialization has been heralded
    successfully.
    """
    t_wait_post_init: Time

class ParityInitHeralded(ParityInit):
    """
    Heralded parity initialization of a qubit pair.

    This sub-sequence wraps the bare `ParityInit` in a repeat-until-success loop
    that is driven by the measurement result of the *following* readout sequence
    (the ``feedback_result``). While the desired state has not yet been heralded,
    the sequence keeps re-running the bare initialization and its
    ``step_requirement`` stays ``False``. As soon as the readout reports the
    ``target_state``, the ``step_requirement`` is raised to ``True``, the
    re-initialization is skipped and the downstream quantum-control and
    data-saving stages are allowed to execute (see `Measurement`'s step
    requirement mechanism).
    """
    PARAMETER_CLASS = ParityInitHeraldedParameters
    arbok_params: ParityInitHeraldedParameters

    def __init__(
            self,
            parent: SequenceBase,
            name: str,
            feedback_result: str,
            target_state: int,
            sequence_config: dict,
            debug: bool = True,
        ):
        """
        Constructor method for 'ParityInitHeralded' class

        Args:
            parent (SequenceBase): parent sequence
            name (str): name of sequence
            feedback_result (str): path to the readout result used to herald the
                initialization. Must be resolvable from the measurement and lead
                to a gettable's ``qua_result_var`` (e.g.
                ``'parity_read.p1p2.state__p1p2.qua_result_var'``)
            target_state (int): readout result satisfying the protocol (0 or 1)
            sequence_config (dict): config containing pulse parameters
            debug (bool): if True, the number of initialization attempts per
                successful heralding is streamed for inspection
        """
        self.feedback_result = feedback_result
        self.target_state: bool = bool(target_state)
        self.debug = debug
        super().__init__(parent, name, sequence_config)
        self.elements = self.arbok_params.gate_elements.get()
        self.successful_init: QuaVariable[bool]
        self.feedback_var: QuaVariable[bool]

    def qua_declare(self):
        """
        Declares the flags coordinating the heralding loop.

        ``successful_init`` remembers the outcome of the previous readout, while
        ``step_requirement`` is registered on the measurement and gates the
        downstream control and data-saving stages.
        """
        self.successful_init = qua.declare(bool, value = False)
        self.step_requirement = qua.declare(bool, value = False)
        self.measurement.add_step_requirement(self.step_requirement)
        self.nr_attempts = qua.declare(int, value = 0)
        if self.debug:
            self.attempt_stream = qua.declare_stream()

    def qua_sequence(self):
        """QUA sequence to perform heralded spin parity initialization"""
        self.feedback_var = self.measurement.find_parameter_from_sub_sequence(
            self.feedback_result
        )
        with qua.if_(self.successful_init):
            ### Desired state was heralded by the previous readout: skip the
            ### re-initialization, allow the downstream stages to run and let
            ### the state settle before quantum control.
            qua.assign(self.step_requirement, True)
            if self.debug:
                qua.save(self.nr_attempts, self.attempt_stream)
            qua.assign(self.nr_attempts, 0)
            qua.align(*self.elements)
            qua.wait(self.arbok_params.t_wait_post_init.qua, *self.elements)
        with qua.else_():
            ### Desired state not yet heralded: block the downstream stages and
            ### run another bare initialization attempt.
            qua.assign(self.step_requirement, False)
            if self.debug:
                qua.assign(self.nr_attempts, self.nr_attempts + 1)
            super().qua_sequence()

    def qua_after_sequence(self):
        """
        Updates the heralding flag for the next iteration.

        If this iteration performed an initialization attempt, the flag is set
        from the latest readout result. If control was executed this iteration
        (state already heralded), the flag is reset so a fresh initialization is
        performed on the next shot.
        """
        with qua.if_(~self.successful_init):
            if self.target_state:
                qua.assign(self.successful_init, self.feedback_var)
            else:
                qua.assign(self.successful_init, ~self.feedback_var)
        with qua.else_():
            qua.assign(self.successful_init, False)

    def qua_stream(self):
        """Streams the per-shot attempt counter when debugging is enabled"""
        if self.debug:
            self.attempt_stream.save_all('heralded_attempts')
