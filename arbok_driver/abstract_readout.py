"""Module containing abstract class for dependent readouts"""
from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import TYPE_CHECKING
from functools import reduce

from qm import qua

from .gettable_parameter import GettableParameter
from .signal import Signal
if TYPE_CHECKING:
    from .read_sequence import ReadSequence

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
        self.read_sequence: ReadSequence = read_sequence
        self.signal: Signal = signal
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

    def qua_measure_and_save(self, *args, **kwargs):
        """Measures and saves the result of the given readout"""
        self.qua_measure(*args, **kwargs)
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
                self.parameters[param_name] = parameter

    def get_gettable_from_path(self, attr_path: str) -> GettableParameter:
        """
        Returns the gettable from a given path from a given string. If the
        string leads to an AbstractReadout it is being tried to find a single
        gettable associated to that AbstractReadout
        
        Args:
            attr_path (str): Path to the given gettable relative to the
                ReadSequence with the format 'signal.gettable_name'
        
        Returns:
            gettable: The found gettable from the given path

        Raises:
            ValueError: If the path is not in the format 'signal.gettable_name'
            KeyError: If the signal or gettable is not found in the read sequence
            TypeError: If the found object is not a child class of gettable
        """
        attributes = attr_path.split('.')
        if len(attributes) == 2:
            signal_name, gettable_name = attributes
            return get_gettable_from_read_sequence(
                self.read_sequence, signal_name, gettable_name)

        if len(attributes) > 2:
            signal_name, gettable_name = attributes[-2:]
            sub_sequence_path = attributes[:-2]
            try:
                read_sequence = reduce(
                    getattr, sub_sequence_path, self.read_sequence.measurement)
            except AttributeError as e:
                raise ValueError(
                    f"Error resolving given path: '{attr_path}' for "
                    f" abstract readout {self.name}. Check error above."
                ) from e
            return get_gettable_from_read_sequence(
                read_sequence, signal_name, gettable_name
            )
        else:
            raise ValueError(
                f"Path {attr_path} does not lead to a single gettable. "
                "Please provide a path with the format 'signal.gettable_name' "
                "or 'sub_sequence_path.signal.gettable_name'."
            )

### REVIEW ALL OF THE BELOW METHODS

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

def get_gettable_from_read_sequence(
        read_sequence: ReadSequence,
        signal_name: str,
        gettable_name: str,
        ) -> GettableParameter:
    """
    Helper method to get a gettable from this readout. This is used

    Args:
        read_sequence (ReadSequence): The read sequence to get the gettable from
        signal_name (str): Name of the signal
        gettable_name (str): Name of the gettable
    
    Raises:
        KeyError: If the signal or gettable is not found in the read sequence
        KeyError: If the GettableParameter is not found in the signal
        ValueError: If the found object is not a child class of GettableParameter
    """
    if signal_name not in read_sequence.signals:
        raise KeyError(
            f"Signal {signal_name} not found in read sequence"
            f" '{read_sequence.name}'. Available signals: "
            f"{read_sequence.signals.keys()}"
        )
    signal: Signal = read_sequence.signals[signal_name]
    if gettable_name not in signal.gettables:
        raise KeyError(
            f"Gettable {gettable_name} not found in signal {signal.name}"
            f" of read sequence '{read_sequence.name}'. "
            f"Available gettables: {signal.gettables.keys()}"
        )
    gettable: GettableParameter = signal.gettables[gettable_name]
    if not isinstance(gettable, GettableParameter):
        raise ValueError(
            f"The given path {signal_name}.{gettable_name} yields a ",
            f"{type(gettable)}-type, not a child class of gettable"
        )
    return gettable
