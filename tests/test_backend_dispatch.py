"""Tests for backend-keyed method dispatch on SubSequence."""
import pytest

from arbok_driver import SubSequence, ParameterClass, arbok
from arbok_driver.backends.sim_backend import SimBackend
from arbok_driver.backends.qua_backend import QuaBackend
from arbok_driver.parameter_types import Int


class MinimalParams(ParameterClass):
    pass


class GenericSequence(SubSequence):
    """Only defines fpga_sequence — works on all backends."""
    PARAMETER_CLASS = MinimalParams

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.called_by = None

    def fpga_sequence(self):
        self.called_by = 'fpga_sequence'


class BackendKeyedSequence(SubSequence):
    """Defines backend-specific overrides."""
    PARAMETER_CLASS = MinimalParams

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.called_by = None

    def fpga_sequence__qua(self):
        self.called_by = 'fpga_sequence__qua'

    def fpga_sequence__sim(self):
        self.called_by = 'fpga_sequence__sim'


class MixedSequence(SubSequence):
    """Has both a default and a backend-specific override."""
    PARAMETER_CLASS = MinimalParams

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.called_by = None

    def fpga_sequence(self):
        self.called_by = 'fpga_sequence'

    def fpga_sequence__sim(self):
        self.called_by = 'fpga_sequence__sim'


class LegacyOnlySequence(SubSequence):
    """Only defines qua_sequence (legacy)."""
    PARAMETER_CLASS = MinimalParams

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.called_by = None

    def qua_sequence(self):
        self.called_by = 'qua_sequence'


class LegacyAllHooksSequence(SubSequence):
    """Defines all legacy qua_* hooks."""
    PARAMETER_CLASS = MinimalParams

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hooks_called = []

    def qua_declare(self):
        self.hooks_called.append('qua_declare')

    def qua_before_sequence(self):
        self.hooks_called.append('qua_before_sequence')

    def qua_sequence(self):
        self.hooks_called.append('qua_sequence')

    def qua_after_sequence(self):
        self.hooks_called.append('qua_after_sequence')

    def qua_stream(self):
        self.hooks_called.append('qua_stream')


class LegacyWithFpgaMixSequence(SubSequence):
    """Mixes legacy qua_declare with new fpga_sequence__qua."""
    PARAMETER_CLASS = MinimalParams

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hooks_called = []

    def qua_declare(self):
        self.hooks_called.append('qua_declare')

    def fpga_sequence__qua(self):
        self.hooks_called.append('fpga_sequence__qua')


class TestBackendDispatch:
    def test_fpga_sequence_called_on_any_backend(self, mock_measurement):
        seq = GenericSequence(mock_measurement, 'generic', {})
        seq._dispatch('sequence')
        assert seq.called_by == 'fpga_sequence'

    def test_backend_keyed_method_called_for_qua(self, mock_measurement):
        seq = BackendKeyedSequence(mock_measurement, 'keyed', {})
        seq._dispatch('sequence')
        assert seq.called_by == 'fpga_sequence__qua'

    def test_backend_keyed_method_called_for_sim(self, mock_measurement):
        seq = BackendKeyedSequence(mock_measurement, 'keyed', {})
        driver = mock_measurement.driver
        sim = SimBackend()
        original = driver.backend
        driver.backend = sim
        arbok.set_active_backend(sim)
        try:
            seq._dispatch('sequence')
            assert seq.called_by == 'fpga_sequence__sim'
        finally:
            driver.backend = original
            arbok.set_active_backend(original)

    def test_backend_keyed_takes_priority_over_fpga(self, mock_measurement):
        """fpga_sequence__sim wins over fpga_sequence when SimBackend active."""
        seq = MixedSequence(mock_measurement, 'mixed', {})
        driver = mock_measurement.driver
        sim = SimBackend()
        original = driver.backend
        driver.backend = sim
        arbok.set_active_backend(sim)
        try:
            seq._dispatch('sequence')
            assert seq.called_by == 'fpga_sequence__sim'
        finally:
            driver.backend = original
            arbok.set_active_backend(original)

    def test_mixed_falls_back_to_fpga_on_qua(self, mock_measurement):
        """No fpga_sequence__qua defined, so fpga_sequence is used."""
        seq = MixedSequence(mock_measurement, 'mixed', {})
        seq._dispatch('sequence')
        assert seq.called_by == 'fpga_sequence'

    def test_legacy_qua_sequence_used_on_qua_backend(self, mock_measurement):
        seq = LegacyOnlySequence(mock_measurement, 'legacy', {})
        seq._dispatch('sequence')
        assert seq.called_by == 'qua_sequence'

    def test_legacy_qua_raises_on_non_qua_backend(self, mock_measurement):
        seq = LegacyOnlySequence(mock_measurement, 'legacy', {})
        driver = mock_measurement.driver
        sim = SimBackend()
        original = driver.backend
        driver.backend = sim
        arbok.set_active_backend(sim)
        try:
            with pytest.raises(NotImplementedError, match="qua_sequence"):
                seq._dispatch('sequence')
        finally:
            driver.backend = original
            arbok.set_active_backend(original)


class TestLegacyQuaNotation:
    """Tests verifying the old qua_* notation still works through dispatch."""

    def test_legacy_qua_declare_dispatched(self, mock_measurement):
        seq = LegacyAllHooksSequence(mock_measurement, 'legacy_all', {})
        seq._dispatch('declare')
        assert 'qua_declare' in seq.hooks_called

    def test_legacy_qua_before_sequence_dispatched(self, mock_measurement):
        seq = LegacyAllHooksSequence(mock_measurement, 'legacy_all', {})
        seq._dispatch('before_sequence')
        assert 'qua_before_sequence' in seq.hooks_called

    def test_legacy_qua_sequence_dispatched(self, mock_measurement):
        seq = LegacyAllHooksSequence(mock_measurement, 'legacy_all', {})
        seq._dispatch('sequence')
        assert 'qua_sequence' in seq.hooks_called

    def test_legacy_qua_after_sequence_dispatched(self, mock_measurement):
        seq = LegacyAllHooksSequence(mock_measurement, 'legacy_all', {})
        seq._dispatch('after_sequence')
        assert 'qua_after_sequence' in seq.hooks_called

    def test_legacy_qua_stream_dispatched(self, mock_measurement):
        seq = LegacyAllHooksSequence(mock_measurement, 'legacy_all', {})
        seq._dispatch('stream')
        assert 'qua_stream' in seq.hooks_called

    def test_all_legacy_hooks_dispatched_in_full_lifecycle(self, mock_measurement):
        """Simulates a full measurement lifecycle using dispatch on all hooks."""
        seq = LegacyAllHooksSequence(mock_measurement, 'legacy_all', {})
        for hook in ('declare', 'before_sequence', 'sequence', 'after_sequence', 'stream'):
            seq._dispatch(hook)
        assert seq.hooks_called == [
            'qua_declare',
            'qua_before_sequence',
            'qua_sequence',
            'qua_after_sequence',
            'qua_stream',
        ]

    def test_legacy_qua_declare_raises_on_sim_backend(self, mock_measurement):
        seq = LegacyAllHooksSequence(mock_measurement, 'legacy_all', {})
        driver = mock_measurement.driver
        sim = SimBackend()
        original = driver.backend
        driver.backend = sim
        arbok.set_active_backend(sim)
        try:
            with pytest.raises(NotImplementedError, match="qua_declare"):
                seq._dispatch('declare')
        finally:
            driver.backend = original
            arbok.set_active_backend(original)

    def test_legacy_mixed_with_new_notation(self, mock_measurement):
        """qua_declare (legacy) + fpga_sequence__qua (new) can coexist."""
        seq = LegacyWithFpgaMixSequence(mock_measurement, 'mixed_legacy', {})
        seq._dispatch('declare')
        seq._dispatch('sequence')
        assert seq.hooks_called == ['qua_declare', 'fpga_sequence__qua']
