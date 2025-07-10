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

    def add_subsequences_from_dict(
            self,
            subsequence_dict: dict,
            namespace_to_add_to: dict = None) -> None:
        """
        Adds subsequences to the sequence from a given dictionary

        Args:
            subsequence_dict (dict): Dictionary containing the subsequences
        """
        super()._add_subsequences_from_dict(
            default_sequence = SubSequence,
            subsequence_dict = subsequence_dict,
            namespace_to_add_to = namespace_to_add_to
        )

    def find_measurement(self):
        """Recursively searches the parent sequence"""
        if self.parent.__class__.__name__ == 'Measurement':
            return self.parent
        elif isinstance(self.parent, SubSequence):
            return self.parent.find_measurement()
        else:
            raise ValueError(
                "Parent sequence must be of type Sequence. "
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
