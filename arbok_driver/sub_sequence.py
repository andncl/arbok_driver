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

    Subclasses should implement either:
    - ``fpga_sequence()`` for hardware-agnostic code (works with any backend)
    - ``qua_sequence()`` for QUA-specific code (legacy, QuaBackend only)

    If both are defined, ``fpga_sequence()`` takes priority when a non-QUA
    backend is active. The QUA backend uses ``qua_sequence()`` if defined,
    falling back to ``fpga_sequence()`` otherwise.
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
    # Override these for multi-backend support
    # ──────────────────────────────────────────────────────────────────────

    def fpga_sequence(self) -> None:
        """Hardware-agnostic sequence using arbok.* operations.

        Override this method to write sequences that work with any backend
        (QUA, simulation, etc.). Uses arbok.play(), arbok.wait(), etc.

        Default implementation delegates to child sub_sequences.
        """
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch_fpga_sequence()

    def fpga_declare(self) -> None:
        """Hardware-agnostic variable declaration hook.

        Override to declare variables needed for your sequence using
        arbok.declare() etc. Default delegates to children.
        """
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch_fpga_declare()

    def fpga_before_sequence(self) -> None:
        """Hardware-agnostic hook run before the inner measurement loop.

        Default delegates to children.
        """
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch_fpga_before_sequence()

    def fpga_after_sequence(self) -> None:
        """Hardware-agnostic hook run after the inner measurement loop.

        Default delegates to children.
        """
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch_fpga_after_sequence()

    def fpga_stream(self) -> None:
        """Hardware-agnostic stream processing hook.

        Default delegates to children.
        """
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch_fpga_stream()

    # ──────────────────────────────────────────────────────────────────────
    # Dispatch logic
    # ──────────────────────────────────────────────────────────────────────

    def _dispatch_fpga_sequence(self) -> None:
        """Dispatch to fpga_sequence or qua_sequence based on backend."""
        from .backends.qua_backend import QuaBackend

        has_fpga = type(self).fpga_sequence is not SubSequence.fpga_sequence
        has_qua = type(self).qua_sequence is not SubSequence.qua_sequence

        if has_fpga:
            if self.check_step_requirements:
                self.measurement.qua_check_step_requirements(self.fpga_sequence)
            else:
                self.fpga_sequence()
        elif has_qua:
            if not isinstance(self.backend, QuaBackend):
                raise NotImplementedError(
                    f"SubSequence '{self.name}' only defines qua_sequence() "
                    f"which is not compatible with {type(self.backend).__name__}. "
                    f"Implement fpga_sequence() for hardware-agnostic operation."
                )
            if self.check_step_requirements:
                self.measurement.qua_check_step_requirements(self.qua_sequence)
            else:
                self.qua_sequence()
        else:
            if self.check_step_requirements:
                self.measurement.qua_check_step_requirements(self.fpga_sequence)
            else:
                self.fpga_sequence()

    def _dispatch_fpga_declare(self) -> None:
        """Dispatch to fpga_declare or qua_declare."""
        from .backends.qua_backend import QuaBackend

        has_fpga = type(self).fpga_declare is not SubSequence.fpga_declare
        has_qua = type(self).qua_declare is not SubSequence.qua_declare

        if has_fpga:
            self.fpga_declare()
        elif has_qua:
            self.qua_declare()
        else:
            self.fpga_declare()

    def _dispatch_fpga_before_sequence(self) -> None:
        """Dispatch to fpga_before_sequence or qua_before_sequence."""
        has_fpga = type(self).fpga_before_sequence is not SubSequence.fpga_before_sequence
        has_qua = type(self).qua_before_sequence is not SubSequence.qua_before_sequence

        if has_fpga:
            self.fpga_before_sequence()
        elif has_qua:
            self.qua_before_sequence()
        else:
            self.fpga_before_sequence()

    def _dispatch_fpga_after_sequence(self) -> None:
        """Dispatch to fpga_after_sequence or qua_after_sequence."""
        has_fpga = type(self).fpga_after_sequence is not SubSequence.fpga_after_sequence
        has_qua = type(self).qua_after_sequence is not SubSequence.qua_after_sequence

        if has_fpga:
            self.fpga_after_sequence()
        elif has_qua:
            self.qua_after_sequence()
        else:
            self.fpga_after_sequence()

    def _dispatch_fpga_stream(self) -> None:
        """Dispatch to fpga_stream or qua_stream."""
        has_fpga = type(self).fpga_stream is not SubSequence.fpga_stream
        has_qua = type(self).qua_stream is not SubSequence.qua_stream

        if has_fpga:
            self.fpga_stream()
        elif has_qua:
            self.qua_stream()
        else:
            self.fpga_stream()

    # ──────────────────────────────────────────────────────────────────────
    # Legacy QUA lifecycle hooks (backwards compatible)
    # ──────────────────────────────────────────────────────────────────────

    def qua_sequence(self):
        """QUA-specific sequence (legacy). Override for QuaBackend-only code.

        For new sequences, prefer overriding fpga_sequence() instead.
        """
        if self.check_step_requirements:
            self.measurement.qua_check_step_requirements(
                super().qua_sequence
            )
        else:
            super().qua_sequence()

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
