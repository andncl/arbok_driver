"""Module containing the ReadSequence class"""
import logging
from qcodes.validators import Arrays

from .sub_sequence import SubSequence
from .signal import Signal
from .gettable_parameter import GettableParameter

class ReadSequence(SubSequence):
    """ Baseclass for sequences containing readouts """
    def __init__(
        self,
        name,
        sample,
        seq_config,
        available_readout_types = None
        ):
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the ReadSequence
            smaple (Sample): sample for which sequence is configured
        """
        super().__init__(name, sample, seq_config)
        self.seq_config = seq_config
        self.readouts = []
        self._signals = {}
        self.readout_points = {}
        self.available_readout_types = available_readout_types
        self._abstract_readouts = {}
        self.readout_groups = {}
        if 'signals' in self.seq_config:
            logging.debug("Adding signals to ReadSequence: %s", self.name)
            self._add_signals_from_config(self.seq_config['signals'])
            self._add_gettables_from_signals()
        if "readout_groups" in self.seq_config:
            logging.debug(
                "Adding readout groups to ReadSequence: %s", self.name)
            self._add_readout_groups_from_config(
                self.seq_config["readout_groups"])
            self._add_gettables_from_readouts()

    @property
    def signals(self):
        """Signals registered in this sequence"""
        return self._signals

    @property
    def abstract_readouts(self):
        """All abstract readouts in this read-sequence"""
        return self._abstract_readouts

    def qua_declare(self):
        """QUA variable declaration for mixed down up initialization"""
        for point_name, readout_point in self.readout_points.items():
            logging.debug("Declaring qua vars for %s", point_name)
            readout_point.qua_declare_variables()
        for readout_name, abstract_readout in self._abstract_readouts.items():
            logging.debug("Declaring qua vars for %s", readout_name)
            abstract_readout.qua_declare_variables()

    def qua_stream(self):
        for _, signal in self.signals.items():
            signal.qua_save_streams()
            logging.debug("Saving streams of signal %s", signal.name)
        for readout_name, abstract_readout in self._abstract_readouts.items():
            logging.debug("Saving streams of abstract readout %s", readout_name)
            abstract_readout.qua_save_streams()
            continue

    def _add_signals_from_config(self, signal_config: dict):
        """Creates all signals and their readout points from config"""
        for name, config in signal_config.items():
            new_signal = Signal(name, self, config)
            setattr(self, name, new_signal)
            self._signals[new_signal.name] = new_signal

    def _add_gettables_from_signals(self):
        """Adds gettables from all given signals"""
        for _, signal in self.signals.items():
            for name, readout_point in signal.readout_points.items():
                for stream_name in readout_point.qua_buffer_names:
                    self._add_opx_gettable_parameter(name, stream_name)

    def _add_gettables_from_readouts(self):
        """Adds gettables from all abstract readouts e.g difference/threshold"""
        for _, readouts in self.readout_groups.items():
            for readout_name, readout in readouts.items():
                for stream_name in readout.qua_buffer_names:
                    self._add_opx_gettable_parameter(readout_name, stream_name)

    def _add_readout_groups_from_config(self, groups_config: dict):
        """Creates readout grops from config file"""
        for group_name, group_conf in groups_config.items():
            setattr(self, group_name, {})
            readout_group = getattr(self, group_name)
            logging.debug("Creating readout group %s", group_name)
            for readout_name, readout_conf in group_conf.items():
                match readout_conf["method"]:
                    case readout if readout in self.available_readout_types:
                        ReadoutClass = self.available_readout_types[readout]
                    case _:
                        raise ValueError(
                            f'{readout_conf["method"]} not available!',
                            'check your available_readout_types'
                        )
                logging.debug(
                    "Adding '%s' readout to signal '%s' with name '%s'",
                    readout_conf["method"],
                    readout_conf["signal"],
                    readout_conf["name"],
                    )
                full_name = f'{readout_conf["signal"]}__{readout_conf["name"]}'
                abstract_readout = ReadoutClass(
                    name = readout_name,
                    attr_name = readout_conf["name"],
                    sequence = self,
                    signal = readout_conf["signal"],
                    **readout_conf["args"],
                )
                readout_group[full_name] = abstract_readout
                self._abstract_readouts[readout_name] = abstract_readout
            self.readout_groups[group_name] = readout_group

    def _add_opx_gettable_parameter(
        self,
        readout_name: str,
        qua_variable_name: str
        ):
        """
        Creates GettableParameter in the ReadSequence that will be fetchable
        during a measurement. The name of the created parameter has to coincide
        with the name of the buffered stream (Refer to the generated qua script)
            
        Args:
            readout_name (str): Name of the abstract readout or readout point
            qua_variable_name (str): Name of the qua variable to be recorded
        """
        logging.debug(
            "Added stream %s from %s to %s",
            readout_name,
            qua_variable_name,
            self.name
        )
        gettable_name = f"{readout_name}__{qua_variable_name}"
        gettable_name = qua_variable_name
        self.add_parameter(
            parameter_class = GettableParameter,
            name = gettable_name,
            sequence = self,
            vals = Arrays(shape = (1,))
        )
        self._gettables.append(getattr(self, gettable_name))
