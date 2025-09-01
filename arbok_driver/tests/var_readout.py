"""Module containing threshold readout helper"""
import logging
from qm import qua
from arbok_driver import ReadSequence, AbstractReadout

class VarReadout(AbstractReadout):
    """Helper class enabling variable readout from a given signal"""
    signals: list

    def __init__(
            self,
            name: str,
            sequence: ReadSequence,
            attr_name: str,
            save_results: bool,
            params: dict
            ):
        """
        Constructor method for `VarReadout` readout helper class
        
        Args:
            name (str): Name of readout
            sequence (arbok_driver.ReadSequence): ReadSequence performing the
                abstract readout
            attr_name (str): Name under which the result will be saved
            save_results (bool): Whether to save the results
            params (dict): Parameters to be added to the read sequence
        """
        super().__init__(name, sequence, attr_name, save_results, params)
        self._create_gettables()

    def qua_measure(self):
        """Measures the given gettables and assigns the result to the vars"""
        for signal in self.signal_names:
            qua.assign(
                self.variable_obs[signal].qua_var, self.variables[signal]()
                )

    def _create_gettables(self):
        """Creates the gettables for the given readout"""
        # TODO: write