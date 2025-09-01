"""Module containing the ReadSequence class"""
from __future__ import annotations
from typing import TYPE_CHECKING
import logging
from qcodes.validators import Arrays

from .abstract_readout import AbstractReadout
from .gettable_parameter import GettableParameter
from .signal import Signal
from .sub_sequence import SubSequence

if TYPE_CHECKING:
    from .device import Device

class ReadSequence(SubSequence):
    """ Baseclass for sequences containing readouts """
    def __init__(
        self,
        parent: SubSequence,
        name: str,
        device: Device,
        sequence_config: dict,
        ):
        """
        Constructor class for ReadSequence class
        Args:
            parent (SubSequence): Parent instrument module
            name (dict): name of the ReadSequence
            device (Device): device for which sequence is configured
            sequence_config (dict): Dict configuring all parameters for the given
                read-sequence and its read-points and abstract-readouts
        """
        super().__init__(
            parent=parent,
            name=name,
            device=device,
            sequence_config=sequence_config
            )

        self._check_read_sequence_config(sequence_config)
        self.sequence_config = sequence_config
        self._signals = {}
        self._readout_groups = {}
        self._abstract_readouts = {}

        logging.debug("Adding signals to ReadSequence: %s", self.name)
        self._add_signals_from_config(self.sequence_config['signals'])
        logging.debug("Adding readout groups to ReadSequence: %s", self.name)
        self._add_readout_groups_from_config(self.sequence_config["readout_groups"])
        self.measurement.add_available_gettables(self._gettables)

    @property
    def signals(self):
        """Signals registered in this sequence"""
        return self._signals

    @property
    def readout_groups(self):
        """All configured readout groups"""
        return self._readout_groups

    @property
    def abstract_readouts(self):
        """All abstract readouts in this read-sequence"""
        return self._abstract_readouts

    def qua_declare(self):
        """
        QUA variable and stream declaration based on the given sequence
        configuration. Only to be called within qua.program() context manager!
        """
        for readout_name, abstract_readout in self._abstract_readouts.items():
            logging.debug("Declaring qua vars for %s", readout_name)
            abstract_readout.qua_declare_variables()

    def qua_stream(self):
        """
        Saves acquired results to qua stream
        Only to be called within qua.program() context manager!
        """
        for readout_name, abstract_readout in self._abstract_readouts.items():
            logging.debug("Saving streams of abstract readout %s", readout_name)
            abstract_readout.qua_save_streams()
            continue

    def _add_signals_from_config(self, signal_name_list: list):
        """
        Creates all signals on the ReadSequence from the given config.
        Checks validity of signal names and adds them to the sequence.
        Signals are added as attributes to the sequence with the same name.
        Signals are also added to the signals property of the sequence.

        Args:
            signal_name_list (list): List of signal names to be added to the

        Raises:
            TypeError: If signal name is not a list
            ValueError: If signal name is not a string or already exists
            AttributeError: If signal name is already an attribute of the sequence
        """
        if not isinstance(signal_name_list, list):
            raise ValueError(
                f"Signals in sequence config of {self.full_name} must be a list!"
            )
        for signal_name in signal_name_list:
            logging.debug("Adding signal %s to %s", signal_name, self.full_name)
            if not isinstance(signal_name, str):
                raise ValueError(
                    f"Signal name {signal_name} in sequence config of"
                    f" {self.full_name} must be a string!"
                )
            if hasattr(self, signal_name):
                raise AttributeError(
                    f"Attribute '{signal_name}' already exists on {self.full_name}!"
                    " Cant add signal with the same name."
                )
            new_signal = Signal(name=signal_name, read_sequence = self)
            self._signals[new_signal.name] = new_signal
            setattr(self, signal_name, new_signal)

    def _check_read_sequence_config(self, sequence_config: dict):
        """
        Checks the given sequence config for validity
        Args:
            sequence_config (dict): Dict configuring all parameters for the given
                read-sequence and its read-points and abstract-readouts
        """
        if 'signals' not in sequence_config:
            raise ValueError(
                f"No signals configured in sequence config for {self.full_name}!"
                )
        if 'readout_groups' not in sequence_config:
            raise ValueError(
                "No readout groups configured in sequence config for"
                f"{self.full_name}!"
            )
        group_configs = sequence_config['readout_groups'].values()
        if not all([isinstance(conf, dict) for conf in group_configs]):
            raise TypeError(
                f"Readout groups configs in sequence config of {self.full_name}"
                " must be dicts!"
            )

    def _add_readout_groups_from_config(self, groups_config: dict) -> None:
        """
        Creates readout groups from config file

        Args:
            groups_config (dict): Dict containing readout groups and their
                readouts. The keys are the group names and the values are dicts
                containing readout names and their configurations.
        Raises:
            TypeError: If readout config is not a dict
        """
        for group_name, group_conf in groups_config.items():
            logging.debug("Creating readout group %s", group_name)
            self._readout_groups[group_name] = {}
            for readout_name, readout_conf in group_conf.items():
                if not isinstance(readout_conf, dict):
                    raise TypeError(
                        f"Readout config of {readout_name} in group {group_name}"
                        f" of {self.full_name} must be a dict!"
                    )
                abstract_readout = self._add_abstract_readout(
                    readout_conf, readout_name, group_name
                )
                self._readout_groups[group_name][readout_name] = abstract_readout

    def _add_abstract_readout(
        self,
        readout_conf: dict,
        readout_name: str,
        group_name: str
    ) -> AbstractReadout:
        """
        Adds an abstract readout to the sequence from the given configuration.
        
        Args:
            readout_conf (dict): Configuration dict of the readout
            readout_name (str): Name of the readout
            group_name (str): Name of the readout group
        Raises:
            ValueError: If signal is not found in the sequence signals
        Returns:
            AbstractReadout: The created abstract readout object
        """
        full_readout_name = f"{group_name}__{readout_name}"
        self._check_readout_config(readout_conf, full_readout_name, group_name)
        logging.debug(
            "Adding '%s' readout to sequence '%s' with name '%s'",
            readout_conf['readout_class'].__name__,
            self.full_name,
            full_readout_name,
        )
        if "save_results" in readout_conf:
            save_results = readout_conf["save_results"]
        else:
            save_results = True
        kwargs = readout_conf['kwargs'] if 'kwargs' in readout_conf else {}
        params = readout_conf["parameters"] if "parameters" in readout_conf else None
        if readout_conf['signal'] not in self.signals:
            raise ValueError(
                f"Signal {readout_conf['signal']} not found in read sequence"
                f"{self.full_name}. Available signals: {list(self.signals.keys())}"
            )
        abstract_readout = readout_conf['readout_class'](
            name = full_readout_name,
            read_sequence = self,
            signal = self.signals[readout_conf['signal']],
            save_results = save_results,
            parameters = params,
            **kwargs
        )
        self._abstract_readouts[full_readout_name] = abstract_readout
        return abstract_readout

    def _check_readout_config(
            self, readout_conf: dict, readout_name: str, group_name: str) -> None:
        """
        Checks the given readout configuration for validity.
        
        Args:
            readout_conf (dict): Configuration dict of the readout
            readout_name (str): Name of the readout
            group_name (str): Name of the readout group
        Raises:
            KeyError: If 'readout_class' or 'signal' is not in the config
            TypeError: If 'readout_class' is not a subclass of AbstractReadout
        """
        if 'readout_class' not in readout_conf:
            raise KeyError(
                f"'readout_class' not found in readout config for {readout_name}"
                f" in group {group_name} on {self.full_name}!."
                f" Config is: {readout_conf}"
            )
        if 'signal' not in readout_conf:
            raise KeyError(
                f"'signal' not found in readout config for {readout_name}"
                f" in group {group_name} on {self.full_name}!"
                )
        if not issubclass(readout_conf['readout_class'], AbstractReadout):
            raise TypeError(
                f"Readout class {readout_conf['readout_class'].__name__} is not"
                f" a subclass of AbstractReadout ({self.full_name},"
                f" {group_name}__{readout_name})!"
            )

    def add_gettable(self, gettable: GettableParameter) -> None:
        """
        Adds a gettable parameter to the read sequence. This is used to make
        the gettable fetchable during a measurement.

        Args:
            gettable (GettableParameter): Gettable parameter to be added
        """
        if not isinstance(gettable, GettableParameter):
            raise TypeError(
                f"Expected GettableParameter, got {type(gettable)}"
            )
        self._gettables.append(gettable)

    def get_qm_elements_from_signals(self):
        """
        Gets all qm elements from the configured signals in this read sequence
        """
        qm_elements = []
        for _, signal in self.signals.items():
            qm_elements += signal.readout_elements.values()
        # this is meant to be deterministic with non duplicates in the list.
        return list(dict.fromkeys(qm_elements))
