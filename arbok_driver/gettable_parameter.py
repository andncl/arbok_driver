""" Module containing GettableParameter class """

import time
import logging
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
        self.reset_measuerement_attributes()

    def set_raw(self, *args, **kwargs) -> None:
        """Empty abstract `set_raw` method. Parameter not meant to be set"""
        raise NotImplementedError("GettableParameters are not meant to be set")

    def reset_measuerement_attributes(self):
        """Resets all job specific attributes"""
        self.qm_job = None
        self.buffer = None
        self.buffer_val = None
        self.shape = None
        self.batch_size = 0
        self.result_nr = 0
        self.batch_counter = None
        self.nr_registered_results = 0

    def get_raw(self, progress_bar = None) -> np.ndarray:
        """ 
        Get method to retrieve a single batch of data from a running measurement
        On its first call, the gettables attributes get configured regarding
        the given measurement and the underlying hardware.
        """
        logging.debug("GettableParameter %s get_raw called", self.name)
        ### Setup is called on first get
        if self.buffer is None:
            self._set_up_gettable_from_program()

        ### The progress is being tracked while waiting for the buffer to fill
        self._wait_until_buffer_full(progress_bar = progress_bar)
        self.buffer_val = self._fetch_opx_buffer()

        ### The QM can have a delay in populating the stream for big sweeps
        while not self.buffer_val.shape == (self.sequence.sweep_size,):
            time.sleep(0.1)
            self.buffer_val = self._fetch_opx_buffer()
        return self._reshape_data(self.buffer_val, self.shape, self.snaked)

    def _reshape_data(self, a_in: np.ndarray, sizes: tuple[int, ...], snaked: tuple[bool, ...]) -> np.ndarray:
        """
        Reshape the inherited array to be len(sizes). Iterate through each of the sizes gradually
        reshaping the inherited array one dimensions at a time. If for dimension n, snaked[n] is true,
        then reverse every second row of that dimension, then iterate to the next dimension.

        Args:
            a_in (np.ndarray): The input array to be reshaped.
            sizes (Tuple[int, ...]): The target shape dimensions.
            snaked (Tuple[bool, ...]): A tuple indicating which dimensions should have every second row reversed.

        Returns:
            np.ndarray: The reshaped array with specified dimensions and reversed rows as needed
        """

        # First check that the cumulative product of sizes is the same as self.size
        if np.prod(sizes) != a_in.size:
            raise ValueError(f"""The cumulative product of sizes {np.prod(sizes)} must be equal to the 
                             total number of elements in the array {self.size}.""")

        # Duplicate the ndarray
        a = a_in

        # Now iterate through each of the sizes
        for i, (sz, sn) in enumerate(zip(sizes[:-1], snaked[1:])):
            # Reshape a to have an extra dimension of size sz
            if i < len(sizes)-1:
                new_shape = a.shape[:-1] + (sz, -1)
                a = a.reshape(new_shape)

                # If sn is true, then reverse every second innermost row
                if sn:
                    if i == 0: # For the first dimension, reverse elements of even rows
                        a[1::2] = np.flip(a[1::2], axis=-1)
                    else:      # For subsequent dimensions, reverse every second innermost row (like before)
                        a[:, 1::2] = np.flip(a[:, 1::2], axis=-1)
        return a

    def _set_up_gettable_from_program(self):
        """
        Set up Gettable attributes from running OPX including measurement and 
        hardware specific values.
        """
        self.sequence = self.sequence.measurement
        if not self.sequence.measurement.driver.opx:
            raise LookupError("Results cant be retreived without OPX connected")
        self.qm_job = self.sequence.driver.qm_job
        self.batch_counter = getattr(
            self.qm_job.result_handles,
            f"{self.sequence.name}_shots"
        )
        self.buffer = getattr(self.qm_job.result_handles, f"{self.name}_buffer")
        if self.buffer is None:
            raise LookupError(
                f"Buffer {self.name}_buffer not found. Try one of:"
                f"{self.qm_job.result_handles.keys()}")
        self.shape = tuple(reversed(tuple(sweep.length for sweep in self.sequence.sweeps)))
        self.snaked = tuple(reversed(tuple(sweep.snake_scan for sweep in self.sequence.sweeps)))
        self.batch_size = self.sequence.sweep_size

    def _wait_until_buffer_full(self, progress_bar = None):
        """
        This function is running until a batch with self.batch_size is ready
        """
        batch_count, old_count = 0, 0
        last_result_nr = self.result_nr
        time_per_shot = 0
        shot_timing = "Calculate timing...\n"
        total_results = "Total results: ..."
        t0 = time.time()
        try:
            # self.qm_job.resume()
            while batch_count < self.batch_size or not self.qm_job.is_paused():
                logging.debug(
                    "Waiting for buffer to fill (%s/%s), %s",
                    batch_count, self.batch_size, self.qm_job.is_paused()
                    )
                shot_count_result = self.batch_counter.fetch_all()
                if shot_count_result is not None:
                    batch_count = shot_count_result[0]
                    total_nr_results = batch_count + self.nr_registered_results
                    total_results = f"Total results: {total_nr_results}"
                if progress_bar is not None:
                    bar_title = "[cyan]Batch progress "
                    bar_title += f"{batch_count}/{self.batch_size}\n"
                    if batch_count > 0:
                        time_per_shot = 1e3*(time.time()-t0)/(batch_count)
                    shot_timing = f"{time_per_shot:.1f} ms per shot\n"
                    progress_bar[1].update(
                        progress_bar[0],
                        completed = batch_count,
                        description = bar_title + shot_timing + total_results
                    )
                    progress_bar[1].refresh()
        except KeyboardInterrupt as exc:
            raise KeyboardInterrupt('Measurement interrupted by user') from exc
        if progress_bar is not None:
            progress_bar[1].update(progress_bar[0], completed = batch_count)
        self.nr_registered_results += self.batch_size

    def _fetch_opx_buffer(self):
        """
        Fetches the OPX buffer into the `buffer_val` and increments the internal
        counter `count`
        """
        buffer_val = np.array(self.buffer.fetch_all(), dtype = float)
        return buffer_val

    def reset(self):
        """Resets all job specific attributes"""
        self.qm_job = None
        self.buffer = None
        self.buffer_val = None
        self.shape = None
        self.batch_size = 0
        self.result_nr = 0

    def plot_set_current_histogram(self, *args, **kwargs) -> tuple:
        """
        Plots a histrogram of all the measured data so far
        
        Args:
            *args: Arguments for plt.hist
            **kwargs: Keyword arguments for plt.hist
        """
        set_current = np.array(self.get_all(), dtype = float)
        return plt.hist(set_current, args, kwargs)
