""" Module containing GettableParameter class """
import logging
import hashlib
import warnings
import numpy as np

from qm import qua

from qcodes.validators import Arrays
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
        read_sequence (ReadSequence): `ReadSequence` managing the sequence of
            QUA program
        qm_job (RunningQmJob): Running job on the opx to interact with
        buffer (obj): QM buffer to get results from
        buffer_val (array): flat numpy array containing results of opx fetch
        shape (tuple): Shape of the setpoints array
        batch_size (tuple): Shape of one OPX batch
        count (int): Amount of successful `get` executions
    """
    def __init__(
            self,
            name: str,
            read_sequence: 'ReadSequence',
            var_type: int | bool | qua.fixed,
            *args,
            **kwargs
            ) -> None:
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the GettableParameter
            readout (Readout): Readout class summarizing data streams and variables
        """
        super().__init__(name, *args, vals=Arrays(shape=(1,)), **kwargs)

        # self.unit = ""
        # self.label = ""

        self.var_type = var_type
        self.read_sequence = read_sequence
        self.read_sequence.add_gettable(self)
        self.measurement = read_sequence.measurement
        measurement_full_name = f"{self.measurement.driver.short_name}_" \
            f"{self.measurement.short_name}_"
        self._register_name = self.full_name.split(measurement_full_name)[-1]
        
        self.reset_measuerement_attributes()
        ### The following attributes hold the QUA variables and streams
        ### those can only be generated upon qua program compilation
        self.qua_var = None
        self.qua_buffer = None
        self.qua_stream = None

        self.buffer = None
        self.buffer_val = None
        self.sweep_dims = None
        self.snaked = None
        self.batch_size = 0
        self.result_nr = 0
        self.batch_counter = None
        self.nr_registered_results = 0
        self.is_mock = False

    def set_raw(self, *args, **kwargs) -> None:
        """Empty abstract `set_raw` method. Parameter not meant to be set"""
        raise NotImplementedError("GettableParameters are not meant to be set")

    def reset_measuerement_attributes(self):
        """Resets all job specific attributes"""
        self.buffer = None
        self.buffer_val = None
        self.sweep_dims = None
        self.batch_size = 0
        self.result_nr = 0
        self.batch_counter = None
        self.nr_registered_results = 0
        self.snaked = None

    def configure_from_measurement(self):
        """
        Configures the gettable parameter from the measurement object.
        This method sets the sweep dimensions, batch size, and snaked shape
        based on the sweeps defined in the measurement.
        """
        self.batch_size = self.measurement.sweep_size
        self.sweep_dims = self.measurement.sweep_dims
        self.vals = Arrays(
            shape = tuple(sweep.length for sweep in self.measurement.sweeps))
        self.is_mock = self.measurement.is_mock
        snaked_shape = tuple(s.snake_scan for s in self.measurement.sweeps)
        self.snaked = tuple(reversed(snaked_shape))

    def _is_dummy_mode(self) -> bool:
        """
        Check if we're running in dummy mode by examining the driver type
        Returns:
            bool: True if running with dummy driver, False otherwise
        """
        if self.measurement.driver.is_mock:
            return True
        return False
    
    def set_qm_buffer(self, qm_job: 'RunningQmJob') -> None:
        """
        Fetches the QM buffer result from the QM driver and assigns it to the
        `buffer` attribute.
        
        Args:
            qm_driver (RunningQmJob): The QM driver instance to fetch the buffer from.
        """
        buffer_name = f"{self.full_name}_buffer"
        if buffer_name not in qm_job.result_handles.keys():
            raise ValueError(
                f"Buffer {buffer_name} not found in QM job result handles. "
                f"Use one of the available ones:\n {qm_job.result_handles.keys()}"
            )
        self.buffer = getattr(qm_job.result_handles, buffer_name)

    def get_raw(self) -> np.ndarray:
        """ 
        Get method to retrieve a single batch of data from a running measurement
        On its first call, the gettables attributes get configured regarding
        the given measurement and the underlying hardware.
        """
        warnings.warn(
            "Directly calling get_raw on gettable (%s)"
            "Make sure the qua program has run and the buffer to fetch is full"
            )
        return self.fetch_results()

    def fetch_results(self) -> np.ndarray:
        """
        Get method to retrieve the results from the OPX buffer.

        Returns:
            np.ndarray: Reshaped data array from the OPX buffer.
        """
        if not self.is_mock:
            data = self._fetch_opx_buffer()
        else:
            logging.debug(
                "GettableParameter %s is in mock mode, returning random array",
                self.name
            )
            data = self._generate_synthetic_data()
        if data is None:
            raise RuntimeError(
                f"GettableParameter {self.name} has no data in the buffer. "
                "Make sure the QUA program has run and the buffer is full."
            )
        return self._reshape_data(data, self.sweep_dims, self.snaked)

    def _fetch_opx_buffer(self):
        """
        Fetches the OPX buffer into the `buffer_val` and increments the internal
        counter `count`
        """
        buffer_val = np.array(self.buffer.fetch_all(), dtype = float)
        return buffer_val

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

    def _generate_synthetic_data(self) -> np.ndarray:
        """
        Generate synthetic/dummy data for testing purposes
        
        Returns:
            np.ndarray: Synthetic data array with the expected shape
        """
        # Generate and return synthetic data
        # Use a seed based on the parameter name for repeatability
        seed = int(hashlib.md5(self.name.encode()).hexdigest(), 16) % (2**32)
        np.random.seed(seed)
        # Generate synthetic data based on the sweep size
        sweep_size = np.prod(self.sweep_dims)
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
            # Generic data: linear increasing values
            data = np.linspace(0, 1, sweep_size)
        data = np.array(data)
        logging.debug(
            "Generated synthetic data for %s: shape=%s, mean=%s",
            self.name, len(data), np.mean(data)
            )
        return data
