""" Module containing ParameterType classes """

import numpy as np
from qm import qua
from qcodes.validators import (
    Arrays, Numbers, Ints, MultiTypeOr, Strings, Sequence
)
from .sequence_parameter import SequenceParameter

class Time(SequenceParameter):
    unit = 'cycles'
    """ Default: 'cycles' """
    qua_type = int
    """ Default: int """
    validator = Ints()
    sweep_validator = MultiTypeOr(Ints(), Arrays(valid_types = [int]))
    """ Default: Numbers """

class String(SequenceParameter):
    unit = 'N/A'
    """ Default: 'N/A' """
    qua_type = str
    """ Default: str """
    validator = Strings()
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
    validator = Numbers(min_value = 0, max_value = 1)
    sweep_validator = MultiTypeOr(
        Numbers(min_value = 0, max_value = 1),
        Arrays(valid_types = [float])
        )
    """ Default: Numbers """

class List(SequenceParameter):
    unit = 'N/A'
    """ Default: 'N/A' """
    qua_type = None
    """ Default: str """
    validator = Sequence()
    """ Default: Strings """
    sweep_validator = Sequence()

class Int(Time):
    unit = '#'

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
