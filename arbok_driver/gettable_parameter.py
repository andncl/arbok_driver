""" Module containing GettableParameter class """

import time
import logging
import hashlib
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

        self.measurement = sequence.measurement
        self.reset_measuerement_attributes()

        self.qm_job = None
        self.buffer = None
        self.buffer_val = None
        self.shape = None
        self.snaked = None
        self.batch_size = 0
        self.result_nr = 0
        self.batch_counter = None
        self.nr_registered_results = 0

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

    def _is_dummy_mode(self) -> bool:
        """
        Check if we're running in dummy mode by examining the driver type
        
        Returns:
            bool: True if running with dummy driver, False otherwise
        """
        if self.measurement.driver.is_dummy:
            return True
        try:
            # Check if the driver is a DummyDriver
            driver_class_name = self.measurement.driver.__class__.__name__
            return driver_class_name == 'DummyDriver' or 'Dummy' in driver_class_name
        except AttributeError:
            return False

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
        # Check if we're in dummy mode
        if self._is_dummy_mode():
            logging.debug(
                "Running in dummy mode for %s,"
                "generating synthetic data", self.name
                )
            # Set up basic attributes for dummy mode
            synthetic_data = self._generate_synthetic_data(
                progress_bar= progress_bar)
            return self._reshape_data(synthetic_data, self.shape, self.snaked)
        
        # Original hardware mode code
        ### The progress is being tracked while waiting for the buffer to fill
        self._wait_until_buffer_full(progress_bar = progress_bar)
        self.buffer_val = self._fetch_opx_buffer()

        ### The QM can have a delay in populating the stream for big sweeps
        while not self.buffer_val.shape == (self.measurement.sweep_size,):
            time.sleep(0.1)
            self.buffer_val = self._fetch_opx_buffer()
        return self._reshape_data(self.buffer_val, self.shape, self.snaked)

    def _reshape_data(
            self,
            a_in: np.ndarray,
            sizes: tuple[int, ...],
            snaked: tuple[bool, ...]
            ) -> np.ndarray:
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
            raise ValueError(
                f"The cumulative product of sizes {np.prod(sizes)} must be"
                "equal to the total number of elements in the array: "
                f"{self.batch_size}."
                )
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
        hardware specific values if driver is not operated in dummy mode.
        """
        shape = tuple(sweep.length for sweep in self.measurement.sweeps)
        self.shape = tuple(reversed(shape))
        snaked_shape = tuple(sweep.snake_scan for sweep in self.measurement.sweeps)
        self.snaked = tuple(reversed(snaked_shape))
        self.batch_size = self.measurement.sweep_size
        if not self._is_dummy_mode():
            if not self.measurement.driver.opx:
                raise LookupError("Results cant be retreived without OPX connected")
            self.qm_job = self.measurement.driver.qm_job
            self.batch_counter = getattr(
                self.qm_job.result_handles,
                f"{self.measurement.name}_shots"
            )
            self.buffer = getattr(self.qm_job.result_handles, f"{self.name}_buffer")
            if self.buffer is None:
                raise LookupError(
                    f"Buffer {self.name}_buffer not found. Try one of:"
                    f"{self.qm_job.result_handles.keys()}")

    def _wait_until_buffer_full(self, progress_bar: tuple = None):
        """
        This function is running until a batch with self.batch_size is ready

        Args:
            progress_bar (tuple): Optional tuple containing progress bar
        """
        batch_count = 0
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

    def _generate_synthetic_data(self, progress_bar) -> np.ndarray:
        """
        Generate synthetic/dummy data for testing purposes
        
        Returns:
            np.ndarray: Synthetic data array with the expected shape
        """
        # Simulate progress bar updates if provided
        if progress_bar is not None:
            import time
            for i in range(10):  # Simulate 10 progress updates
                count = int((i + 1) * self.batch_size / 10)
                progress_bar[1].update(
                    progress_bar[0],
                    completed = int((i + 1) * self.batch_size / 10),
                    description = f"[cyan]Dummy batch progress {count}/{self.batch_size}"
                )
                progress_bar[1].refresh()
                time.sleep(0.01)  # Small delay to simulate real measurement time
        
        # Generate and return synthetic data
        # Use a seed based on the parameter name for repeatability
        seed = int(hashlib.md5(self.name.encode()).hexdigest(), 16) % (2**32)
        np.random.seed(seed)
        # Generate synthetic data based on the sweep size
        sweep_size = np.prod(self.shape)
        # Create different types of synthetic data based on parameter name
        if 'I' in self.name or 'current' in self.name.lower():
            # Current-like data: small values with some noise
            base_value = 1e-9  # 1 nA base current
            noise_level = 0.1 * base_value
            data = np.random.normal(base_value, noise_level, sweep_size)
        elif 'voltage' in self.name.lower() or 'V' in self.name:
            # Voltage-like data: larger values
            base_value = 0.5  # 0.5V base voltage
            noise_level = 0.05 * base_value
            data = np.random.normal(base_value, noise_level, sweep_size)
        elif 'frequency' in self.name.lower() or 'freq' in self.name.lower():
            # Frequency-like data
            base_value = 1e9  # 1 GHz base frequency
            noise_level = 1e6  # 1 MHz noise
            data = np.random.normal(base_value, noise_level, sweep_size)
        elif 'phase' in self.name.lower():
            # Phase data: between -pi and pi
            data = np.random.uniform(-np.pi, np.pi, sweep_size)
        elif 'count' in self.name.lower() or 'shot' in self.name.lower():
            # Count data: integers
            data = np.random.poisson(100, sweep_size).astype(float)
        else:
            # Generic data: normalized values around 0
            data = np.random.normal(0, 1, sweep_size)
        data = np.array(data)
        logging.debug(
            "Generated synthetic data for %s: shape=%s, mean=%s",
            self.name, len(data), np.mean(data)
            )
        time.sleep(0.5)
        return data
