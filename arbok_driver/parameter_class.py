"""Module containing ParameterClass"""
from abc import ABC
from dataclasses import dataclass, fields

@dataclass(frozen = True)
class ParameterClass(ABC):
    """
    Parent for shared identity for the parameter classes every sub-sequence should own
    """
    def __len__(self) -> int:
        return len(fields(self))

@dataclass(frozen = True)
class EmptyParameterClass(ParameterClass):
    """Empty ParameterClass for all sub-sequences that require no parameters"""
    pass
