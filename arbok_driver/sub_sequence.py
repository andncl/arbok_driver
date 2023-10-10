""" Module containing Sequence class """

from .sample import Sample
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
        logging.debug("Set %s as parent of %s", parent.name, self.name)
        self._parent_sequence = parent

    def find_parent_sequence(self):
        """Recursively searches the parent sequence"""
        if isinstance(self._parent_sequence, Sequence):
            return self._parent_sequence
        elif self._parent_sequence is None:
            return self
        else:
            return self._parent_sequence.find_parent_sequence()
