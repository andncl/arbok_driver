""" Module containing Sequence class """
import logging
from typing import Any

from .sample import Sample
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
            sequence_config: dict | None = None,
            check_step_requirements: bool = False,
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
        super().__init__(
            parent, name, sample, sequence_config, check_step_requirements, **kwargs)
        self.parent.add_subsequence(self)

    @property
    def measurement(self):
        """Returns parent (sub) sequence"""
        return self.find_measurement()

    def find_measurement(self):
        """Recursively searches the parent sequence"""
        if self.parent.__class__.__name__ == 'Measurement':
            return self.parent
        elif isinstance(self.parent, SubSequence):
            return self.parent.find_measurement()
        else:
            raise ValueError(
                "Parent sequence must be of type Sequence"
                f"Is of type {self.parent.__class__.__name__}")

    def get_sequence_path(self, path: str = None) -> str:
        """Returns the path of subsequences up to the parent sequence"""
        if path is None:
            path = ""
        if self.parent.__class__.__name__ == 'Measurement':
            return f"{self.parent.short_name}__{self.short_name}__{path}"
        elif self.parent is None:
            return f"{self.short_name}__{path}"
        else:
            return self.parent.get_sequence_path(f"{self.short_name}__{path}")

    def _add_subsequence(
        self,
        name: str,
        subsequence: SequenceBase | str,
        sequence_config: dict = None,
        insert_sequences_into_name_space: dict = None,
        **kwargs) -> None:
        """Adds a subsequence to the sequence"""
        if subsequence == 'default':
            subsequence = SubSequence
        if not issubclass(subsequence, SubSequence):
            raise TypeError(
                "Subsequence must be of type SubSequence or str: 'default'")
        seq_instance = subsequence(
            parent = self,
            name = name,
            sample = self.sample,
            sequence_config = sequence_config,
            **kwargs
            )
        setattr(self, name, seq_instance)
        if insert_sequences_into_name_space is not None:
            name_space = insert_sequences_into_name_space
            name_space[name] = seq_instance
        return seq_instance

    def __getattr__(self, key: str) -> Any:
        """Returns parameter from self. If parameter is not found in self, 
        searches parent sequence"""
        if key in self.parameters:
            return self.parameters[key]
        elif self.measurement is None:
            raise AttributeError(
                f"Sub-sequence {self.name} does not have attribute {key}")
        else:
            return self._return_measurement_parameters(key)

    def _return_measurement_parameters(self, key: str) -> Any:
        """Returns attribute from parent sequence"""
        logging.debug("Searching parent sequence %s for parameter %s",
                        self.measurement.name, key)
        if key in self.measurement.parameters:
            return self.measurement.parameters[key]
        raise AttributeError(
            f"Parameter {key} not found in {self.measurement.name}")
