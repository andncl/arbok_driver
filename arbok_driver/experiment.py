"""Module containing abstract class for experiments"""
from abc import ABC

class Experiment(ABC):
    """
    Abstract class describing a type of experiment to run on the QM.
    This enforces a certain order of sequences that only requires certain
    input parameters or configurations to be set.
    E.g. for a rabi experiment, the order of sequences is:
        1. Initialization of quantum state
        2. Rabi pulse
        3. Readout of quantum state
    
    Attributes:
        name (str): Name of the experiment to run
        sequences (dict): Sequences to be run within program uploaded to the QM
    """
    _sequences_config = None
    _name = None

    @property
    def name(self) -> str:
        """Name of the experiment to run"""
        return self._name

    @property
    def sequences(self) -> dict:
        """Sequences to be run within program uploaded to the OPX"""
        return self._sequences_config

    def __call__(self) -> dict:
        """Returns the sequences to be run"""
        return self.sequences
