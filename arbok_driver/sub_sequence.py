""" Module containing Sequence class """

import warnings
import copy
from typing import List, Union, Optional
import logging
import math

import numpy as np

from qcodes.instrument import InstrumentBase, InstrumentModule
from qcodes.validators import Arrays

from qm import SimulationConfig, generate_qua_script
from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.simulate.credentials import create_credentials
from qm.qua import (
    program, infinite_loop_, pause, stream_processing, 
    declare, for_, assign, play, amp, fixed
)

from qualang_tools.loops import from_array

from .sample import Sample
from .sequence_base import SequenceBase
from .sequence_parameter import SequenceParameter
from . import utils

class SubSequence(SequenceBase, InstrumentModule):
    """
    Class describing a subsequence of a QUA programm (e.g Init, Control, Read).
    TODO: should inherit from InstrumentModule!
    """
    def __init__(self, name: str, sample: Sample,
                 param_config: Union[dict, None] = None, **kwargs):
        """
        Constructor class for `Program` class
        
        Args:
            name (str): Name of the program
            sample (Sample): Sample class describing phyical device
            param_config (dict): Dictionary containing all device parameters
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(name = name, sample = sample, param_config = param_config, **kwargs)
        super(SequenceBase, self).__init__(name)
        self.elements = self.sample.elements
        self._gettables = []

    @property
    def gettables(self) -> list:
        """
        List of `GettableParameter`s that can be registered for acquisition
        in a `program`
        """
        return self._gettables
    
    def qua_declare(self):
        """Contains raw QUA code to initialize the qua variables"""
        ...

    def qua_sequence(self):
        """Contains raw QUA code to define the pulse sequence"""
        ...
    
    def qua_stream(self):
        """Contains raw QUA code to define streams"""
        ...