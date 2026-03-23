"""Module containing difference readout helper"""
from qm import qua
from arbok_driver import (
    AbstractReadout,
    ReadSequence,
    Signal, 
)

class Difference(AbstractReadout):
    """Helper class enabling difference readout from a given signal"""

    def __init__(
            self,
            name: str,
            read_sequence: ReadSequence,
            signal: Signal,
            save_results: bool,
            parameters: dict,
            minuend: str,
            subtrahend: str,
            ):
        """
        Constructor method of `Difference` readout helper
        
        Args:
            name (str): Name of readout
            read_sequence (arbok_driver.ReadSequence): ReadSequence performing the
                abstract readout
            signal (arbok_driver.Signal): Signal to be measured
            save_results (bool): Whether to save the results
            params (dict): Parameters to be added to the read sequence
            minuend (str): Name of the minuend gettable
            subtrahend (str): Name of the subtrahend gettable
        """
        super().__init__(
            name = name,
            read_sequence = read_sequence,
            signal = signal,
            save_results = save_results,
            parameters = parameters
        )
        self.signal = signal
        self.minuend = minuend
        self.subtrahend = subtrahend
        self._create_gettables()

    def qua_measure(self):
        """
        Measures the given gettables and assigns the result to the variables.
        Only to be called within qua.program() context manager!
        """
        qua.assign(
            self.difference_gettable.qua_result_var,
            self.minuend_gettable.qua_result_var
            - self.subtrahend_gettable.qua_result_var
            )

    def _create_gettables(self):
        """Creates the gettables for the given readout"""
        self.minuend_gettable = self.get_gettable_from_path(self.minuend)
        self.subtrahend_gettable = self.get_gettable_from_path(self.subtrahend)

        self.difference_gettable = self.create_gettable(
            gettable_name = self.name,
            var_type = qua.fixed
        )
