"""Tests for SimBackend play/wait/align with callable operations."""
import numpy as np
import pytest

from arbok_driver.backends.sim_backend import SimBackend


def ramp_generator(amplitude, dur_ns):
    """Simple linear ramp from 0 to amplitude."""
    return list(np.linspace(0, amplitude, dur_ns))


def constant_generator(amplitude, dur_ns):
    """Constant pulse at given amplitude."""
    return [amplitude] * dur_ns


class TestSimBackendPlay:
    def test_play_with_callable(self):
        sim = SimBackend()
        with sim.program_context():
            sim.play('P1', ramp_generator, 0.5, 25)

        wf = sim.get_waveforms()
        assert 'P1' in wf
        assert len(wf['P1']) == 100  # 25 cycles * 4 ns
        assert wf['P1'][-1] == pytest.approx(0.5)
        assert wf['P1'][0] == pytest.approx(0.0, abs=0.01)

    def test_play_raises_on_string_operation(self):
        sim = SimBackend()
        with sim.program_context():
            with pytest.raises(TypeError, match="requires a callable"):
                sim.play('P1', 'unit_ramp', 0.5, 25)

    def test_play_default_amplitude(self):
        sim = SimBackend()
        with sim.program_context():
            sim.play('P1', constant_generator)

        wf = sim.get_waveforms()
        # default amplitude=1.0, default duration=25 cycles=100ns
        assert len(wf['P1']) == 100
        assert all(s == pytest.approx(1.0) for s in wf['P1'])


class TestSimBackendWait:
    def test_wait_holds_last_voltage(self):
        sim = SimBackend()
        with sim.program_context():
            sim.play('P1', constant_generator, 0.3, 25)
            sim.wait(10, ['P1'])  # 10 cycles = 40ns

        wf = sim.get_waveforms()
        assert len(wf['P1']) == 140  # 100 + 40
        # Wait samples should hold at last played voltage
        assert all(s == pytest.approx(0.3) for s in wf['P1'][100:])

    def test_wait_at_zero_if_never_played(self):
        sim = SimBackend()
        with sim.program_context():
            sim.wait(10, ['P1'])

        wf = sim.get_waveforms()
        assert len(wf['P1']) == 40
        assert all(s == pytest.approx(0.0) for s in wf['P1'])


class TestSimBackendAlign:
    def test_align_pads_to_longest(self):
        sim = SimBackend()
        with sim.program_context():
            sim.play('P1', constant_generator, 0.5, 50)  # 200ns
            sim.play('P2', constant_generator, 0.3, 25)  # 100ns
            sim.align(['P1', 'P2'])

        wf = sim.get_waveforms()
        assert len(wf['P1']) == 200
        assert len(wf['P2']) == 200
        # P2 padded with its last voltage (0.3)
        assert wf['P2'][100] == pytest.approx(0.3)
        assert wf['P2'][-1] == pytest.approx(0.3)

    def test_align_all_elements(self):
        sim = SimBackend()
        with sim.program_context():
            sim.play('P1', constant_generator, 1.0, 50)  # 200ns
            sim.play('P2', constant_generator, 0.5, 25)  # 100ns
            sim.play('P3', constant_generator, 0.2, 10)  # 40ns
            sim.align()  # align all

        wf = sim.get_waveforms()
        assert len(wf['P1']) == len(wf['P2']) == len(wf['P3']) == 200

    def test_align_holds_at_current_voltage(self):
        sim = SimBackend()
        with sim.program_context():
            sim.play('P1', ramp_generator, 0.8, 25)  # ramps to 0.8
            sim.play('P2', constant_generator, 0.0, 10)  # 40ns at 0
            sim.align(['P1', 'P2'])

        wf = sim.get_waveforms()
        # P2 padded from 40ns to 100ns at its last voltage (0.0)
        assert len(wf['P2']) == 100
        assert wf['P2'][-1] == pytest.approx(0.0)


class TestSimBackendSequence:
    def test_play_wait_align_sequence(self):
        """Full sequence: play, wait, play on two elements, align."""
        sim = SimBackend()
        with sim.program_context():
            sim.play('P1', ramp_generator, 0.5, 25)    # 100ns ramp to 0.5
            sim.play('P2', constant_generator, 0.3, 25)  # 100ns at 0.3
            sim.wait(25, ['P1'])                         # 100ns hold at 0.5
            sim.align(['P1', 'P2'])                      # P2 pads to 200ns
            sim.play('P1', ramp_generator, -0.2, 10)    # 40ns ramp to -0.2
            sim.play('P2', constant_generator, 0.1, 10)  # 40ns at 0.1

        wf = sim.get_waveforms()
        assert len(wf['P1']) == 240
        assert len(wf['P2']) == 240
        # P1: 0→0.5 (100ns), hold 0.5 (100ns), ramp to -0.2 (40ns)
        assert wf['P1'][99] == pytest.approx(0.5)
        assert wf['P1'][150] == pytest.approx(0.5)
        assert wf['P1'][-1] == pytest.approx(-0.2)
        # P2: 0.3 (100ns), padded at 0.3 (100ns), 0.1 (40ns)
        assert wf['P2'][50] == pytest.approx(0.3)
        assert wf['P2'][150] == pytest.approx(0.3)
        assert wf['P2'][-1] == pytest.approx(0.1)
