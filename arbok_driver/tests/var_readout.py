"""Module containing threshold readout helper"""
import logging
from qm import qua
from arbok_driver import ReadSequence, AbstractReadout, AbstractObservable

class VarReadout(AbstractReadout):
    """Helper class enabling variable readout from a given signal"""
    signals: list
    thresholds: dict
    current_obs  = {}
    state_obs = {}

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
        self._create_observables()

    def qua_measure(self):
        """Measures the given observables and assigns the result to the vars"""
        for signal in self.signals:
            qua.assign(
                self.variable_obs[signal].qua_var, self.variables[signal]()
                )

    def _create_observables(self):
        """Creates the observables for the given readout"""
        self.observables = {}
        self.variable_obs = {}
        self.variables = self.get_params_with_prefix('signal_param')
        self.signals = self.variables.keys()
        for signal, var in self.variables.items():
            self.variable_obs[signal] = obs = AbstractObservable(
                observable_name = self.attr_name,
                abstract_readout = self,
                signal = signal,
                qua_type = qua.fixed
            )
            self.observables[obs.full_name] = obs
