""" Module containing Sequence class """
import logging
from typing import Any

from .sample import Sample
from .sequence import Sequence
from .sequence_base import SequenceBase

class SubSequence(SequenceBase):
    """
    Class describing a subsequence of a QUA programm (e.g Init, Control, Read). 
    """
    def __init__(
            self,
            parent,
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
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(parent, name, sample, param_config, **kwargs)
        self.parent.add_subsequence(self)

    @property
    def parent_sequence(self):
        """Returns parent (sub) sequence"""
        return self.find_parent_sequence()

    def find_parent_sequence(self):
        """Recursively searches the parent sequence"""
        if isinstance(self.parent, Sequence):
            return self.parent
        elif isinstance(self.parent, SubSequence):
            return self.parent.find_parent_sequence()
        else:
            raise ValueError("Parent sequence must be of type Sequence")

    def get_sequence_path(self, path: str = None) -> str:
        """Returns the path of subsequences up to the parent sequence"""
        if path is None:
            path = ""
        if isinstance(self.parent, Sequence):
            return f"{self.parent.name}__{self.name}__{path}"
        elif self.parent is None:
            return f"{self.name}__{path}"
        else:
            return self.parent.get_sequence_path(f"{self.name}__{path}")

    def __getattr__(self, key: str) -> Any:
        """Returns parameter from self. If parameter is not found in self, 
        searches parent sequence"""
        if key in self.parameters:
            return self.parameters[key]
        elif self.parent_sequence is None:
            raise AttributeError(
                f"Sub-sequence {self.name} does not have attribute {key}")
        else:
            return self._return_parent_sequence_parameters(key)

    def _return_parent_sequence_parameters(self, key: str) -> Any:
        """Returns attribute from parent sequence"""
        logging.debug("Searching parent sequence %s for parameter %s",
                        self.parent_sequence.name, key)
        if key in self.parent_sequence.parameters:
            return self.parent_sequence.parameters[key]
        raise AttributeError(
            f"Parameter {key} not found in {self.parent_sequence.name}")
