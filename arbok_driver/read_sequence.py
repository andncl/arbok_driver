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
        self.abstract_readouts = {}
        if 'signals' in self.seq_config:
            logging.debug("Adding signals to ReadSequence: %s", self.name)
            self.add_signals_from_config(self.seq_config['signals'])
            self.add_gettables_from_signals()
        self.readout_groups = {}
        if "readout_groups" in self.seq_config:
            self.add_readout_groups_from_config(
                self.seq_config["readout_groups"])

    @property
    def signals(self):
        """Signals registered in this sequence"""
        return self._signals

    def add_signals_from_config(self, signal_config: dict):
        """Creates all signals and their readout points from config"""
        for name, config in signal_config.items():
            new_signal = Signal(name, self, config)
            setattr(self, name, new_signal)
            self._signals[new_signal.name] = new_signal

    def add_readout_groups_from_config(self, groups_config: dict):
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
                readout_group[full_name] = ReadoutClass(
                    name = readout_name,
                    attr_name = readout_conf["name"],
                    sequence = self,
                    signal = readout_conf["signal"],
                    **readout_conf["args"],
                )

    def add_gettables_from_signals(self):
        """Adds gettables from all given signals"""
        for _, signal in self.signals.items():
            for name, readout_point in signal.readout_points.items():
                for stream_name in readout_point.qua_variable_names:
                    logging.debug(
                        "Added stream %s from point %s to %s",
                        stream_name,
                        name,
                        self.name
                    )
                    gettable_name = f"{readout_point.name}__{stream_name}"
                    self.add_parameter(
                        parameter_class = GettableParameter,
                        name = gettable_name,
                        sequence = self,
                        vals = Arrays(shape = (1,))
                    )
                    self._gettables.append(getattr(self, gettable_name))

    def add_gettables_from_readouts(self):
        """Adds gettables from all abstract readouts e.g difference/threshold"""
        pass



    def qua_stream(self):
        for readout in self.readouts:
            readout.save_streams()
            continue
        for signal_name, signal in self.signals.items():
            signal.save_streams()
            logging.debug("Saving streams of signal %s", signal.name)
