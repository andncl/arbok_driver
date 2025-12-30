"""Module containing GettableParameterBase class"""
from __future__ import annotations

from abc import abstractmethod
import copy
from typing import TYPE_CHECKING
import logging
import numpy as np
import warnings

from qcodes.validators import Arrays
from qcodes.parameters import ParameterWithSetpoints
from qm import qua

if TYPE_CHECKING:
    from arbok_driver.measurement import Measurement
    from arbok_driver.read_sequence import ReadSequence
    from numpy import ndarray
    from qm.qua._dsl.stream_processing.stream_processing import ResultStreamSource
    from qcodes.dataset.data_set_protocol import ValuesType
    from qcodes.parameters.parameter_base import ParameterBase

class GettableParameterBase(ParameterWithSetpoints):
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

    """
    def __init__(
            self,
            name: str,
            read_sequence: ReadSequence,
            var_type: int | bool | qua.fixed,
            **kwargs
            ) -> None:
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the GettableParameter
            readout (Readout): Readout class summarizing data streams and variables
        """
        super().__init__(name, vals=Arrays(shape=(1,)), **kwargs)
        self.vals: Arrays
        self.var_type: int | bool | qua.fixed = var_type
        self.read_sequence: ReadSequence = read_sequence
        self.read_sequence.add_gettable(self)
        self.measurement: Measurement = read_sequence.measurement
        measurement_full_name = f"{self.measurement.driver.short_name}_" \
            f"{self.measurement.short_name}_"
        self._register_name = self.full_name.split(measurement_full_name)[-1]
        
        self.reset_measuerement_attributes()
        self.qua_stream: None | ResultStreamSource = None
        self.buffer: None = None
        self.is_mock: bool = self.measurement.is_mock

    @abstractmethod
    def qua_declare_variables(self) -> None:
        """Declares the qua variables and streams for this gettable"""
        pass

    @abstractmethod
    def qua_save_variables(self) -> None:
        """Saves acquired results to qua stream"""
        pass

    def qua_save_streams(self) -> None:
        """Saves acquired results to qua stream"""
        buffer = self.qua_stream.buffer(*self.vals.shape)
        buffer.save(self.full_name)

    def set_raw(self, *args, **kwargs) -> None:
        """Empty abstract `set_raw` method. Parameter not meant to be set"""
        raise NotImplementedError("GettableParameters are not meant to be set")

    def reset_measuerement_attributes(self):
        """Resets all job specific attributes"""
        self.buffer = None
        self.qua_stream = None

    def configure_from_measurement(self, setpoints: tuple[ParameterBase, ...]) -> None:
        """
        Configures the gettable parameter from the measurement object.
        This method sets the sweep dimensions, batch size, and snaked shape
        based on the sweeps defined in the measurement.

        Args:
            setpoints (Tuple[ParameterBase, ...]): The setpoint parameters for this gettable
        """
        self.setpoints = setpoints
        self.vals = Arrays(
            shape = tuple(len(param.get()) for param in self.setpoints))
        self.is_mock = self.measurement.is_mock
    
    def set_qm_buffer(self, qm_job: 'RunningQmJob') -> None:
        """
        Fetches the QM buffer result from the QM driver and assigns it to the
        `buffer` attribute.
        
        Args:
            qm_driver (RunningQmJob): The QM driver instance to fetch the buffer from.
        """
        buffer_name = self.full_name
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
        if any([x.snake_scan for x in self.measurement.sweeps]):
            raise NotImplementedError(
                "Snaked data reshaping is not yet implemented."
            )
        return data

    def _fetch_opx_buffer(self):
        """
        Fetches the OPX buffer into the `buffer_val` and increments the internal
        counter `count`
        """
        buffer_val = np.array(self.buffer.fetch_all(), dtype = float)
        return buffer_val

    def unpack_self(self, value: ValuesType) -> list[tuple[ParameterBase, ValuesType]]:
        """
        Unpacks the ParameterWithSetpoints, its setpoints and any inferred
        parameters controlled by the setpoints.
        Args:
            value(ValuesType): The data acquired from this parameter.
        Returns:
            A list of tuples of parameters and values to be added as results
            to the dataset.
        """
        unpacked_results: list[tuple[ParameterBase, ValuesType]] = []
        setpoint_params = list(self.setpoints)
        setpoint_data = [param.get() for param in setpoint_params]
        output_grids = list(np.meshgrid(*setpoint_data, indexing="ij"))
        for i, param in enumerate(setpoint_params[:]):
            for inferred_param in param.has_control_of:
                copy_setpoint_data = setpoint_data[:]
                copy_setpoint_data[i] = inferred_param.get()
                setpoint_params.append(inferred_param)
                output_grids.append(
                    np.meshgrid(*copy_setpoint_data, indexing="ij")[i]
                )
        unpacked_results = list(zip(setpoint_params, output_grids))
        unpacked_results.extend(
            [(self, value)]
        )  # Must come last to preserve original ordering
        return unpacked_results
    
    def get_mock_result(self):
        """
        Generates linearly increasing results filling the shape of the batch
        """
        mock_result = np.linspace(0, 1, num=np.prod(list(self.vals.shape)))
        mock_result = mock_result.reshape(self.vals.shape)
        return mock_result
    
    def get_full_dims_and_coords(
            self, ext_dims: list[str], ext_coords: dict[str, ndarray]
        ) -> tuple[list[str], dict[str, ndarray]]:
        """
        Returns the full dims and coordinates for xarray DataArray generation

        Args:
            ext_dims (list): list of external dimesions
            external_coords (dict): 
        """
        dims = copy.copy(ext_dims)
        coords = copy.copy(ext_coords)
        for param in self.setpoints:
            dims.append(param.register_name)
            name = param.register_name
            coords[name] = (name, param.get())
            for inferred_param in param.depends_on:
                coords[inferred_param] = (name, inferred_param.get())
        return dims, coords
