""" Module containing GettableParameter class """

import warnings
import logging as lg
import numpy as np
from qcodes.parameters import ParameterWithSetpoints

class GettableParameter(ParameterWithSetpoints):
    """
    This is a valid Gettable not because of inheritance, but because it has the
    expected attributes and methods.
    TODO: zip all streams together, stream at once and unpack while opx resume
    TODO: interleaved measurements

    Attributes:
        unit (str): Unit of the parameter
        label (label): Label for parameter (printed on axis)
        can_resume (bool): Whether the instance resumes the program after read
        readout (Readout): `Readout` instance that created this parameter
        sequence (Sequence): `Sequence` managing the sequence of QUA program
        qm_job (RunningQmJob): Running job on the opx to interact with
        result (obj): QM object managing OPX streams 
        buffer (obj): QM buffer to get results from
        buffer_val (array): flat numpy array containing results of opx fetch
        shape (tuple): Shape of the setpoints array
        count_so_far (int): Total single measurements of OPX
        batch_size (tuple): Shape of one OPX batch
        count (int): Amount of successful `get` executions
    """
    def __init__(self, name, readout, *args, **kwargs) -> None:
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the GettableParameter
            readout (Readout): Readout class summarizing data streams and variables
        """
        super().__init__(name, *args, **kwargs)
        self.unit = ""
        self.label = ""
        self.can_resume = False

        self.readout = readout
        self.sequence = None
        self.qm_job = None
        self.result = None
        self.buffer = None
        self.buffer_val = None
        self.shape = None
        self.count_so_far = 0
        self.batch_size = 0
        self.batch_count = 0

    def set_raw(self, *args, **kwargs):
        """ Empty abstract `set_raw` method. Parameter not meant to be set """

    def get_raw(self) -> np.ndarray:
        """ 
        Get method to retrieve a single batch of data from a running measurement
        """
        if self.result is None:
            # Will be executed on the first call of get()
            self._set_up_gettable_from_program()
        self._fetch_from_opx()
        if self.buffer_val is None:
            warnings.warn("NO VALUE STREAMED!")
        if self.sequence.stream_mode == "pause_each" and self.can_resume:
            self.qm_job.resume()
        return self.buffer_val.reshape(tuple((reversed(self.shape))))

    def _set_up_gettable_from_program(self):
        """ Set up Gettable attributes from running OPX """
        self.sequence = self.readout.sequence.parent_sequence
        if not self.readout.sequence.parent_sequence.program.opx:
            raise LookupError("Results cant be retreived without OPX connected")
        self.qm_job = self.sequence.program.qm_job
        self.result = getattr(self.qm_job.result_handles, self.name)
        self.buffer = getattr(self.qm_job.result_handles, f"{self.name}_buffer")
        self.shape = tuple(sweep.length for sweep in self.sequence.sweeps)
        self.batch_size = self.sequence.sweep_size

    def _fetch_from_opx(self):
        """ Fetches and returns data from OPX after results came in """
        self.count_so_far = self.result.count_so_far()
        if self.count_so_far > (self.batch_count + 2)*self.batch_size:
            warnings.warn("OVERHEAD of data on OPX! Try larger batches or other sweep type!")

        self._wait_until_buffer_full()
        self._fetch_opx_buffer()

    def _wait_until_buffer_full(self):
        """ This function is running until a batch with self.batch_size is ready """
        while self.count_so_far < (self.batch_count + 1)*self.batch_size:
            lg.info("Waiting: %s/%s results are in", 
                self.count_so_far, (self.batch_count + 1)*self.batch_size)
            self.count_so_far = self.result.count_so_far()

    def _fetch_opx_buffer(self):
        """
        Fetches the OPX buffer into the `buffer_val` and increments the internal
        counter `count`
        """
        self.buffer_val = np.array(self.buffer.fetch(-1), dtype = float)
        if self.buffer_val is None:
            raise ValueError("NO VALUE STREAMED")
        self.batch_count += 1

    def get_all(self):
        """ Fetches ALL (not buffered) data """
        if self.result:
            return self.result.fetch_all()
        else:
            raise LookupError("Results cant be retreived without OPX")
