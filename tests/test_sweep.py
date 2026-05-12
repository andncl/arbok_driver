"""Module containing tests for Sweep class snake scanning"""
import re

import numpy as np
from qm import generate_qua_script


class TestSnakeScanProperty:
    """Tests for snake_scan property on Sweep"""

    def test_snake_scan_defaults_to_false(
            self, empty_sub_seq_1, mock_measurement):
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.par1: np.arange(10)},
        )
        assert mock_measurement.sweeps[0].snake_scan is False

    def test_snake_scan_can_be_enabled(
            self, empty_sub_seq_1, mock_measurement):
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.par1: np.arange(10)},
        )
        mock_measurement.sweeps[0].snake_scan = True
        assert mock_measurement.sweeps[0].snake_scan is True


class TestSnakeScanQUACompilation:
    """Tests verifying QUA program compiles correctly with snake scanning"""

    def test_snake_on_inner_parametrized_sweep_adds_if_else(
            self, empty_sub_seq_1, mock_measurement):
        """Snaking on a parametrized inner sweep should produce if/else"""
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.par1: np.arange(0, 10, 1)},
            {empty_sub_seq_1.par2: np.arange(0, 20, 1)},
        )
        mock_measurement.sweeps[1].snake_scan = True
        qua_prog = mock_measurement.get_qua_program()
        qua_prog_str = generate_qua_script(qua_prog)
        # Snake adds: 1 bool declare, if_/else_ branching
        assert len(re.findall(r'declare\(bool', qua_prog_str)) >= 1
        assert 'if_(' in qua_prog_str
        assert 'else_' in qua_prog_str

    def test_snake_on_inner_explicit_array_sweep_adds_if_else(
            self, empty_sub_seq_1, mock_measurement):
        """Snaking on a non-linear (explicit array) inner sweep"""
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.par1: np.arange(0, 10, 1)},
            {empty_sub_seq_1.par2: np.array([1, 3, 7, 12, 20, 31, 45, 60])},
        )
        mock_measurement.sweeps[1].snake_scan = True
        qua_prog = mock_measurement.get_qua_program()
        qua_prog_str = generate_qua_script(qua_prog)
        assert len(re.findall(r'declare\(bool', qua_prog_str)) >= 1
        assert 'if_(' in qua_prog_str
        assert 'else_' in qua_prog_str

    def test_no_snake_does_not_add_if_else(
            self, empty_sub_seq_1, mock_measurement):
        """Without snaking, no if/else branching should appear"""
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.par1: np.arange(0, 10, 1)},
            {empty_sub_seq_1.par2: np.arange(0, 20, 1)},
        )
        qua_prog = mock_measurement.get_qua_program()
        qua_prog_str = generate_qua_script(qua_prog)
        assert 'if_(' not in qua_prog_str
        assert 'else_' not in qua_prog_str

    def test_snake_declares_bool_variable(
            self, empty_sub_seq_1, mock_measurement):
        """Snaking should declare exactly one bool variable for the direction"""
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.par1: np.arange(0, 10, 1)},
            {empty_sub_seq_1.par2: np.arange(0, 20, 1)},
        )
        # Count bool declares without snaking
        qua_prog = mock_measurement.get_qua_program()
        qua_prog_str = generate_qua_script(qua_prog)
        bool_declares_without = len(
            re.findall(r'declare\(bool', qua_prog_str))

        # Now with snaking
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.par1: np.arange(0, 10, 1)},
            {empty_sub_seq_1.par2: np.arange(0, 20, 1)},
        )
        mock_measurement.sweeps[1].snake_scan = True
        qua_prog = mock_measurement.get_qua_program()
        qua_prog_str = generate_qua_script(qua_prog)
        bool_declares_with = len(
            re.findall(r'declare\(bool', qua_prog_str))

        assert bool_declares_with == bool_declares_without + 1

    def test_snake_on_multiple_axes(
            self, empty_sub_seq_1, mock_measurement):
        """Snaking on two inner axes should produce multiple if/else blocks"""
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.par1: np.arange(0, 10, 1)},
            {empty_sub_seq_1.par2: np.arange(0, 8, 1)},
            {empty_sub_seq_1.v_home_P1: np.arange(-0.1, 0.1, 0.01)},
        )
        mock_measurement.sweeps[1].snake_scan = True
        mock_measurement.sweeps[2].snake_scan = True
        qua_prog = mock_measurement.get_qua_program()
        qua_prog_str = generate_qua_script(qua_prog)
        assert len(re.findall(r'declare\(bool', qua_prog_str)) >= 2
        assert len(re.findall(r'if_\(', qua_prog_str)) >= 2


class TestReverseIdx:
    """Tests for _reverse_idx computation"""

    def test_reverse_idx_value(self, empty_sub_seq_1, mock_measurement):
        """_reverse_idx should return length - 1 - idx"""
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.par1: np.arange(10)},
        )
        sweep = mock_measurement.sweeps[0]
        assert sweep._reverse_idx(0) == 9
        assert sweep._reverse_idx(4) == 5
        assert sweep._reverse_idx(9) == 0
