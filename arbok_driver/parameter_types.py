""" Module containing ParameterType classes """

from .sequence_parameter import SequenceParameter
from qm import qua
from qcodes.validators import Arrays, Numbers, Ints

class Time(SequenceParameter):
    unit = 'cycles'
    """ Default: 'cycles' """
    qua_type = int
    """ Default: int """
    validator = Ints()
    """ Default: Numbers """

class Voltage(SequenceParameter):
    unit = 'V'
    """ Default: 'V' """
    qua_type = qua.fixed
    """ Default: fixed """
    validator = Numbers()
    """ Default: Numbers """

class Frequency(SequenceParameter):
    unit = 'Hz'
    """ Default: 'Hz' """
    qua_type = qua.fixed
    """ Default: 'qua.fixed' """
    validator = Numbers()
    """ Default: Numbers """
