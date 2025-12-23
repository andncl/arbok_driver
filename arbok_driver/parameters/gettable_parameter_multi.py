""" Module containing GettableParameter class """
from __future__ import annotations
from typing import TYPE_CHECKING
import logging
import hashlib
import warnings
import numpy as np

from qm import qua

from qcodes.validators import Arrays
from qcodes.parameters import ParameterWithSetpoints

from .gettable_parameter import GettableParameter
if TYPE_CHECKING:
    from qcodes.dataset.data_set_protocol import ValuesType
    from qcodes.parameters.parameter_base import ParameterBase

class GettableParameterMulti(GettableParameter):
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
            internal_setpoints: tuple[ParameterBase] | None = None,
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
        if internal_setpoints is not None:
            self.internal_setpoints = internal_setpoints
        else:
            self.internal_setpoints: tuple[ParameterBase] = ()

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

    def configure_from_measurement(self, setpoints: tuple[ParameterBase, ...]):
        """
        Configures the gettable parameter from the measurement object.
        This method sets the sweep dimensions, batch size, and snaked shape
        based on the sweeps defined in the measurement.
        """
        super().configure_from_measurement(
            self.internal_setpoints + setpoints
        )

    def _fetch_opx_buffer(self):
        """
        Fetches the OPX buffer into the `buffer_val` and increments the internal
        counter `count`
        """
        buffer_val = np.array(self.buffer.fetch_all(), dtype = float)
        return buffer_val

    def qua_declare_variables(self) -> None:
        """Declares the qua variables and streams for this gettable"""
        self.qua_var = qua.declare(self.var_type)
        self.qua_stream = qua.declare_stream()

    def qua_save_variables(self) -> None:
        """Saves acquired results to qua stream"""
        qua.save(self.qua_var, self.qua_stream)

    def qua_save_streams(self) -> None:
        """Saves acquired results to qua stream"""
        buffer = self.qua_stream.buffer(*self.vals.shape)
        buffer.save(self.full_name)
