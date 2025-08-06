"""Module testing the Program class"""
import pytest
from arbok_driver import Measurement, ArbokDriver, Device

def test_arbok_driver_init(arbok_driver)-> None:
    """Tests if arbok_driver is correctly initialized"""
    assert arbok_driver.name == 'arbok_driver'
    assert arbok_driver.device.name == 'dummy_device'
    assert arbok_driver.measurements == []

def test_arbok_driver_adding_measurement(arbok_driver, dummy_device)-> None:
    """Tests if measurement is correctly added to arbok_driver"""
    meas = Measurement(arbok_driver, 'dummy_measurement', dummy_device)
    assert len(arbok_driver.measurements) == 1
    assert arbok_driver.measurements[0] == meas
    assert len(arbok_driver.submodules) == 1

    arbok_driver.reset_measurements()
    assert len(arbok_driver.measurements) == 0
    assert len(arbok_driver.submodules) == 0
