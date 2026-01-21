"""Module containing test for Experiment class"""
from arbok_driver import Measurement
from arbok_driver.examples.experiments import (
    SquarePulseExperiment,
    SquarePulseExperimentWithDefaults
)
from arbok_driver.examples.configurations import square_pulse_conf

def test_measurement_creation_from_experiment(arbok_driver, dummy_device):

    experiment = SquarePulseExperiment(dummy_device)
    measurement = arbok_driver.create_measurement_from_experiment(
        experiment, 'qc_measurement')
    assert isinstance(measurement, Measurement)
    assert len(measurement.sub_sequences) == 1

def test_measurement_creation_with_defaults(arbok_driver, dummy_device):
    """
    Tests whether a experiment configuration is loaded corretly from the measurement defaults
    """
    experiment_default = SquarePulseExperimentWithDefaults(dummy_device)
    print("experiments configs: ", experiment_default.configs)
    print("experiments layout: ", experiment_default.sequences_config)
    measurement_default = arbok_driver.create_measurement_from_experiment(
        experiment_default, 'qc_measurement')
    assert isinstance(measurement_default, Measurement)
    assert len(measurement_default.sub_sequences) == 1

def test_measurement_creation_overwrite(arbok_driver, dummy_device):
    experiment_overload = SquarePulseExperimentWithDefaults(
        dummy_device,
        square_pulse_config = {'config': square_pulse_conf})
    measurement_overload = arbok_driver.create_measurement_from_experiment(
        experiment_overload, 'qc_measurement')
    assert isinstance(measurement_overload, Measurement)
    assert len(measurement_overload.sub_sequences) == 1
