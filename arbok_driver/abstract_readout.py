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
        save_results: bool = True,
        params: dict = {}
    ):
        """
        Constructor method of `AbstractReadout`
        
        Args:
            name (str): name of readout
            sequence (ReadSequence): Sequence generating the given readout
            attr_name (str): Name of the attribute as which the readout will be
                added in the signal
            save_results (bool, optional): Whether to save the results
            params (dict, optional): Parameters to be added to the read sequence
        """
        self.name = name
        self.sequence = sequence
        self.attr_name = attr_name
        self.save_results = save_results
        self.observables = {}

        ### Parameters are added to the sequence with the readout prefix
        self.add_qc_params_from_config(params)

    def qua_declare_variables(self):
        """Declares all necessary qua variables for readout"""
        for observable_name, observable in self.observables.items():
            logging.debug(
                "Declaring variables for observable %s on abstract readout %s",
                observable_name, self.name)
            observable.qua_var = qua.declare(observable.qua_type)
            observable.qua_stream = qua.declare_stream(
                adc_trace = observable.adc_trace)

    def qua_save_variables(self):
        """Saves the qua variables of all observables in this readout"""
        if self.save_results:
            for observable_name, observable in self.observables.items():
                logging.debug(
                    "Saving variables of observable %s on abstract readout %s",
                    observable_name, self.name)
                qua.save(observable.qua_var, observable.qua_stream)

    def qua_save_streams(self):
        """Saves acquired results to qua stream"""
        if self.save_results:
            for observable_name, observable in self.observables.items():
                logging.debug(
                    "Saving streams of observable %s on abstract readout %s",
                    observable_name, self.name)
                sweep_size = self.sequence.measurement.sweep_size
                buffer = observable.qua_stream.buffer(sweep_size)
                buffer.save(f"{observable.full_name}_buffer")
        else:
            logging.debug(
                "NOT saving streams of abstract readout %s", self.name)

    def qua_measure_and_save(self):
        """Measures ans saves the result of the given readout"""
        self.qua_measure()
        self.qua_save_variables()

    def add_qc_params_from_config(self, param_dict: dict) -> None:
        """
        Adds the given parameters to the sequence with the readout prefix
        
        Args:
            params (list): List of parameter names to be added to the sequence
        """
        full_params = {f'{self.name}__{k}': v for k, v in param_dict.items()}
        self.sequence.add_qc_params_from_config(full_params)
        for param_name, conf in param_dict.items():
            if 'value' in conf:
                parameter = getattr(self.sequence, f"{self.name}__{param_name}")
                setattr(self, param_name, parameter)

    def get_params_with_prefix(self, prefix: str) -> dict:
        """
        Finds the element parameters with the given prefix
        
        Args:
            prefix (str): Prefix of the element parameters
        
        Returns:
            dict: Dictionary with elemets as keys and parameters as values
        """
        all_params = self.sequence.parameters
        full_prefix = f"{self.name}__{prefix}"
        param_names = [x for x in all_params if full_prefix in x]
        element_list = [x.split(full_prefix)[-1].split('_')[-1] for x in param_names]
        return {e: all_params[p] for e, p in zip(element_list, param_names)}

    def get_signals_and_observables(self, prefix: str) -> dict:
        """
        Returns observables found at the path given from the param storing it.
        Works very similarly to `get_params_with_prefix`. First finds params
        with the given prefix and then tries to find the observable from the
        path stored in the parameter

        Args:
            prefix (str): Prefix of the element parameters
        
        Returns:
            dict: Dictionary with signals as keys and observables
        """
        obs_dict = {}
        for signal, obs in self.get_params_with_prefix(prefix).items():
            obs_dict[signal] = self._find_observable_from_path(obs())
        return obs_dict

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
            try:
                current_obj = getattr(current_obj, attr_name)
            except AttributeError as exc:
                raise AttributeError(
                    f'Attribute {attr_name} not found in {current_obj.name}'
                ) from exc
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
        return list(dict.fromkeys(qm_elements))

    @abstractmethod
    def qua_measure(self):
        """Measures the qua variables for the given abstract readout"""
