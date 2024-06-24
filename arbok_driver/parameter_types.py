""" Module containing ParameterType classes """

from .sequence_parameter import SequenceParameter
from qm import qua
from qcodes.validators import Arrays, Numbers, Ints, MultiTypeOr, Strings

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
    qua_type = qua.fixed
    """ Default: 'qua.fixed' """
    validator = Numbers()
    sweep_validator = MultiTypeOr(Numbers(), Arrays(valid_types = [float]))
    """ Default: Numbers """
