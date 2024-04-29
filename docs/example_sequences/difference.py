"""Module containing difference readout helper"""
import logging
from qm import qua
from arbok_driver import (
    ReadSequence, Signal, AbstractReadout, AbstractObservable
)

class Difference(AbstractReadout):
    """Helper class enabling difference readout from a given signal"""
    def __init__(
            self,
            name: str,
            sequence: ReadSequence,
            attr_name: str,
            save_results: bool,
            signal: Signal,
            minuend: str,
            subtrahend: str,
            ):
        """
        Constructor method of `Difference` readout helper
        
        Args:
            name (str): Name of readout
            sequence (arbok_driver.ReadSequence): ReadSequence performing the
                abstract readout
            attr_name (str): Name under which the result will be saved
            signal (arbok_driver.Signal): Signal on which the result will be
                saved
            minuend (str): Path to the qua variable that acts as minuend
            subtrahend (str): Path to the qua variable that acts as subtrahend
        """
        super().__init__(name, sequence, attr_name, save_results)
        self.minuend_path = minuend
        self.subtrahend_path = subtrahend
        self.observable = AbstractObservable(
            observable_name = self.attr_name,
            abstract_readout = self,
            signal = signal,
            qua_type = qua.fixed
        )
        self.observables = {self.observable.full_name: self.observable}

    def qua_measure(self):
        """
        Measures the given observables and assigns the result to the variables.
        Only to be called within qua.program() context manager!
        """
        minuend = self._find_observable_from_path(self.minuend_path)
        subtrahend = self._find_observable_from_path(self.subtrahend_path)
        qua.assign(
            self.observable.qua_var,
            minuend.qua_var - subtrahend.qua_var
            )
