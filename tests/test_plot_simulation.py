"""Tests for the simulation plotting helpers in arbok_driver.utils"""
import numpy as np
import pytest

from arbok_driver import utils


class FakeController:
    """Minimal stand-in for a simulated controller result"""
    def __init__(self, analog, digital=None, analog_sampling_rate=None):
        self.analog = analog
        self.digital = digital or {}
        self.analog_sampling_rate = analog_sampling_rate or {}


class FakeSimResults:
    """Minimal stand-in for sim_job.get_simulated_samples()"""
    def __init__(self, **controllers):
        self.__dict__.update(controllers)


OPX_CONFIG = {
    'elements': {
        'P1': {'singleInput': {'port': ('con1', 1, 1)}},
        'mw_element': {'MWInput': {'port': ('con1', 2, 1)}},
    }
}


@pytest.fixture(name='real_samples')
def fixture_real_samples():
    return np.linspace(0, 0.5, 100)


@pytest.fixture(name='complex_samples')
def fixture_complex_samples():
    return np.linspace(0, 0.5, 100) + 1j*np.linspace(0.5, 0, 100)


def test_plot_simulation_real_channel(real_samples):
    sim_results = FakeSimResults(
        con1=FakeController(analog={'1-1': real_samples}))
    fig = utils.plot_simulation(sim_results, OPX_CONFIG)

    assert len(fig.data) == 1
    assert fig.data[0].name == 'P1'
    np.testing.assert_allclose(fig.data[0].y, real_samples)


def test_plot_simulation_complex_channel_splits_into_i_and_q(complex_samples):
    sim_results = FakeSimResults(
        con1=FakeController(analog={'2-1': complex_samples}))
    fig = utils.plot_simulation(sim_results, OPX_CONFIG)

    assert len(fig.data) == 2
    assert [trace.name for trace in fig.data] == [
        'mw_element (I)', 'mw_element (Q)']
    np.testing.assert_allclose(fig.data[0].y, complex_samples.real)
    np.testing.assert_allclose(fig.data[1].y, complex_samples.imag)
    for trace in fig.data:
        assert not np.iscomplexobj(np.asarray(trace.y))


def test_plot_simulation_mixed_real_and_complex(real_samples, complex_samples):
    sim_results = FakeSimResults(
        con1=FakeController(
            analog={'1-1': real_samples, '2-1': complex_samples},
            digital={'1-1': np.ones(100, dtype=bool)},
        )
    )
    fig = utils.plot_simulation(sim_results, OPX_CONFIG)

    assert [trace.name for trace in fig.data] == [
        'P1', 'mw_element (I)', 'mw_element (Q)', 'con1:dig_1-1 (dig)']


def test_plot_simulation_skips_empty_complex_channel(complex_samples):
    sim_results = FakeSimResults(
        con1=FakeController(analog={'2-1': np.zeros_like(complex_samples)}))
    fig = utils.plot_simulation(sim_results, OPX_CONFIG)

    assert len(fig.data) == 0


def test_plot_simulation_complex_channel_respects_sampling_rate(complex_samples):
    sim_results = FakeSimResults(
        con1=FakeController(
            analog={'2-1': complex_samples},
            analog_sampling_rate={'2-1': 2e9},
        )
    )
    fig = utils.plot_simulation(sim_results, OPX_CONFIG)

    for trace in fig.data:
        np.testing.assert_allclose(trace.x, np.arange(len(complex_samples))*0.5)
