""" Module containing Sequence class """
import logging

from .sample import Sample
from .sequence import Sequence
from .sequence_base import SequenceBase

class SubSequence(SequenceBase):
    """
    Class describing a subsequence of a QUA programm (e.g Init, Control, Read). 
    """
    def __init__(
            self,
            name: str,
            sample: Sample,
            param_config: dict | None = None,
            **kwargs
            ):
        """
        Constructor class for `Program` class
        
        Args:
            name (str): Name of the program
            sample (Sample): Sample class describing phyical device
            param_config (dict): Dictionary containing all device parameters
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(name, sample, param_config, **kwargs)

    @property
    def parent_sequence(self):
        """Returns parent (sub) sequence"""
        return self.find_parent_sequence()

    @parent_sequence.setter
    def parent_sequence(self, parent):
        self._parent_sequence = parent

    def find_parent_sequence(self):
        """Recursively searches the parent sequence"""
        if isinstance(self._parent_sequence, Sequence):
            return self._parent_sequence
        elif self._parent_sequence is None:
            return self
        else:
            return self._parent_sequence.find_parent_sequence()

    def get_sequence_path(self, path: str = None):
        """Returns the path of subsequences up to the parent sequence"""
        if path is None:
            path = ""
        if isinstance(self._parent_sequence, Sequence):
            return f"{self._parent_sequence.name}__{self.name}__{path}" 
        elif self._parent_sequence is None:
            return f"{self.name}__{path}"
        else:
            return self._parent_sequence.get_sequence_path(f"{self.name}__{path}")