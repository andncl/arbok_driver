"""Module containing test for MeasurementRunner class"""
import pytest
from unittest.mock import MagicMock

import numpy as np

from arbok_driver.measurement_runners.measurement_runner_base import (
    _flip_alternating_slices,
)


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


class TestFlipAlternatingSlices:
    """Tests for the _flip_alternating_slices helper function"""

    def test_2d_flips_odd_rows(self):
        """Odd rows along axis 0 should have axis 1 reversed"""
        expected = np.arange(12).reshape(4, 3)
        snaked = expected.copy()
        snaked[1] = snaked[1, ::-1]
        snaked[3] = snaked[3, ::-1]
        result = _flip_alternating_slices(snaked, outer_axis=0, flip_axis=1)
        np.testing.assert_array_equal(result, expected)

    def test_3d_flips_along_inner_axis(self):
        """Snake on axis 2, driven by axis 1"""
        expected = np.arange(24).reshape(2, 3, 4)
        snaked = expected.copy()
        snaked[:, 1, :] = snaked[:, 1, ::-1]
        result = _flip_alternating_slices(snaked, outer_axis=1, flip_axis=2)
        np.testing.assert_array_equal(result, expected)

    def test_3d_flips_along_middle_axis(self):
        """Snake on axis 1, driven by axis 0"""
        expected = np.arange(24).reshape(2, 3, 4)
        snaked = expected.copy()
        snaked[1, :, :] = snaked[1, ::-1, :]
        result = _flip_alternating_slices(snaked, outer_axis=0, flip_axis=1)
        np.testing.assert_array_equal(result, expected)

    def test_does_not_modify_input(self):
        """The original array should not be mutated"""
        data = np.arange(6).reshape(2, 3)
        data[1] = data[1, ::-1]
        original = data.copy()
        _flip_alternating_slices(data, outer_axis=0, flip_axis=1)
        np.testing.assert_array_equal(data, original)

    def test_single_outer_element_no_flip(self):
        """With only one element on the outer axis, nothing should flip"""
        data = np.arange(5).reshape(1, 5)
        result = _flip_alternating_slices(data, outer_axis=0, flip_axis=1)
        np.testing.assert_array_equal(result, data)


class TestUnsnakeResult:
    """Tests for MeasurementRunnerBase.unsnake_result using mocked sweeps"""

    def _make_runner_with_sweeps(self, snake_flags: list[bool], shape: tuple):
        """
        Creates a MeasurementRunnerBase-like object with mocked sweeps.
        snake_flags[i] corresponds to sweep axis i.
        """
        from arbok_driver.measurement_runners.measurement_runner_base import (
            MeasurementRunnerBase,
        )
        sweeps = []
        for flag in snake_flags:
            sweep = MagicMock()
            sweep.snake_scan = flag
            sweeps.append(sweep)

        runner = MagicMock(spec=MeasurementRunnerBase)
        runner.measurement = MagicMock()
        runner.measurement.sweeps = sweeps
        runner.unsnake_result = MeasurementRunnerBase.unsnake_result.__get__(
            runner, MeasurementRunnerBase)
        return runner

    def test_no_snaking_returns_copy(self):
        """With no snaked axes, data should be unchanged"""
        runner = self._make_runner_with_sweeps([False, False], (4, 5))
        data = np.arange(20).reshape(4, 5)
        result = runner.unsnake_result(data)
        np.testing.assert_array_equal(result, data)

    def test_inner_axis_snaked_2d(self):
        """Inner sweep (axis 1) snaked: odd rows reversed"""
        runner = self._make_runner_with_sweeps([False, True], (4, 5))
        expected = np.arange(20).reshape(4, 5)
        snaked = expected.copy()
        snaked[1] = snaked[1, ::-1]
        snaked[3] = snaked[3, ::-1]
        result = runner.unsnake_result(snaked)
        np.testing.assert_array_equal(result, expected)

    def test_outermost_snaked_is_skipped(self):
        """Axis 0 snaked has no outer axis to drive alternation — skip it"""
        runner = self._make_runner_with_sweeps([True, False], (4, 5))
        data = np.arange(20).reshape(4, 5)
        result = runner.unsnake_result(data)
        np.testing.assert_array_equal(result, data)

    def test_multiple_snaked_axes_3d(self):
        """Both axis 1 and axis 2 snaked in a 3D array"""
        runner = self._make_runner_with_sweeps([False, True, True], (2, 3, 4))
        expected = np.arange(24).reshape(2, 3, 4)
        snaked = expected.copy()
        # Axis 1 snaked (driven by axis 0): reverse axis 1 for odd on axis 0
        snaked[1, :, :] = snaked[1, ::-1, :]
        # Axis 2 snaked (driven by axis 1): reverse axis 2 for odd on axis 1
        snaked[:, 1, :] = snaked[:, 1, ::-1]
        result = runner.unsnake_result(snaked)
        np.testing.assert_array_equal(result, expected)

    def test_middle_axis_only_snaked_3d(self):
        """Only axis 1 snaked in 3D — axis 2 untouched"""
        runner = self._make_runner_with_sweeps([False, True, False], (3, 4, 5))
        expected = np.arange(60).reshape(3, 4, 5)
        snaked = expected.copy()
        snaked[1, :, :] = snaked[1, ::-1, :]
        result = runner.unsnake_result(snaked)
        np.testing.assert_array_equal(result, expected)
