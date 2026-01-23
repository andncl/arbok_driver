"""Module containing abstract class for dependent readouts"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
import logging
from typing import Generic, Sequence, TYPE_CHECKING, Type, TypeVar

from qm import qua

from .parameter_class import ParameterClass
from .parameters.gettable_parameter import GettableParameter
from .parameters.gettable_parameter_base import GettableParameterBase
from .parameters.gettable_parameter_multi import GettableParameterMulti
from .import path_finders
from .signal import Signal

if TYPE_CHECKING:
    from .parameters.sequence_parameter import SequenceParameter
    from .read_sequence import ReadSequence
    from qcodes.parameters import Parameter

P = TypeVar("P", bound=ParameterClass)

@dataclass(frozen = True)
class EmptyParameterClass(ParameterClass):
    pass

class AbstractReadout(Generic[P], ABC):
    """
    Abstract base class for abstract readouts. This base class handles qua
    variable and stream declaration, saving and streaming. The child class only
    needs to handle the abstract method `qua_measure`
    """
    PARAMETER_CLASS: Type[P]
    arbok_params: P

    def __init__(
        self,
        name: str,
        read_sequence: ReadSequence,
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
        self.read_sequence: ReadSequence = read_sequence
        self.signal: Signal = signal
        self.save_results = save_results
        self._parameters: dict[str, SequenceParameter] = {}
        self._gettables: dict[str, GettableParameterBase] = {}

        ### Parameters are added to the sequence with the readout prefix
        if parameters is not None:
            self.add_qc_params_from_config(parameters)
            self.arbok_params = self.map_arbok_params()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "PARAMETER_CLASS" not in cls.__dict__:
            cls.PARAMETER_CLASS = EmptyParameterClass  # type: ignore[assignment]

    @abstractmethod
    def qua_measure(self):
        """Measures the qua variables for the given abstract readout"""
        raise NotImplementedError(
            "Abstract method 'qua_measure' not implemented in child class"
        )

    @property
    def parameters(self) -> dict[str, SequenceParameter]:
        """Returns the parameters of the readout"""
        return self._parameters

    @property
    def gettables(self) -> dict[str, GettableParameterBase]:
        """Returns the gettables of the readout"""
        return self._gettables

    def create_gettable(
        self,
        gettable_name: str,
        var_type: type[int | bool | qua.fixed]
        ) -> GettableParameter:
        """
        Creates a new GettableParameter for the AbstractReadout.
        The gettable is added to the read sequence as a parameter and registered
          under the given name.
        
        Args:
            gettable_name (str): Name of the gettable to be created
            var_type (int | bool | qua.fixed): Type of the gettable variable

        Returns:
            GettableParameter: The created gettable parameter
        """
        gettable = self.read_sequence.add_parameter(
            parameter_class = GettableParameter,
            name = gettable_name,
            read_sequence = self.read_sequence,
            var_type = var_type
        )
        self.signal.add_gettable(gettable)
        self._gettables[gettable.full_name] = gettable
        return gettable

    def create_multi_gettable(
        self,
        gettable_name: str,
        var_type: type[int | bool | qua.fixed],
        internal_setpoints: Sequence[Parameter]
    ) -> GettableParameterMulti:
        """
        Creates a new GettableParameterMulti for the AbstractReadout.
        The gettable is added to the read sequence as a parameter and registered
        under the given name.
        
        Args:
            gettable_name (str): Name of the gettable to be created
            var_type (int | bool | qua.fixed): Type of the gettable variable
            internal_setpoints (internal_setpoints: Sequence[Parameter]):
                setpoints for this multi gettable

        Returns:
            GettableParameter: The created gettable parameter
        """
        gettable = self.read_sequence.add_parameter(
            parameter_class = GettableParameterMulti,
            name = gettable_name,
            read_sequence = self.read_sequence,
            var_type = var_type,
            internal_setpoints = internal_setpoints
        )
        self.signal.add_gettable(gettable)
        self._gettables[gettable.full_name] = gettable
        return gettable

    def qua_declare_variables(self) -> None:
        """Declares all necessary qua variables for readout"""
        for gettable_name, gettable in self.gettables.items():
            logging.debug(
                "Declaring variables for gettable %s on abstract readout %s",
                gettable_name, self.name)
            gettable.qua_declare_variables()

    def qua_save_variables(self) -> None:
        """Saves the qua variables of all gettables in this readout"""
        if self.save_results:
            for gettable_name, gettable in self.gettables.items():
                logging.debug(
                    "Saving variables of gettable %s on abstract readout %s",
                    gettable_name, self.name)
                gettable.qua_save_variables()

    def qua_save_streams(self) -> None:
        """Saves acquired results to qua stream"""
        if self.save_results:
            for gettable_name, gettable in self.gettables.items():
                logging.debug(
                    "Saving streams of gettable %s on abstract readout %s",
                    gettable_name, self.name)
                gettable.qua_save_streams()
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
        self.read_sequence.add_qc_params_from_config(full_params)

    def map_arbok_params(self) -> ParameterClass:
        """
        Adds the parameters to a ParameterClass instance

        Returns:
            ParameterClass: ParameterClass with references to all needed params
        """
        if not hasattr(self, "PARAMETER_CLASS"):
            raise AttributeError(
                f"AbstractReadout {self.name} does not have a PARAMETER_CLASS"
                " class-attribute"
            )
        arg_names = [f.name for f in fields(self.PARAMETER_CLASS) if f.init]
        arg_names_full = [
            f'{self.name}__{f}' for f in arg_names
            ]
        init_dict_full = self.read_sequence.get_parameters_and_maps(arg_names_full)
        init_dict = self.read_sequence.measurement.get_parameters_and_maps(arg_names)
        init_dict.update(self.read_sequence.get_parameters_and_maps(arg_names))
        init_dict.update(
            {n.split(f"{self.name}__")[1]: p for n, p in init_dict_full.items()}
        )
        return self.PARAMETER_CLASS(**init_dict)
        

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
        try:
            if len(attributes) == 2:
                signal_name, gettable_name = attributes
                return path_finders.get_gettable_from_read_sequence(
                    self.read_sequence, signal_name, gettable_name)
            elif len(attributes) > 2:
                return path_finders.get_gettable_from_measurement_path(
                    self.read_sequence.measurement, attributes
                )
            else:
                raise ValueError(
                    f"Path {attr_path} does not lead to a single gettable. "
                    "Please provide a path with the format 'signal.gettable_name' "
                    "or 'sub_sequence_path.signal.gettable_name'."
                )
        except AttributeError as e:
            raise ValueError(
                f"Error resolving given path: '{attr_path}' for "
                f" abstract readout {self.name}. CHECK ERROR ABOVE!"
            ) from e
