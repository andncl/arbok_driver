""" Module containing GettableParameter class """

import warnings
import time
import logging as lg
import numpy as np
import matplotlib.pyplot as plt
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
        readout (Readout): `Readout` instance that created this parameter
        sequence (Sequence): `Sequence` managing the sequence of QUA program
        qm_job (RunningQmJob): Running job on the opx to interact with
        buffer (obj): QM buffer to get results from
        buffer_val (array): flat numpy array containing results of opx fetch
        shape (tuple): Shape of the setpoints array
        batch_size (tuple): Shape of one OPX batch
        count (int): Amount of successful `get` executions
    """
    def __init__(self, name, sequence, *args, **kwargs) -> None:
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the GettableParameter
            readout (Readout): Readout class summarizing data streams and variables
        """
        super().__init__(name, *args, **kwargs)
        self.unit = ""
        self.label = ""

        self.sequence = sequence
        self.qm_job = None
        self.buffer = None
        self.buffer_val = None
        self.shape = None
        self.batch_size = 0
        self.result_nr = 0
        self.batch_counter = None

    def set_raw(self, *args, **kwargs) -> None:
        """Empty abstract `set_raw` method. Parameter not meant to be set"""
        raise NotImplementedError("GettableParameters are not meant to be set")

    def get_raw(self, progress_bar = None) -> np.ndarray:
        """ 
        Get method to retrieve a single batch of data from a running measurement
        On its first call, the gettables attributes get configured regarding
        the given measurement and the underlying hardware.
        """
        if self.buffer is None:
            # Will be executed on the first call of get()
            self._set_up_gettable_from_program()
        self._fetch_from_opx(progress_bar = progress_bar)
        if self.buffer_val is None:
            warnings.warn("NO VALUE STREAMED!")
        return self.buffer_val.reshape(tuple((reversed(self.shape))))

    def _set_up_gettable_from_program(self):
        """
        Set up Gettable attributes from running OPX including measurement and 
        hardware specific values.
        """
        self.sequence = self.sequence.parent_sequence
        if not self.sequence.parent_sequence.driver.opx:
            raise LookupError("Results cant be retreived without OPX connected")
        self.qm_job = self.sequence.driver.qm_job
        self.batch_counter = getattr(
            self.qm_job.result_handles,
            f"{self.sequence.name}_shots"
        )
        self.buffer = getattr(self.qm_job.result_handles, f"{self.name}_buffer")
        self.shape = tuple(sweep.length for sweep in self.sequence.sweeps)
        self.batch_size = self.sequence.sweep_size

    def _fetch_from_opx(self, progress_bar: tuple = None):
        """
        Fetches and returns data from OPX after results came in.
        This method pauses as long as the required amount of results is not in.
        Raises a warning if the data generation on the OPX is faster than the
        data streaming back to the PC.
        """
        self._wait_until_buffer_full(progress_bar = progress_bar)
        self._fetch_opx_buffer()

    def _wait_until_buffer_full(self, progress_bar = None):
        """
        This function is running until a batch with self.batch_size is ready
        """
        batch_count, old_count = 0, 0
        last_result_nr = self.result_nr
        shot_timing = "Calculating shot timing..."
        total_results = "Total results: ..."
        t0 = time.time()
        try:
            while last_result_nr == self.result_nr:
                lg.info(
                    "Waiting: %s/%s results are in",
                    batch_count, self.batch_size
                )
                shot_count_result = self.batch_counter.fetch_all()
                if shot_count_result is not None:
                    self.result_nr, batch_count = divmod(
                        shot_count_result[0], self.batch_size)
                    total_results = f"Total results: {shot_count_result[0]}"
                if progress_bar is not None:
                    bar_title = "[cyan]Batch progress "
                    bar_title += f"{batch_count}/{self.batch_size}\n"
                    if batch_count > old_count:
                        time_per_shot = 1e3*(time.time()-t0)/(batch_count-old_count)
                        shot_timing = f"{time_per_shot:.1f} ms per shot\n"
                        
                    t0 = time.time()
                    progress_bar[1].update(
                        progress_bar[0],
                        completed = batch_count,
                        description = bar_title + shot_timing + total_results
                    )
                    progress_bar[1].refresh()
                    old_count = batch_count
        except KeyboardInterrupt as exc:
            raise KeyboardInterrupt('Measurement interrupted by user') from exc
        if progress_bar is not None:
            progress_bar[1].update(progress_bar[0], completed = batch_count)

    def _fetch_opx_buffer(self):
        """
        Fetches the OPX buffer into the `buffer_val` and increments the internal
        counter `count`
        """
        self.buffer_val = np.array(self.buffer.fetch_all(), dtype = float)
        if self.buffer_val is None:
            raise ValueError("NO VALUE STREAMED")

    def get_all(self):
        """Fetches ALL (not buffered) data"""
        if self.result is None:
            self._set_up_gettable_from_program()
        if self.result:
            return self.result.fetch_all()
        else:
            raise LookupError("Results cant be retreived without OPX")

    def reset(self):
        """Resets all job specific attributes"""
        self.qm_job = None
        self.buffer = None
        self.buffer_val = None
        self.shape = None
        self.batch_size = 0

    def plot_set_current_histogram(self, *args, **kwargs) -> tuple:
        """
        Plots a histrogram of all the measured data so far
        
        Args:
            *args: Arguments for plt.hist
            **kwargs: Keyword arguments for plt.hist
        """
        set_current = np.array(self.get_all(), dtype = float)
        return plt.hist(set_current, args, kwargs)
