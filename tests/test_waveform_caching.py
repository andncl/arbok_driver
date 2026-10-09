"""Tests for waveform caching in sweep and ramp."""
import re

import numpy as np
import pytest
from qm import generate_qua_script

from arbok_driver.backend import as_channel_map
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

    def test_samples_are_plain_floats(self):
        """
        Numpy waveforms are stored as builtin floats.

        Numpy scalars serialize as `np.float64(0.1)` instead of `0.1`, which
        multiplies the size of the generated program by the sample count.
        """
        opx_config = {'elements': {'q1': {}}}
        samples_array = [np.full(50, 0.1), np.full(50, 0.2)]
        _inject_wfc_config(opx_config, 'q1', 'my_op', samples_array, 50)

        for samples in opx_config['waveforms']['my_op_wf']['samples_array']:
            assert type(samples) is list
            assert {type(sample) for sample in samples} == {float}


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


class TestInjectWfcConfigIQ:
    """
    Caching an up-converted pulse.

    A generator returning `{'I': ..., 'Q': ...}` is cached as two array
    waveforms. `load_waveform` selects by pulse, so one index still picks a
    consistent pair of quadratures.
    """

    @staticmethod
    def iq_samples_array(nr_waveforms = 3, length = 50):
        """Returns one I/Q waveform per sweep index"""
        return [
            {'I': [0.1*(index + 1)]*length, 'Q': [-0.1*(index + 1)]*length}
            for index in range(nr_waveforms)
        ]

    def test_injects_one_array_waveform_per_quadrature(self):
        opx_config = {'elements': {'q1': {}}}
        _inject_wfc_config(
            opx_config, 'q1', 'test_op', self.iq_samples_array(), 50)

        for channel, sign in (('I', 1), ('Q', -1)):
            wf = opx_config['waveforms'][f'test_op_{channel}_wf']
            assert wf['type'] == 'array'
            assert len(wf['samples_array']) == 3
            assert wf['samples_array'][1] == [sign*0.2]*50

    def test_pulse_points_at_both_quadratures(self):
        opx_config = {'elements': {'q1': {}}}
        _inject_wfc_config(
            opx_config, 'q1', 'my_op', self.iq_samples_array(), 50)

        pulse = opx_config['pulses']['my_op_pulse']
        assert pulse['waveforms'] == {
            'I': 'my_op_I_wf', 'Q': 'my_op_Q_wf'}
        assert pulse['length'] == 50
        assert opx_config['elements']['q1']['operations']['my_op'] \
            == 'my_op_pulse'

    def test_single_channel_waveform_name_is_unchanged(self):
        """
        A DC pulse keeps its historic unsuffixed waveform name.

        Configs generated before I/Q support have to stay byte identical, the
        name ends up in saved configs and in user code selecting operations.
        """
        opx_config = {'elements': {'q1': {}}}
        _inject_wfc_config(opx_config, 'q1', 'my_op', [[0.1]*50], 50)

        assert 'my_op_wf' in opx_config['waveforms']
        assert opx_config['pulses']['my_op_pulse']['waveforms'] \
            == {'single': 'my_op_wf'}

    def test_samples_are_plain_floats(self):
        """Numpy quadratures are converted just like single traces"""
        opx_config = {'elements': {'q1': {}}}
        samples_array = [
            {'I': np.full(50, 0.1), 'Q': np.full(50, 0.2)}]
        _inject_wfc_config(opx_config, 'q1', 'my_op', samples_array, 50)

        for channel in ('I', 'Q'):
            samples = opx_config['waveforms'][
                f'my_op_{channel}_wf']['samples_array'][0]
            assert type(samples) is list
            assert {type(sample) for sample in samples} == {float}

    def test_mixing_single_and_iq_waveforms_is_rejected(self):
        """One pulse plays all cached waveforms, so they share their channels"""
        opx_config = {'elements': {'q1': {}}}
        samples_array = [{'I': [0.1]*50, 'Q': [0.2]*50}, [0.1]*50]
        with pytest.raises(ValueError, match='same channels'):
            _inject_wfc_config(opx_config, 'q1', 'my_op', samples_array, 50)

    def test_quadratures_of_different_length_are_rejected(self):
        opx_config = {'elements': {'q1': {}}}
        samples_array = [{'I': [0.1]*50, 'Q': [0.2]*40}]
        with pytest.raises(ValueError, match='same length'):
            _inject_wfc_config(opx_config, 'q1', 'my_op', samples_array, 50)

    def test_unknown_channel_keys_are_rejected(self):
        opx_config = {'elements': {'q1': {}}}
        with pytest.raises(ValueError, match='waveform dict must hold'):
            _inject_wfc_config(
                opx_config, 'q1', 'my_op', [{'i': [0.1]*50}], 50)

    def test_iq_waveform_on_a_dc_element_is_rejected(self):
        """
        The element's input declaration has to match what was generated.

        The hardware rejects the mismatch too, but only with a compilation
        error far away from the generator that caused it.
        """
        opx_config = {'elements': {'P1': {'singleInput': {'port': ('con1', 1)}}}}
        with pytest.raises(ValueError, match='singleInput element'):
            _inject_wfc_config(
                opx_config, 'P1', 'my_op', self.iq_samples_array(), 50)

    def test_single_waveform_on_an_iq_element_is_rejected(self):
        opx_config = {'elements': {'q1': {'mixInputs': {'I': (), 'Q': ()}}}}
        with pytest.raises(ValueError, match='mixInputs/MWInput'):
            _inject_wfc_config(opx_config, 'q1', 'my_op', [[0.1]*50], 50)


class TestAsChannelMap:
    """
    Tests for the shared waveform normalizer.

    It is what makes an I/Q pulse need no declaration: the shape of the
    samples decides which channels are driven, everywhere waveforms enter the
    driver (`arbok.play`, `load_waveform_table`, the simulation backend).
    """

    def test_a_real_trace_drives_a_single_channel(self):
        assert as_channel_map([0.1, 0.2]) == {'single': [0.1, 0.2]}

    def test_a_dict_drives_both_quadratures(self):
        channels = as_channel_map({'I': [0.1], 'Q': [0.2]})
        assert channels == {'I': [0.1], 'Q': [0.2]}

    def test_quadrature_order_is_fixed(self):
        """I always comes first, whatever order the caller used"""
        channels = as_channel_map({'Q': [0.2], 'I': [0.1]})
        assert list(channels) == ['I', 'Q']

    def test_a_complex_trace_is_split_into_quadratures(self):
        """
        A complex trace is `I + 1j*Q`.

        That is what a rotating frame envelope is written as, and what
        `simulate_pulse_waveforms` returns for an up-converted element, so it
        can be cached without unpacking it by hand.
        """
        channels = as_channel_map(np.array([0.1 + 0.2j, -0.1 - 0.2j]))
        assert channels == {'I': [0.1, -0.1], 'Q': [0.2, -0.2]}

    def test_samples_are_plain_floats(self):
        channels = as_channel_map({'I': np.full(2, 0.1), 'Q': np.full(2, 0.2)})
        for trace in channels.values():
            assert {type(sample) for sample in trace} == {float}

    def test_unknown_keys_are_rejected(self):
        with pytest.raises(ValueError, match='waveform dict must hold'):
            as_channel_map({'I': [0.1], 'Q': [0.2], 'single': [0.3]})

    def test_quadratures_of_different_length_are_rejected(self):
        with pytest.raises(ValueError, match='same length'):
            as_channel_map({'I': [0.1, 0.2], 'Q': [0.2]})
