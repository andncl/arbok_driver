""" Module containing ParameterType classes """

from .sequence_parameter import SequenceParameter
from qm import qua
from qcodes.validators import Arrays, Numbers, Ints, MultiTypeOr

class Time(SequenceParameter):
    unit = 'cycles'
    """ Default: 'cycles' """
    qua_type = int
    """ Default: int """
    validator = MultiTypeOr(Ints(), Arrays(valid_types = [int]))
    """ Default: Numbers """

class Voltage(SequenceParameter):
    unit = 'V'
    """ Default: 'V' """
    qua_type = qua.fixed
    """ Default: fixed """
    validator = MultiTypeOr(Numbers(), Arrays(valid_types = [float]))
    """ Default: Numbers """

class Frequency(SequenceParameter):
    unit = 'Hz'
    """ Default: 'Hz' """
    qua_type = qua.fixed
    """ Default: 'qua.fixed' """
    validator = MultiTypeOr(Numbers(), Arrays(valid_types = [float]))
    """ Default: Numbers """
