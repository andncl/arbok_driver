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