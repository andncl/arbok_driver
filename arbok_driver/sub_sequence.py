""" Module containing Sequence class """
from __future__ import annotations
from abc import ABC
from dataclasses import fields
from typing import TYPE_CHECKING, Any
import logging
import warnings

from .parameter_class import ParameterClass
from .sequence_base import SequenceBase

if TYPE_CHECKING:
    from .measurement import Measurement

class SubSequence(SequenceBase, ABC):
    """
    Class describing a subsequence of a QUA program (e.g Init, Control, Read).

    ## Lifecycle hooks

    Override these methods to define your sequence logic:

    - ``fpga_sequence()`` — hardware-agnostic (works with any backend)
    - ``fpga_declare()`` — variable declarations
    - ``fpga_before_sequence()`` / ``fpga_after_sequence()`` — setup/teardown
    - ``fpga_stream()`` — stream processing

    ## Backend-specific overrides

    For logic that must differ per backend, use the double-underscore suffix
    with the backend name:

    - ``fpga_sequence__qua()`` — only runs when QuaBackend is active
    - ``fpga_sequence__sim()`` — only runs when SimBackend is active

    Resolution order (first match wins):
    1. ``fpga_<hook>__<backend.name>`` (backend-specific)
    2. ``fpga_<hook>`` (hardware-agnostic, if overridden)
    3. ``qua_<hook>`` (legacy, deprecated — QuaBackend only)
    4. Default ``fpga_<hook>`` (iterates child sub_sequences)
    """
    _enforce_parameter_class: bool = False
    def __init__(
            self,
            parent,
            name: str,
            sequence_config: dict | None = None,
            check_step_requirements: bool = False,
            **kwargs
            ):
        """
        Constructor class for `Program` class

        Args:
            name (str): Name of the program
            sequence_config (dict): Dictionary containing all device parameters
            check_step_requirements (bool): Whether to check step requirements
                for this subsequence
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(
            parent, name, sequence_config, check_step_requirements, **kwargs)
        self.parent.add_subsequence(self)
        self.arbok_params = self.map_arbok_params()

    @property
    def measurement(self) -> Measurement:
        """Returns parent (sub) sequence"""
        return self.find_measurement()

    # ──────────────────────────────────────────────────────────────────────
    # Hardware-agnostic lifecycle hooks (fpga_* prefix)
    # Override these for multi-backend support.
    # For backend-specific overrides, add __<backend_name> suffix.
    # ──────────────────────────────────────────────────────────────────────

    def fpga_sequence(self) -> None:
        """Hardware-agnostic sequence logic. Default delegates to children."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('sequence')

    def fpga_declare(self) -> None:
        """Variable declarations. Default delegates to children."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('declare')

    def fpga_before_sequence(self) -> None:
        """Hook run before the inner measurement loop. Default delegates to children."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('before_sequence')

    def fpga_after_sequence(self) -> None:
        """Hook run after the inner measurement loop. Default delegates to children."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('after_sequence')

    def fpga_stream(self) -> None:
        """Stream processing hook. Default delegates to children."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('stream')

    # ──────────────────────────────────────────────────────────────────────
    # Dispatch logic (inherited from SequenceBase)
    # ──────────────────────────────────────────────────────────────────────

    # ──────────────────────────────────────────────────────────────────────
    # Legacy QUA lifecycle hooks (backwards compatible)
    # ──────────────────────────────────────────────────────────────────────

    def qua_sequence(self):
        """Legacy hook — override fpga_sequence() or fpga_sequence__qua() instead."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('sequence')

    def qua_declare(self):
        """Legacy hook — override fpga_declare() or fpga_declare__qua() instead."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('declare')

    def qua_before_sequence(self):
        """Legacy hook — override fpga_before_sequence() instead."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('before_sequence')

    def qua_after_sequence(self):
        """Legacy hook — override fpga_after_sequence() instead."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('after_sequence')

    def qua_stream(self):
        """Legacy hook — override fpga_stream() instead."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('stream')

    def map_arbok_params(self) -> ParameterClass:
        """Maps required params for QUA code to arbok_params attribute"""
        arg_names = [f.name for f in fields(self.PARAMETER_CLASS) if f.init]
        init_dict = self.measurement.get_parameters_and_maps(arg_names)
        init_dict.update(self.get_parameters_and_maps(arg_names))
        return self.PARAMETER_CLASS(**init_dict)

    def add_subsequences_from_dict(
            self,
            subsequence_dict: dict,
            namespace_to_add_to: dict | None = None) -> None:
        """
        Adds subsequences to the sequence from a given dictionary

        Args:
            subsequence_dict (dict): Dictionary containing the subsequences
            namespace_to_add_to (dict): Namespace to add the registered
                subsequences to
        """
        class ContainerParameterClass(ParameterClass):
            pass

        class ContainerSubSequence(SubSequence):
            PARAMETER_CLASS = ContainerParameterClass
    
        super()._add_subsequences_from_dict(
            default_sequence = ContainerSubSequence,
            subsequence_dict = subsequence_dict,
            namespace_to_add_to = namespace_to_add_to
        )

    def find_measurement(self) -> Measurement:
        """Recursively searches the parent sequence"""
        if self.parent.__class__.__name__ == 'Measurement':
            return self.parent
        elif isinstance(self.parent, SubSequence):
            return self.parent.find_measurement()
        else:
            raise ValueError(
                "Parent sequence must be of type Sequence. "
                f"Is of type {self.parent.__class__.__name__}")

    def get_sequence_path(self, path: str | None = None) -> str:
        """Returns the path of subsequences up to the parent sequence"""
        if path is None:
            path = ""
        if self.parent.__class__.__name__ == 'Measurement':
            return f"{self.parent.short_name}__{self.short_name}__{path}"
        elif self.parent is None:
            return f"{self.short_name}__{path}"
        else:
            return self.parent.get_sequence_path(f"{self.short_name}__{path}")

    def _return_measurement_parameters(self, key: str) -> Any:
        """Returns attribute from parent sequence"""
        logging.debug("Searching parent sequence %s for parameter %s",
                        self.measurement.name, key)
        if key in self.measurement.parameters:
            return self.measurement.parameters[key]
        raise AttributeError(
            f"Parameter {key} not found in {self.measurement.name}")
