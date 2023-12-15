"""Module containing abstract class for dependent readouts"""
from abc import ABC, abstractmethod
import logging

from qm import qua
from .read_sequence import ReadSequence

class AbstractReadout(ABC):
    """Abstract base class for dependent readouts"""
    def __init__(
        self,
        name: str,
        sequence: ReadSequence,
        attr_name: str,
        signal_name: str,
    ):
        """
        Constructor method of `AbstractReadout`
        
        Args:
            name (str): name of readout
            config (dict):
            sequence (arbok_driver.ReadSequence): 
        """
        self.name = name
        self.sequence = sequence
        self.attr_name = attr_name
        self.signal = getattr(self.sequence, signal_name)
        self.signal.add_abstract_readout(self, f"{self.attr_name}")
        #self.sequence.abstract_readouts[f"{self.signal.name}__{self.attr_name}"] = self
        self.stream_list = []
        self.qua_variable_names = []
        self.qua_stream_names = []
        self.qua_buffer_names = []


    @abstractmethod
    def qua_declare_variables(self):
        """Declares all necessary qua variables for readout"""

    @abstractmethod
    def qua_measure(self):
        """Measures the qua variables for the given abstract readout"""
    @abstractmethod
    def qua_save_variables(self):
        """Saves acquired results to qua stream"""

    @abstractmethod
    def qua_save_streams(self):
        """Saves acquired results to qua stream"""

    def qua_measure_and_save(self):
        """Measures ans saves the result of the given readout"""
        self.qua_measure()
        self.qua_save_variables()

    def _check_type_and_make_list(
        self, argument: any, arg_type: type):
        """
        Checks validity of constructor arguments and returns them in correct 
        shape
        
        Args:
            charge_readouts (str, list): list or str containing charge readouts
                to refer to
            threshold (float, list): contains threshold value(s)
        """
        if isinstance(argument, arg_type):
            argument = [argument]
        elif not isinstance(argument, list):
            raise ValueError(
                f"Given argument must be type {arg_type} or list is: ",
                f"{type(argument)}")
        return argument

    def _find_signal_attribute(self, attr_path: str):
        """Returns the attribute from a given string"""
        attributes = attr_path.split('.')
        current_obj = self.sequence
        for attr_name in attributes:
            current_obj = getattr(current_obj, attr_name)
        if not isinstance(current_obj, qua._dsl._Variable):
            try:
                current_obj = current_obj()
            except TypeError:
                pass
        if isinstance(current_obj, qua._dsl._Variable):
            return current_obj
        else:
            raise ValueError(
                f"The given path {attr_path} yields a {type(current_obj)}-type")

    def _save_qua_stream_variable(self, qua_stream):
        """
        Saves the given stream once as a whole and once with a buffer that
        matches the given measurement loop
        
        Args:
            qua_stream (qua._dsl._ResultSource): Stream to save
        """
        sweep_size = self.sequence.parent_sequence.sweep_size
        qua_stream.buffer(sweep_size).save(f"{self.name}_buffer")
        qua_stream.save_all(self.name)