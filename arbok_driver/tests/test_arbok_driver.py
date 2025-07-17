"""Module testing the Program class"""
import pytest
from arbok_driver import Sequence, ArbokDriver, Device

def test_arbok_driver_init(arbok_driver)-> None:
    """Tests if arbok_driver is correctly initialized"""
    assert arbok_driver.name == 'arbok_driver'
    assert arbok_driver.device.name == 'dummy_device'
    assert arbok_driver.sequences == []

def test_arbok_driver_adding_sequence(arbok_driver, dummy_device)-> None:
    """Tests if sequence is correctly added to arbok_driver"""
    seq = Sequence(arbok_driver, 'dummy_sequence', dummy_device)
    assert len(arbok_driver.sequences) == 1
    assert arbok_driver.sequences[0] == seq
    assert len(arbok_driver.submodules) == 1

    arbok_driver.reset_sequences()
    assert len(arbok_driver.sequences) == 0
    assert len(arbok_driver.submodules) == 0
