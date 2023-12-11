import logging
from qcodes.validators import Arrays

from .sub_sequence import SubSequence
from .signal import Signal
from .gettable_parameter import GettableParameter

class ReadSequence(SubSequence):
    """ Baseclass for sequences containing readouts """
    def __init__(self, name, sample, seq_config):
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
        
        if 'signals' in self.seq_config:
            logging.debug("Adding signals to ReadSequence: %s", self.name)
            self.add_signals_from_config(self.seq_config['signals'])

    @property
    def signals(self):
        """Signals registered in this sequence"""
        return self._signals

    def add_gettables_from_readouts(self):
        """Creates gettables from readouts list"""
        self._gettables = []
        for readout in self.readouts:
            for stream_name in readout.stream_list:
                gettable_name = readout.name + '_' + stream_name
                self.add_parameter(
                    parameter_class = GettableParameter,
                    name = gettable_name,
                    readout = readout,
                    vals = Arrays(shape = (1,))
                )
                self._gettables.append(getattr(self, gettable_name))
                #setattr(self, gettable_name, gettable)

    def add_signals_from_config(self, signal_config: dict):
        """Creates all signals and their readout points from config"""
        for name, config in signal_config.items():
            new_signal = Signal(name, self, config)
            setattr(self, name, new_signal)
            self._signals[new_signal.name] = new_signal
    
    def add_readout_groups_from_config(self, groups_config: dict):
        """Creates readout grops from config file"""
        for group_name, group_conf in groups_config.items():
            for readout_name, readout_conf in group_conf.items():
                match readout_conf["method"]:
                    case 'difference':
                        ReadoutClass = Difference
                    case 'threshold':
                        ReadoutClass = Threshold

    def qua_stream(self):
        for readout in self.readouts:
            readout.save_streams()
            continue
        for signal_name, signal in self.signals.items():
            signal.save_streams()
            logging.debug("Saving streams of signal %s", signal.name)
