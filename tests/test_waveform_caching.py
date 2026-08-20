"""Tests for waveform caching in sweep and ramp."""
import re

import numpy as np
import pytest
from qm import generate_qua_script

from arbok_driver.parameter_types import ParameterMap, Voltage
from arbok_driver.sweep import build_wfc_op_name, MAX_WFC_WAVEFORMS
from arbok_driver.arbok.play import (
    _inject_wfc_config,
    _compute_amplitude_array,
    _validate_wfc_eligibility,
    MAX_WFC_DURATION_NS,
)


class TestBuildWfcOpName:
    """Tests for the shared wfc operation name builder."""

    def test_name_without_reference(self, empty_sub_seq_1, mock_measurement):
        param = empty_sub_seq_1.v_home_P1
        name = build_wfc_op_name(param, None, 'P1')
        assert name.endswith('_wfc')
        assert 'v_home_P1' in name
        assert 'mock_measurement' not in name
        assert '_FROM_' not in name

    def test_name_with_reference(self, empty_sub_seq_1, empty_sub_seq_2,
                                 mock_measurement):
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        ref_map = empty_sub_seq_2._parameter_maps['v_home']
        name = build_wfc_op_name(target_map['P1'], ref_map, 'P1')
        assert '_FROM_' in name
        assert name.endswith('_wfc')

    def test_name_is_deterministic(self, empty_sub_seq_1, mock_measurement):
        param = empty_sub_seq_1.v_home_P1
        name1 = build_wfc_op_name(param, None, 'P1')
        name2 = build_wfc_op_name(param, None, 'P1')
        assert name1 == name2


class TestRegisterWaveformLoad:
    """Tests for Sweep.register_waveform_load."""

    def test_registers_successfully(self, empty_sub_seq_1, mock_measurement):
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: np.linspace(-0.1, 0.1, 100)},
        )
        sweep = mock_measurement.sweeps[0]
        sweep.register_waveform_load(target_map)
        assert len(sweep._waveform_cache_registrations) == 1

    def test_sets_wfc_active_flag(self, empty_sub_seq_1, mock_measurement):
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: np.linspace(-0.1, 0.1, 100)},
        )
        sweep = mock_measurement.sweeps[0]
        sweep.register_waveform_load(target_map)
        assert getattr(empty_sub_seq_1.v_home_P1, '_wfc_active', False)

    def test_skips_when_too_many_waveforms(
            self, empty_sub_seq_1, mock_measurement):
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: np.linspace(-0.1, 0.1, 1025)},
        )
        sweep = mock_measurement.sweeps[0]
        sweep.register_waveform_load(target_map)
        assert len(sweep._waveform_cache_registrations) == 0

    def test_skips_at_boundary_1024(
            self, empty_sub_seq_1, mock_measurement):
        """Exactly 1024 should still be eligible."""
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: np.linspace(-0.1, 0.1, 1024)},
        )
        sweep = mock_measurement.sweeps[0]
        sweep.register_waveform_load(target_map)
        assert len(sweep._waveform_cache_registrations) == 1

    def test_skips_when_user_disables(self, empty_sub_seq_1, mock_measurement):
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        empty_sub_seq_1.v_home_P1.use_waveform_caching = False
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: np.linspace(-0.1, 0.1, 100)},
        )
        sweep = mock_measurement.sweeps[0]
        sweep.register_waveform_load(target_map)
        assert len(sweep._waveform_cache_registrations) == 0

    def test_noop_when_param_not_in_sweep(
            self, empty_sub_seq_1, empty_sub_seq_2, mock_measurement):
        target_map = empty_sub_seq_2._parameter_maps['v_home']
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: np.linspace(-0.1, 0.1, 100)},
        )
        sweep = mock_measurement.sweeps[0]
        sweep.register_waveform_load(target_map)
        assert len(sweep._waveform_cache_registrations) == 0

    def test_registers_with_reference(
            self, empty_sub_seq_1, empty_sub_seq_2, mock_measurement):
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        ref_map = empty_sub_seq_2._parameter_maps['v_home']
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: np.linspace(-0.1, 0.1, 100)},
        )
        sweep = mock_measurement.sweeps[0]
        sweep.register_waveform_load(target_map, ref_map)
        assert len(sweep._waveform_cache_registrations) == 1


class TestEmitWaveformLoads:
    """Tests that load_waveform appears in QUA program when registered."""

    def test_load_waveform_in_qua_script(
            self, empty_sub_seq_1, mock_measurement):
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: np.linspace(-0.1, 0.1, 20)},
        )
        sweep = mock_measurement.sweeps[0]
        sweep.register_waveform_load(target_map)

        qua_prog = mock_measurement.get_qua_program()
        qua_script = generate_qua_script(qua_prog)
        assert 'load_waveform' in qua_script

    def test_no_load_waveform_without_registration(
            self, empty_sub_seq_1, mock_measurement):
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: np.linspace(-0.1, 0.1, 20)},
        )
        qua_prog = mock_measurement.get_qua_program()
        qua_script = generate_qua_script(qua_prog)
        assert 'load_waveform' not in qua_script

    def test_snake_scan_emits_both_directions(
            self, empty_sub_seq_1, mock_measurement):
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.par1: np.arange(0, 5, 1)},
            {empty_sub_seq_1.v_home_P1: np.linspace(-0.1, 0.1, 20)},
        )
        sweep = mock_measurement.sweeps[1]
        sweep.snake_scan = True
        sweep.register_waveform_load(target_map)

        qua_prog = mock_measurement.get_qua_program()
        qua_script = generate_qua_script(qua_prog)
        load_count = qua_script.count('load_waveform')
        assert load_count >= 2


class TestInjectWfcConfig:
    """Tests for _inject_wfc_config."""

    def test_injects_array_type_waveform(self):
        opx_config = {'elements': {'q1': {}}}
        samples_array = [[0.1] * 100, [0.2] * 100, [0.3] * 100]
        _inject_wfc_config(opx_config, 'q1', 'test_op', samples_array, 100)

        wf = opx_config['waveforms']['test_op_wf']
        assert wf['type'] == 'array'
        assert len(wf['samples_array']) == 3
        assert wf['samples_array'][0] == [0.1] * 100

    def test_injects_pulse_and_operation(self):
        opx_config = {'elements': {'q1': {}}}
        samples_array = [[0.1] * 50]
        _inject_wfc_config(opx_config, 'q1', 'my_op', samples_array, 50)

        assert opx_config['pulses']['my_op_pulse']['length'] == 50
        assert opx_config['elements']['q1']['operations']['my_op'] == 'my_op_pulse'


class TestValidateWfcEligibility:
    """Tests for _validate_wfc_eligibility."""

    def test_raises_on_swept_duration(self):
        with pytest.raises(ValueError, match="incompatible with swept duration"):
            _validate_wfc_eligibility(1000, dur_is_swept=True)

    def test_raises_on_duration_too_long(self):
        with pytest.raises(ValueError, match="duration <="):
            _validate_wfc_eligibility(MAX_WFC_DURATION_NS + 1, dur_is_swept=False)

    def test_passes_at_max_duration(self):
        _validate_wfc_eligibility(MAX_WFC_DURATION_NS, dur_is_swept=False)

    def test_passes_for_short_duration(self):
        _validate_wfc_eligibility(1000, dur_is_swept=False)


class TestComputeAmplitudeArray:
    """Tests for _compute_amplitude_array."""

    def test_target_only(self, empty_sub_seq_1, mock_measurement):
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        sweep_values = np.linspace(-0.1, 0.1, 10)
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: sweep_values},
        )
        amps = _compute_amplitude_array(
            empty_sub_seq_1.v_home_P1, None, 'P1')
        scale = empty_sub_seq_1.v_home_P1.scale
        np.testing.assert_array_almost_equal(amps, sweep_values * scale)

    def test_target_minus_fixed_reference(
            self, empty_sub_seq_1, empty_sub_seq_2, mock_measurement):
        target_map = empty_sub_seq_1._parameter_maps['v_home']
        ref_map = empty_sub_seq_2._parameter_maps['v_home']
        sweep_values = np.linspace(-0.1, 0.1, 10)
        mock_measurement.set_sweeps(
            {empty_sub_seq_1.v_home_P1: sweep_values},
        )
        scale = empty_sub_seq_1.v_home_P1.scale
        ref_value = empty_sub_seq_2.v_home_P1.get_raw()
        amps = _compute_amplitude_array(
            empty_sub_seq_1.v_home_P1, ref_map, 'P1')
        expected = sweep_values * scale - ref_value
        np.testing.assert_array_almost_equal(amps, expected)


class TestVoltageWfcAttribute:
    """Tests for use_waveform_caching attribute on Voltage."""

    def test_default_is_true(self, empty_sub_seq_1, mock_measurement):
        assert empty_sub_seq_1.v_home_P1.use_waveform_caching is True

    def test_can_be_disabled(self, empty_sub_seq_1, mock_measurement):
        empty_sub_seq_1.v_home_P1.use_waveform_caching = False
        assert empty_sub_seq_1.v_home_P1.use_waveform_caching is False
