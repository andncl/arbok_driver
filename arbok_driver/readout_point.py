"""Module containing ReadoutPoint class"""
import logging
from abc import ABC, abstractmethod

from qm import qua
from .observable import Observable

class ReadoutPoint(ABC):
    """
    Class managing voltage signal readout points of OPX
    """
    def __init__(
            self,
            point_name: str,
            signal: any,
            config: dict,
            ):
        """
        Constructor method of ReadoutPoint class
        
        Args:
            point_name (str): Name of readout point
            signal (Signal): Signal corresponding to readout point
            config (dict): List of readout points
        """
        self.signal = signal
        self.sequence = self.signal.sequence
        self.point_name = point_name
        self.name = f"{self.signal.name}__{point_name}"
        self.config = config
        if 'save_values' in self.config:
            self.save_values = self.config['save_values']
        else:
            self.save_values = True
        self.description = self.config["desc"]
        self._observables_names = self.config["observables"]

        self.observables = {}
        self.valid_observables = ('I', 'Q', 'IQ')
        self._add_qua_variable_attributes(self.signal.readout_elements)

    @abstractmethod
    def qua_measure(self):
        """Measures I and Q at the given read point"""

    def qua_declare_variables(self):
        """Declares all neccessary qua variables"""
        for observable_name, observable in self.observables.items():
            observable.qua_var = qua.declare(qua.fixed)
            observable.qua_stream = qua.declare_stream()
            logging.debug(
                "Assigned qua-var and qua-stream %s to point %s",
                observable_name, self.name)

    def _add_qua_variable_attributes(self, readout_elements: dict):
        """
        Adds attributes to the readout point that will later store the qua 
        variables. This is primarily done to make all streams and qua varables
        visible before we ask to generate the qua script
        
        Args:
            readout_elements (dict): Readout elements from which to read
        """
        for element_name, element in readout_elements.items():
            for observable_name in self.config["observables"]:
                observable = Observable(
                    element_name = element_name,
                    element = element,
                    observable_name = observable_name,
                    readout_point = self
                )
                self.observables[observable.full_name] = observable
                setattr(self, observable.name, observable)
                logging.debug(
                    "Added observable %s as qua var and stream to point %s",
                    observable.name, self.name)

    def _check_observable_validity(self, observable):
        """Checks if observable is valid"""
        if observable not in self.valid_observables:
            raise ValueError(
                f"Given observable {observable} not valid."
                f"Must be in {self.valid_observables}")

    def qua_measure_and_save(self):
        """Measures and saves qua variables"""
        self.qua_measure()
        self.qua_save_variables()

    def qua_save_variables(self):
        """Saves streams after measurement"""
        if not self.save_values:
            logging.debug("Values of point %s will not be saved.", self.name)
            return
        for obs_name, observable in self.observables.items():
            logging.debug(
                "Saving qua var of observable %s to its stream", obs_name)
            qua.save(observable.qua_var, observable.qua_stream)

    def _check_IQ_qua_vars(self, name):
        """
        Validates that mandatory attributes for IQ measurements that store qua
        variables exist
        
        Args:
            name (str): Name of the readout element
        """
        if not hasattr(self, f"{name}_I") or not hasattr(self, f"{name}_I"):
            raise AttributeError(
                f"{self.name} does not have I and Q variable"
                )

    def qua_save_streams(self):
        """Saves streams and buffers of streams"""
        sweep_size = self.signal.sequence.measurement.sweep_size
        if not self.save_values:
            logging.debug("Values of point %s will not be streamed.", self.name)
            return
        for obs_name, observable in self.observables.items():
            logging.debug("Saving stream %s", obs_name)
            buffer = observable.qua_stream.buffer(sweep_size)
            buffer.save(f"{observable.full_name}_buffer")
