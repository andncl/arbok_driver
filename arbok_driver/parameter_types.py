""" Module containing ParameterType classes """
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Generic, TypeVar

import numpy as np
from qm import qua
from qm.qua._expressions import QuaVariable, Scalar
from qcodes.validators import (
    Arrays, Numbers, Ints, MultiTypeOr, Strings, Sequence, Bool
)
from .parameters.sequence_parameter import SequenceParameter

K = TypeVar("K", bound=str)
V = TypeVar("V", covariant = True)

@dataclass(frozen=True)
class ParameterMap(Mapping[K, V], Generic[K, V]):
    _mapping: Mapping[K, V]

    def __getitem__(self, key: K) -> V:
        return self._mapping[key]

    def __iter__(self):
        return iter(self._mapping)

    def __len__(self) -> int:
        return len(self._mapping)
        
class Time(SequenceParameter[int]):
    """
    Cycles sequence parameter. Parameter values and sweeps are given in units of 
    FPGA cycles (4 ns). The parameter is converted to seconds before being
    registered to a measurement.
    """
    unit = 's'
    """ Default: 'cycles' """
    var_type = int
    """ Default: int """
    vals = Ints()
    scale = 1
    sweep_validator = None
    ### TODO: Implement vals. User should only be able to set ints (cycles)
    """ Default: Numbers """

    def convert_to_real_units(self, value):
        return np.array(np.array(value)*4e-9)

class String(SequenceParameter[str]):
    unit = 'N/A'
    """ Default: 'N/A' """
    var_type = str
    """ Default: str """
    vals = Strings()
    scale = None
    """ Default: Strings """
    sweep_validator = MultiTypeOr(Strings(), Arrays(valid_types = [None]))

class Voltage(SequenceParameter[float | QuaVariable]):
    unit = 'V'
    """ Default: 'V' """
    var_type = qua.fixed
    """ Default: fixed """
    vals = Numbers()
    scale = 1
    sweep_validator = MultiTypeOr(Numbers(), Arrays(valid_types = [float]))
    """ Default: Numbers """

class Frequency(SequenceParameter[int | QuaVariable]):
    unit = 'Hz'
    """ Default: 'Hz' """
    var_type = int
    """ Default: 'qua.fixed' """
    vals = Numbers()
    scale = 1
    sweep_validator = MultiTypeOr(Numbers(), Arrays(valid_types = [int]))
    """ Default: Numbers """

class Amplitude(SequenceParameter[float | Scalar]):
    unit = None
    var_type = qua.fixed
    """ Default: fixed """
    vals = Numbers(min_value = -2, max_value = 2)
    scale = 1
    sweep_validator = MultiTypeOr(
        Numbers(min_value = -2, max_value = 2),
        Arrays(valid_types = [float])
        )
    """ Default: Numbers """

class List(SequenceParameter[list]):
    unit = 'N/A'
    """ Default: 'N/A' """
    var_type = None
    """ Default: str """
    vals = Sequence()
    scale = None
    """ Default: Strings """
    sweep_validator = Sequence()

class Int(SequenceParameter[int | QuaVariable]):
    var_type = int
    """ Default: int """
    vals = Ints()
    scale = 1
    sweep_validator = MultiTypeOr(Numbers(), Arrays(valid_types = [int]))

class Boolean(SequenceParameter[bool]):
    var_type = bool
    """ Default: int """
    vals = Bool()
    scale = None
    sweep_validator = None

class Radian(SequenceParameter[float]):
    unit = 'pi'
    var_type = qua.fixed
    vals = Numbers(min_value = -2*np.pi, max_value = 2*np.pi)
    scale = 1
    sweep_validator = MultiTypeOr(
        Numbers(min_value = -2*np.pi, max_value = 2*np.pi),
        Arrays(valid_types = [float])
        )

class Pi(SequenceParameter):
    unit = 'pi'
    var_type = qua.fixed
    scale = 1
    vals = Numbers(min_value = -2, max_value = 2)
    sweep_validator = MultiTypeOr(
        Numbers(min_value = -2, max_value = 2),
        Arrays(valid_types = [float])
        )
