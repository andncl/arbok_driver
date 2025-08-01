"""Module containing abstract class for dependent readouts"""
from abc import ABC, abstractmethod
import logging

from qm import qua

from .observable import Observable
from .signal import Signal

class AbstractReadout(ABC):
    """
    Abstract base class for abstract readouts. This base class handles qua
    variable and stream declaration, saving and streaming. The child class only
    needs to handle the abstract method `qua_measure`
    """
    def __init__(
        self,
        name: str,
        read_sequence: 'ReadSequence',
        signal: Signal,
        save_results: bool = True,
        parameters: dict | None = None
    ):
        """
        Constructor method of `AbstractReadout`
        
        Args:
            name (str): name of readout
            read_sequence (ReadSequence): Sequence generating the given readout
            signal (Signal): Signal to be used in the readout
            save_results (bool, optional): Whether to save the results
            params (dict, optional): Parameters to be added to the read sequence

        Info:
            Parameters can be added via this abstract readout to the
            read sequence. The parameters are added with the prefix of the
            readout name. For example, if the readout is called 'my_readout'
            and the parameter is called 'my_param', it will be added to the
            read sequence as 'my_readout__my_param'. Parameters are declared
            only on the read sequence and not on the abstract readout.
            The naming convention prevents name clashes with other
            readouts of the same type. You would want to declare some readout
            attributes as parameters, e.g. the voltage points in order to
            sweep and modify them in real time.
        """
        self.name = name
        self.read_sequence = read_sequence
        self.signal = signal
        self.save_results = save_results
        self.observables = {}
        self.parameters = {}

        ### Parameters are added to the sequence with the readout prefix
        if parameters is not None:
            self.add_qc_params_from_config(parameters)

    @abstractmethod
    def qua_measure(self):
        """Measures the qua variables for the given abstract readout"""
        raise NotImplementedError(
            "Abstract method 'qua_measure' not implemented in child class"
        )

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
                sweep_size = self.read_sequence.measurement.sweep_size
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
        self.read_sequence.add_qc_params_from_config(full_params)
        for param_name, conf in param_dict.items():
            if 'initial_value' in conf:
                logging.debug(
                    "Adding parameter %s with initial value %s to read sequence"
                    " '%s'",
                    param_name, conf['initial_value'], self.read_sequence.name
                    )
                parameter = getattr(self.read_sequence, f"{self.name}__{param_name}")
                setattr(self, param_name, parameter)
                self.parameters[param_name] = parameter

    def get_observable_from_path(self, attr_path: str) -> Observable:
        """
        Returns the observable from a given path from a given string. If the
        string leads to an AbstractReadout it is being tried to find a single
        observable associated to that AbstractReadout
        
        Args:
            attr_path (str): Path to the given observable relative to the
                ReadSequence with the format 'signal.observable_name'
        
        Returns:
            Observable: The found observable from the given path

        Raises:
            ValueError: If the path is not in the format 'signal.observable_name'
            KeyError: If the signal or observable is not found in the read sequence
            TypeError: If the found object is not a child class of Observable
        """
        attributes = attr_path.split('.')
        if len(attributes) != 2:
            raise ValueError(
                f"Path {attr_path} does not lead to a single observable. "
                "Please provide a path with the format 'signal.observable_name'"
            )
        signal, observable_name = attributes
        if signal not in self.read_sequence.signals:
            raise KeyError(
                f"Signal {signal} not found in read sequence"
                f" '{self.read_sequence.name}'. Available signals: "
                f"{self.read_sequence.signals.keys()}"
            )
        signal = self.read_sequence.signals[signal]
        if observable_name not in signal.observables:
            raise KeyError(
                f"Observable {observable_name} not found in signal {signal.name}"
                f" of read sequence '{self.read_sequence.name}'. "
                f"Available observables: {signal.observables.keys()}"
            )
        observable = signal.observables[observable_name]
        if not isinstance(observable, Observable):
            raise ValueError(
                f"The given path {attr_path} yields a {type(observable)}-type",
                "not a child class of Observable"
            )
        return observable

### REVIEW ALL OF THE BELOW METHODS

    def get_params_with_prefix(self, prefix: str) -> dict:
        """
        Finds the element parameters with the given prefix
        
        Args:
            prefix (str): Prefix of the element parameters
        
        Returns:
            dict: Dictionary with elemets as keys and parameters as values
        """
        all_params = self.read_sequence.parameters
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
            obs_dict[signal] = self.get_observable_from_path(obs())
        return obs_dict

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

