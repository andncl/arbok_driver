""" Module containing ParameterType classes """

import numpy as np
from qm import qua
from qcodes.validators import (
    Arrays, Numbers, Ints, MultiTypeOr, Strings, Sequence, Bool
)
from .sequence_parameter import SequenceParameter

class Time(SequenceParameter):
    """
    Cycles sequence parameter. Parameter values and sweeps are given in units of 
    FPGA cycles (4 ns). The parameter is converted to seconds before being
    registered to a measurement.
    """
    unit = 's'
    """ Default: 'cycles' """
    qua_type = int
    """ Default: int """
    validator = Ints()
    sweep_validator = None
    ### TODO: Implement validator. User should only be able to set ints (cycles)
    """ Default: Numbers """

    def convert_to_real_units(self, value):
        return np.array(np.array(value)*4e-9)

class String(SequenceParameter):
    unit = 'N/A'
    """ Default: 'N/A' """
    qua_type = str
    """ Default: str """
    validator = Strings()
    scale = None
    """ Default: Strings """
    sweep_validator = MultiTypeOr(Strings(), Arrays(valid_types = [None]))

class Voltage(SequenceParameter):
    unit = 'V'
    """ Default: 'V' """
    qua_type = qua.fixed
    """ Default: fixed """
    validator = Numbers()
    sweep_validator = MultiTypeOr(Numbers(), Arrays(valid_types = [float]))
    """ Default: Numbers """

class Frequency(SequenceParameter):
    unit = 'Hz'
    """ Default: 'Hz' """
    qua_type = int
    """ Default: 'qua.fixed' """
    validator = Numbers()
    sweep_validator = MultiTypeOr(Numbers(), Arrays(valid_types = [int]))
    """ Default: Numbers """

class Amplitude(SequenceParameter):
    unit = None
    qua_type = qua.fixed
    """ Default: fixed """
    validator = Numbers(min_value = -2, max_value = 2)
    sweep_validator = MultiTypeOr(
        Numbers(min_value = -2, max_value = 2),
        Arrays(valid_types = [float])
        )
    """ Default: Numbers """

class List(SequenceParameter):
    unit = 'N/A'
    """ Default: 'N/A' """
    qua_type = None
    """ Default: str """
    validator = Sequence()
    scale = None
    """ Default: Strings """
    sweep_validator = Sequence()

class Int(SequenceParameter):
    qua_type = int
    """ Default: int """
    validator = Ints()
    sweep_validator = MultiTypeOr(Numbers(), Arrays(valid_types = [int]))

class Boolean(SequenceParameter):
    qua_type = bool
    """ Default: int """
    validator = Bool()
    scale = None
    sweep_validator = None

class Radian(SequenceParameter):
    unit = 'pi'
    qua_type = qua.fixed
    validator = Numbers(min_value = -2*np.pi, max_value = 2*np.pi)
    sweep_validator = MultiTypeOr(
        Numbers(min_value = -2*np.pi, max_value = 2*np.pi),
        Arrays(valid_types = [float])
        )

class Pi(SequenceParameter):
    unit = 'pi'
    qua_type = qua.fixed
    validator = Numbers(min_value = -2, max_value = 2)
    sweep_validator = MultiTypeOr(
        Numbers(min_value = -2, max_value = 2),
        Arrays(valid_types = [float])
        )
