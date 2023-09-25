from arbok_driver.sequence import Sequence
from arbok_driver.gettable_parameter import GettableParameter

from qcodes.validators import Arrays

class ReadSequence(Sequence):
    """ Baseclass for sequences containing readouts """
    def __init__(self, name, sample, seq_config):
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the ReadSequence
            smaple (Sample): sample for which sequence is configured
        """
        super().__init__(name, sample, seq_config)
        self.readouts = []
        self.gettables = {}

    def add_gettables_from_readouts(self):
        """Creates gettables from readouts list"""
        for readout in self.readouts:
            for stream_name in readout.stream_list:
                gettable_name = readout.name + '_' + stream_name
                gettable = GettableParameter(
                    name = gettable_name,
                    readout = readout,
                    vals = Arrays(shape = (1,))
                )
                self.gettables[gettable_name] = gettable
                setattr(self, gettable_name, gettable)

    def qua_stream(self):
        for readout in self.readouts:
            readout.save_streams()
            continue