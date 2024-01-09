"""Module containing abstract class for dependent readouts"""
from abc import ABC, abstractmethod
import logging

from qm import qua
from .read_sequence import ReadSequence
from .observable import ObservableBase

class AbstractReadout(ABC):
    """
    Abstract base class for abstract readouts. This base class handles qua
    variable and stream declaration, saving and streaming. The child class only
    needs to handle the abstract method `qua_measure`
    """
    def __init__(
        self,
        name: str,
        sequence: ReadSequence,
        attr_name: str,
    ):
        """
        Constructor method of `AbstractReadout`
        
        Args:
            name (str): name of readout
            sequence (ReadSequence): Sequence generating the given readout
            attr_name (str): Name of the attribute as which the readout will be
                added in the signal
        """
        self.name = name
        self.sequence = sequence
        self.attr_name = attr_name
        self.observables = {}

    def qua_declare_variables(self):
        """Declares all necessary qua variables for readout"""
        for observable_name, observable in self.observables.items():
            logging.debug(
                "Declaring variables for observable %s on abstract readout %s",
                observable_name, self.name)
            observable.qua_var = qua.declare(observable.qua_type)
            observable.qua_stream = qua.declare_stream()

    def qua_save_variables(self):
        """Saves the qua variables of all observables in this readout"""
        for observable_name, observable in self.observables.items():
            logging.debug(
                "Saving variables of observable %s on abstract readout %s",
                observable_name, self.name)
            qua.save(observable.qua_var, observable.qua_stream)

    def qua_save_streams(self):
        """Saves acquired results to qua stream"""
        for observable_name, observable in self.observables.items():
            logging.debug(
                "Saving streams of observable %s on abstract readout %s",
                observable_name, self.name)
            sweep_size = self.sequence.parent_sequence.sweep_size
            buffer = observable.qua_stream.buffer(sweep_size)
            buffer.save(f"{observable.full_name}_buffer")
            observable.qua_stream.save_all(observable.full_name)

    def qua_measure_and_save(self):
        """Measures ans saves the result of the given readout"""
        self.qua_measure()
        self.qua_save_variables()

    def _find_observable_from_path(self, attr_path: str) -> ObservableBase:
        """
        Returns the observable from a given path from a given string. If the
        string leads to an AbstractReadout it is being tried to find a single
        observable associated to that AbstractReadout
        
        Args:
            attr_path (str): Path to the given observable relative to the
                ReadSequence
        
        Returns:
            ObservableBase: The found observable from the given path
        """
        attributes = attr_path.split('.')
        current_obj = self.sequence
        for attr_name in attributes:
            current_obj = getattr(current_obj, attr_name)
        if isinstance(current_obj, AbstractReadout):
            current_obj = current_obj.observable
        if not isinstance(current_obj, ObservableBase):
            raise ValueError(
                f"The given path {attr_path} yields a {type(current_obj)}-type",
                "not a child class of ObservableBase"
            )
        return current_obj

    def get_qm_elements_from_observables(self):
        """
        Collects all qm read elements from the readouts observables and their
        signal. Duplicates are removed

        Returns:
            list: List of read elements used in observables
        """
        qm_elements = []
        for _, obs in self.observables.items():
            qm_elements += obs.qm_elements
        return list(set(qm_elements))

    @abstractmethod
    def qua_measure(self):
        """Measures the qua variables for the given abstract readout"""
