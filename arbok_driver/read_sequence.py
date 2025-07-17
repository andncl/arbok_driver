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
        parent,
        name,
        device,
        sequence_config,
        available_abstract_readouts = {},
        available_readout_points = {}
        ):
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the ReadSequence
            device (Device): device for which sequence is configured
            seq_config (dict): Dict configuring all parameters for the given
                read-sequence and its read-points and abstract-readouts
            available_abstract_readouts (None | dict): Optional, dictionairy with
                available abstract readouts with method name as key and abstract
                readout class as value
        """
        super().__init__(parent, name, device, sequence_config)
        self.seq_config = sequence_config
        self.available_abstract_readouts = available_abstract_readouts
        self.available_readout_points = available_readout_points

        self._signals = {}
        self._readout_points = {}
        self._readout_groups = {}
        self._abstract_readouts = {}
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
        self.measurement.add_available_gettables(self._gettables)

    @property
    def abstract_readouts(self):
        """All abstract readouts in this read-sequence"""
        return self._abstract_readouts

    @property
    def signals(self):
        """Signals registered in this sequence"""
        return self._signals

    @property
    def readout_groups(self):
        """All configured readout groups"""
        return self._readout_groups

    @property
    def readout_points(self):
        """All configured readout points"""
        return self._readout_points

    def qua_declare(self):
        """
        QUA variable and stream declaration based on the given sequence
        configuration. Only to be called within qua.program() context manager!
        """
        for point_name, readout_point in self.readout_points.items():
            logging.debug("Declaring qua vars for %s", point_name)
            readout_point.qua_declare_variables()
        for readout_name, abstract_readout in self._abstract_readouts.items():
            logging.debug("Declaring qua vars for %s", readout_name)
            abstract_readout.qua_declare_variables()

    def qua_stream(self):
        """
        Saves acquired results to qua stream
        Only to be called within qua.program() context manager!
        """
        for _, signal in self.signals.items():
            signal.qua_save_streams()
            logging.debug("Saving streams of signal %s", signal.name)
        for readout_name, abstract_readout in self._abstract_readouts.items():
            logging.debug("Saving streams of abstract readout %s", readout_name)
            abstract_readout.qua_save_streams()
            continue

    def _add_signals_from_config(self, signal_config: dict):
        """
        Creates all signals and their readout points from config
        """
        for name, config in signal_config.items():
            logging.debug("Adding signal %s to %s", name, self.name)
            new_signal = Signal(name, self, config,
                self.available_readout_points)
            setattr(self, name, new_signal)
            self._signals[new_signal.name] = new_signal

    def _add_gettables_from_signals(self):
        """Adds gettables from all given signals"""
        for _, signal in self.signals.items():
            for _, readout_point in signal.readout_points.items():
                for obs_name, observable in readout_point.observables.items():
                    logging.debug("Adding gettable from observable %s to %s",
                        obs_name, self.name)
                    self._add_gettable_from_observable(observable)

    def _add_gettables_from_readouts(self):
        """Adds gettables from all abstract readouts e.g difference/threshold"""
        for _, readouts in self.readout_groups.items():
            for _, readout in readouts.items():
                for _, observable in readout.observables.items():
                    self._add_gettable_from_observable(observable)

    def _add_readout_groups_from_config(self, groups_config: dict):
        """Creates readout grops from config file"""
        for group_name, group_conf in groups_config.items():
            setattr(self, group_name, {})
            readout_group = getattr(self, group_name)
            logging.debug("Creating readout group %s", group_name)
            for readout_name, readout_conf in group_conf.items():
                method = readout_conf["method"]
                if method in self.available_abstract_readouts:
                    ReadoutClass = self.available_abstract_readouts[method]
                else:
                    raise ValueError(
                        f"{method} not available!",
                        "check your available_abstract_readouts"
                    )
                logging.debug(
                    "Adding '%s' readout to sequence '%s' with name '%s'",
                    method,
                    self,
                    readout_name,
                    )
                if "save_results" in readout_conf:
                    save_results = readout_conf["save_results"]
                else:
                    save_results = True
                if "params" in readout_conf:
                    params = readout_conf["params"]
                else:
                    params = {}

                abstract_readout = ReadoutClass(
                    name = readout_name,
                    attr_name = readout_conf["name"],
                    sequence = self,
                    save_results = save_results,
                    params = params,
                )
                readout_group[readout_name] = abstract_readout
                self._abstract_readouts[readout_name] = abstract_readout
            self._readout_groups[group_name] = readout_group

    def _add_gettable_from_observable(self, observable):
        """Adds a gettable to the given readout sequence from an observable"""
        logging.debug(
            "Adding gettable %s from readout %s to signal %s",
            observable.full_name,
            observable.readout.name,
            observable.signal.name
        )
        self.add_parameter(
            parameter_class = GettableParameter,
            name = observable.full_name,
            register_name = observable.full_name,
            sequence = self,
            vals = Arrays(shape = (1,))
        )
        new_gettable = getattr(self, observable.full_name)
        observable.gettable = new_gettable
        self._gettables.append(new_gettable)

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

    def get_qm_elements_from_signals(self):
        """
        Gets all qm elements from the configured signals in this read sequence
        """
        qm_elements = []
        for _, signal in self.signals.items():
            qm_elements += signal.readout_elements.values()
        # this is meant to be deterministic with non duplicates in the list.
        return list(dict.fromkeys(qm_elements))
