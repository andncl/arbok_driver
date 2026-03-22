"""Module containing test for MeasurementRunner class"""
import pytest

import numpy as np

def test_qcodes_measurement_runner(stability_map, mock_measurement) -> None:
    mock_measurement.driver.is_mock = True
    mock_measurement.set_sweeps(
        {stability_map.v_home_P1: np.arange(10)},
        {stability_map.v_home_P2: np.arange(5)}
        )
    mock_measurement.register_gettables(keywords = ['_'])
    nr_gettables = len(mock_measurement.gettables)
    mock_measurement.qc_measurement_name = 'test_measurement'
    mock_measurement.run_measurement(
        ext_sweep_list=[{stability_map.v_home_P3: np.arange(2)}])
    dataset = mock_measurement.dataset
    assert len(dataset) == nr_gettables
    first_dataarray = next(iter(dataset.data_vars.values()))
    assert first_dataarray.shape == (2, 10, 5)
