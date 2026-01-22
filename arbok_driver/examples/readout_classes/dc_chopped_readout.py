"""Module containing ChoppedReadout class"""

from qm import qua
from arbok_driver import (
    ReadSequence, AbstractReadout, qua_helpers, Signal
)

class DcChoppedReadout(AbstractReadout):
    """Abstract readout class for chopped readout"""

    def __init__(
        self,
        name: str,
        read_sequence: ReadSequence,
        signal: Signal,
        save_results: bool,
        parameters: dict,
        readout_qua_elements: dict[str, str],
        ):
        """
        Constructor method for `ChoppedReadout` abstractreadout helper class
        
        Args:
            name (str): Name of the abstract readout. Will be added to
                respective signals like this
            sequence (arbok_driver.Sequence): ReadSequence in which this
                abstract readout is performed
            attr_name (str): Name under which this readout saves observables
            save_results (bool): Whether to save the results
            params (dict): Parameters to be added to the read sequence
        """
        self.n_chops: callable = None
        super().__init__(
            name = name,
            read_sequence = read_sequence,
            signal = signal,
            save_results = save_results,
            parameters = parameters
        )
        self.readout_qua_elements = readout_qua_elements
        self.qua_chop_nr = None

        self.n_chops_division = 1/self.n_chops()
        self.gate_elements = list(parameters['v_chop']['elements'].keys())
        self.elements = self.gate_elements + list(self.readout_qua_elements.values())
        self.target = f'{self.name}__v_chop'

        self.ref_temp_vars = {}
        self.read_temp_vars = {}
        self.read_gettables = {}
        self.ref_gettables = {}
        self.diff_gettables = {}
        self._create_gettables()

    def qua_declare_variables(self):
        """Declares all necessary qua variables for readout"""
        self.n_chops_division = 1/self.n_chops()
        super().qua_declare_variables()
        self.qua_chop_nr = qua.declare(int)
        for sub_readout, _ in self.readout_qua_elements.items():
            self.ref_temp_vars[sub_readout] = qua.declare(qua.fixed)
            self.read_temp_vars[sub_readout] = qua.declare(qua.fixed)

    def qua_measure(self):
        """Measures the given observables and assigns the result to the vars"""
        for sub_readout, _ in self.readout_qua_elements.items():
            qua.assign(self.diff_gettables[sub_readout].qua_result_var, 0.)
            qua.assign(self.ref_temp_vars[sub_readout], 0.)
            qua.assign(self.read_temp_vars[sub_readout], 0.)

        with qua.for_(
            var = self.qua_chop_nr,
            init = 0,
            cond = self.qua_chop_nr < self.n_chops(),
            update = self.qua_chop_nr + 1
            ):
            qua.align()
            qua_helpers.arbok_go(
                sub_sequence = self.read_sequence,
                elements= self.gate_elements,
                from_volt = 'v_home',
                to_volt = self.target,
                operation = 'unit_ramp',
                align_after = 'elements'
                )

            qua.align(*self.elements)
            qua.wait(self.chop_wait(), *self.elements)
            qua.align(*self.elements)

            for sub_readout, qua_element in self.readout_qua_elements.items():
                outputs = [
                    qua.integration.full('x_const', self.ref_gettables[sub_readout].qua_result_var),
                    ]
                qua.measure('measure', qua_element, None, *outputs)
            qua.align(*self.elements)

            qua_helpers.arbok_go(
                sub_sequence = self.read_sequence,
                elements= self.gate_elements,
                from_volt = self.target,
                to_volt = 'v_home',
                operation = 'unit_ramp',
                align_after = 'elements'
                )

            qua.align(*self.elements)
            qua.wait(self.chop_wait(), *self.elements)
            qua.align(*self.elements)

            for sub_readout, qua_element in self.readout_qua_elements.items():
                outputs = [
                    qua.integration.full('x_const', self.read_gettables[sub_readout].qua_result_var),
                    ]
                qua.measure('measure', qua_element, None, *outputs)
            qua.align(*self.elements)

            ### Calculate difference between read and reference point
            ### Add to total result
            for sub_readout, _ in self.readout_qua_elements.items():
                # Calculate the difference in qua
                qua.assign(
                    self.ref_temp_vars[sub_readout],
                    self.ref_temp_vars[sub_readout]
                    + self.ref_gettables[sub_readout].qua_result_var*self.n_chops_division
                )
                qua.assign(
                    self.read_temp_vars[sub_readout],
                    self.read_temp_vars[sub_readout]
                    + self.read_gettables[sub_readout].qua_result_var*self.n_chops_division
                )
        qua.align()
        ### Normalize the result and threshold it
        for sub_readout, _ in self.readout_qua_elements.items():
            ### Save accumulated ref and read to respective observables
            qua.assign(
                self.ref_gettables[sub_readout].qua_result_var,
                self.ref_temp_vars[sub_readout]
                )
            qua.assign(
                self.read_gettables[sub_readout].qua_result_var,
                self.read_temp_vars[sub_readout]
                )
            ### Calculate the difference and threshold it
            qua.assign(
                self.diff_gettables[sub_readout].qua_result_var,
                self.read_temp_vars[sub_readout] - self.ref_temp_vars[sub_readout]
                )
        qua.align(*self.elements)

    def _create_gettables(self):
        """
        Populates helper attributes for chopped readout class instance.

        Attributes:
            elements (list): List of elements to be chopped
            signals (list): List of signals on which results are saved
            ref__gettables (dict): Dict with signal names as keys and
                respective reference observables as values
            read__gettables (dict): Dict with signal names as keys and
                respective read observables as values
            chop_observables (dict): Dict with signal names as keys and
                respective chop observables as values
            state_observables (dict): Dict with signal names as keys and
                respective state observables as values
            observables (dict): Dict with FULL observable names as keys and
                ALL observables as values. Crucial for auto param declare
        """
        for sub_readout, _ in self.readout_qua_elements.items():
            read = self.read_gettables[sub_readout] = self.create_gettable(
                gettable_name = f"{sub_readout}_read",
                var_type = qua.fixed,
            )
            ref = self.ref_gettables[sub_readout] = self.create_gettable(
                gettable_name = f"{sub_readout}_ref",
                var_type = qua.fixed,
            )
            diff = self.diff_gettables[sub_readout] = self.create_gettable(
                gettable_name = f"{sub_readout}_diff",
                var_type = qua.fixed,
            )
            self.read_gettables[sub_readout] = read
            self.ref_gettables[sub_readout] = ref
            self.diff_gettables[sub_readout] = diff
