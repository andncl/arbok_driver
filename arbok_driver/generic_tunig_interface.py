"""Module containing GenericTuningInterface class."""
from __future__ import annotations
from collections.abc import Callable
import copy
import random
import time
from typing import Protocol, TYPE_CHECKING

from scipy.stats import qmc
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np
from rich.progress import Progress
from rich import print
from IPython import display

if TYPE_CHECKING:
    from .arbok_driver import ArbokDriver
    from .measurement import Measurement
    from .parameters import SequenceParameter, GettableParameterBase

class CostFunction(Protocol):
    def __call__(
        self,
        results: dict[GettableParameterBase, np.ndarray]
    ) -> float:
        ...


class GenericTuningInterface:
    """
    Generic streaming interface for machine learning–based parameter tuning.

    This class coordinates measurement execution, parameter management,
    and cost evaluation via a pluggable ``CostStrategy``.

    Attributes:
        measurement (Measurement):
            Measurement object providing access to the experiment.
        driver (ArbokDriver):
            Driver associated with the measurement.
        parameter_dict (dict[str, dict]):
            Dictionary describing tunable parameters and their configurations.
        sweeps (list[dict[SequenceParameter, Sequence]]):
            List of sweep configurations defining remaining parameters are
            being varied
        gettables (dict[str, GettableParameterBase]): Gettables to be saved
        verbose (bool): Whether all optional printouts are shown
    """

    def __init__(
        self,
        measurement: Measurement,
        parameter_dicts: dict[str, dict],
        verbose: bool = False
    ) -> None:
        """
        Initialize the tuning interface.

        Args:
            measurement (Measurement):
                Measurement object that provides access to the experiment
                and its associated driver.
            parameter_dicts (dict[str, dict[SequenceParameter, float]]):
                Dictionary defining parameter groups and their bounds.
                Keys represent trivial parameter names or groups, and values
                map ``SequenceParameter`` objects to their bounds and factors.
            verbose (bool, optional):
                If ``True``, enables verbose logging during initialization and
                parameter setup. Defaults to ``False``.

        Raises:
            TypeError:
                If ``cost_strategy`` is not an instance of ``CostStrategy``.
        """
        self.measurement: Measurement = measurement
        self.driver: ArbokDriver = self.measurement.driver
        self._add_parameters(parameter_dicts, verbose=verbose)

        if not self.measurement.sweeps:
            raise ValueError(
                "No sweeps registered! Make sure to run measurement.set_sweeps(...)"
            )
        if not self.measurement.gettables:
            raise ValueError(
                "No gettables registered!"
                "Make sure to run measurement.register_gettables(...)"
            )
        self.gettables = self.measurement.gettables
        self.sweeps = self.measurement.sweeps

    def _add_parameters(self, parameter_dicts: dict, verbose: bool = False) -> None:
        """
        Adds parameters to be streamed to the QUA program.
        Parameters that depend on each other are added in the folowing way;
            'even_hotspot_detune': {
                interface.sequence.init_even.v_hotspot_P1: 1,
                interface.sequence.init_even.v_hotspot_P2: -1,
                },
        If added in this way, only the first parameter will be added to the 
        input stream, while all following once will use its qua variable as a
        reference with the respective factor.
        """
        self.parameter_dict = parameter_dicts
        self.input_stream_params = []
        self.bounds = {}
        for name, param_conf in parameter_dicts.items():
            for i, (parameter, factor) in enumerate(param_conf['qua_vars'].items()):
                if i == 0:
                    self.input_stream_params.append(parameter)
                    if verbose:
                        print(f"Adding input stream for {parameter.name} ({name})")
                else:
                    master_param = self.input_stream_params[-1]
                    def call(x = None, par = master_param, factor = factor):
                        if factor == 1:
                            return par(x)
                        else:
                            return par(x)*factor
                    parameter.call_method = call
                    if verbose:
                        print(
                            f"\tAdding {parameter.name} to {master_param.name}"
                            f"  input stream (factor: {factor}) ({name})")
            self.bounds[name] = param_conf['bounds']
        self.measurement.input_stream_parameters = self.input_stream_params

    def compile_connect_and_run(self, host_ip: str):
        """
        Compiles, connects and runs the parity readout sequences on device with
        given host ip.
        """
        if not self.driver.is_mock:
            self.driver.connect_opx(host_ip = host_ip)
            self.measurement.compile_qua_and_run()

    def run_parameter_set(
        self,
        input_param_dict: dict[SequenceParameter, float],
        progress_bar = None
        ) -> tuple[dict, dict]:
        """
        Runs the given parameter set an returns the current values for
        singlet and triplet init

        Args:
            input_param_dict (dict[SequenceParameter, float]): List of
                parameters to run
            progress_bar (Optional): Progress bar to update

        Returns:
            dict: All measured gettables for the parameter set
            dict: All parameters of the parameter set
        """
        if not isinstance(input_param_dict, dict):
            raise ValueError(
                "Input params must be a dict of SequenceParameters and float" 
                f" key value pairs. Are {type(input_param_dict)}")
        self.measurement.insert_single_value_input_streams(input_param_dict)
        if not self.driver.is_mock:
            self.driver.qm_job.resume()
        gettable_results = {}
        self.measurement.wait_until_result_buffer_full(
            progress_bar
            )
        results = self.measurement.fetch_all_results()
        for _, gettable in self.gettables.items():
            gettable_results[gettable] = results[gettable]
        saved_params = {}
        for param_name, value in zip(self.parameter_dict.keys(), input_param_dict.values()):
            saved_params[param_name] = value
        return gettable_results, saved_params

    def run_cross_entropy_sampler(
            self,
            populations: list,
            cost_strategy: CostFunction,
            select_frac: float = 0.3,
            plot_histograms: bool = False,
            sampling_params_to_plot: list | None = None
            ) -> xr.Dataset:
        """
        Runs the cross entropy method for the given populations.

        Args:
            populations (list[int]):
                List of population sizes for each iteration.

            cost_strategy (CostFunction):
                A callable that takes a dictionary mapping gettables to
                numpy arrays of measurement results and returns a scalar cost.

            select_frac (float):
                Fraction of best parameters to select for generating new bounds.

            plot_histograms (bool):
                If True, plot parameter distributions during sampling.

            sampling_params_to_plot (list[tuple[str, str]] | None):
                Parameter pairs to visualize during the sampling process.

        Returns:
            xr.Dataset: Dataset containing all gettables, parameters and
                rewards
        """
        all_rewards = []
        all_obs = {g: [] for g in self.gettables.values()}
        all_params = {param: [] for param in self.parameter_dict.keys()}
        all_bounds = {name: [] for name in self.bounds.keys()}
        current_bounds = copy.deepcopy(self.bounds)
        last_reward_threshold = None
        data_index = 0
        for population in populations:
            ### Sampling parameter sets and saving bounds
            print('Current bounds:\n', current_bounds)
            for param_name, bounds in current_bounds.items():
                all_bounds[param_name].append(bounds)
            sobol_samples = sobol_sampling(population, current_bounds)
            t0 = time.time()
            with Progress() as progress:
                task = progress.add_task(
                    "Sampling parameter sets", total=population)
                batch_task = progress.add_task(
                    "Sampling batch", total=self.measurement.sweep_size)
                total_nr = len(sobol_samples)
                ### Looping over all deviced parameter sets
                if plot_histograms:
                    fig, axs = plt.subplots(1, 2, figsize = (9,5))
                for i, x in enumerate(sobol_samples):
                    ### Running the parameter set
                    x = dict(zip(self.input_stream_params, x))
                    obs, par_dict = self.run_parameter_set(
                        x, progress_bar = (batch_task, progress))
                    r = cost_strategy(obs)
                    ### Saving the results
                    for param, value in par_dict.items():
                        all_params[param].append(value)
                    for gettable, value in obs.items():
                        all_obs[gettable].append(value)
                    all_rewards.append(r)
                    ### Updating the progress bar
                    progress.advance(task)
                    description = f"{i}/{total_nr} | "
                    description += f"Last SNR {np.max(r):.2f}, "
                    description += f"max: {np.max(all_rewards):.2f}"
                    progress.update(
                        task,
                        description = description
                        )
                    progress.refresh()
                    data_index += 1
                    if plot_histograms:
                        axs[0].cla()
                        axs[0].set_title('Best histogram ')
                        if len(all_rewards) == 0 or r > np.max(all_rewards):
                            for gettable, data in obs.items():
                                _ = axs[0].hist(data, label = gettable.name, alpha = 0.6)
                        axs[1].cla()
                        axs[1].set_title(f'Last histogram({i}/{total_nr})')
                        for gettable, data in obs.items():
                            _ = axs[1].hist(data, label = gettable.name, alpha = 0.6)

                        display.clear_output(wait=True)
                        display.display(plt.gcf())
                plt.close()
            print(f"Total time elapsed: {time.time()-t0:.0f}s")
            ### Updating the bounds for the next iteration
            dataset = self._merge_cem_data_into_xarray(
                all_rewards, all_obs, all_params)
            current_bounds = self._update_sobol_bounds(
                dataset, select_frac, population,
                last_reward_threshold,
                sampling_params_to_plot,
                )
        ### Compressing data into xarray dataset and adding metadata
        dataset = dataset.assign_attrs(populations = populations)
        dataset = dataset.assign_attrs(bounds = bounds)
        return dataset

    def _merge_cem_data_into_xarray(
            self,
            all_rewards: list,
            all_obs: dict[GettableParameterBase, np.ndarray],
            all_params: dict[str, float]
            ):
        """
        Merges the data into an xarray dataset.
        
        Args:
            all_rewards (list): List of rewards for the current iteration
            all_obs (dict): Dict of gettable names and values
            all_params (dict): Dict of par names and values for the last population

        Returns:
            xr.Dataset: Dataset containing all data and metadata
        """
        nr_indices = len(all_rewards)
        dataset = xr.Dataset()
        
        ### Saving rewards
        dataset['rewards'] = xr.DataArray(
            np.array(all_rewards),
            coords = {'index':np.arange(nr_indices)},
            dims = ('index')
            )
        dataset['rewards'] = dataset.rewards.assign_attrs(type = 'reward')
        ### Saving gettables
        for gettable, data in all_obs.items():
            data = np.array(data)
            name = gettable.register_name
            dataset[name] = xr.DataArray(
                data,
                coords = {
                    'index':np.arange(nr_indices),
                    'shot_nr': np.arange(np.shape(data)[1])
                    },
                dims = ('index', 'shot_nr')
                )
            dataset[name] = dataset[name].assign_attrs(type = 'gettable')
        ### Saving parameters
        for par_name, data in all_params.items():
            data = np.array(data)
            dataset[par_name] = xr.DataArray(
                data,
                coords = {'index': np.arange(nr_indices)},
                dims = ('index')
                )
            dataset[par_name] = dataset[par_name].assign_attrs(type = 'parameter')
        ### Adding metadata
        dataset = dataset.assign_attrs(parameters = list(all_params.keys()))
        # dataset = dataset.assign_attrs(gettables = list(all_obs.keys()))
        return dataset

    def _update_sobol_bounds(
            self, dataset, select_frac, population,
            last_reward_threshold: float,
            sampling_params_to_plot: list = None,):
        """
        Updates the bounds for the Sobol devicer.
        
        Args:
            rewards (list): List of rewards for the current iteration
            params (dict): Dict of par names and values for the last population
        """
        dataset = dataset.sel(index = dataset.index[-population:])
        nr_devices = int(np.ceil(select_frac*population))
        sorted_dataset = dataset.sortby(dataset.rewards)
        best_indices = sorted_dataset.index[-nr_devices:]

        new_bounds = {}
        for par_name in dataset.parameters:
            best_params = dataset[par_name].sel(index = best_indices)
            param_mean = float(best_params.mean().to_numpy())
            param_std = float(best_params.std().to_numpy())
            new_bounds[par_name] = (param_mean - param_std*1.5, param_mean + param_std*1.5)

        if sampling_params_to_plot is not None:
            nr_plots = len(sampling_params_to_plot)
            fig, axs = plt.subplots(1, nr_plots, figsize=(nr_plots*4, 5))
            if not isinstance(axs, list):
                axs = [axs]
            for i, (par1_name, par2_name) in enumerate(sampling_params_to_plot):
                param_bounds1 = new_bounds[par1_name]
                param_bounds2 = new_bounds[par2_name]
                axs[i].scatter(
                    dataset[par1_name].to_numpy(),
                    dataset[par2_name].to_numpy(),
                    color = 'blue', label = 'new bounds'
                    )
                axs[i].scatter(
                    dataset[par1_name].sel(index = best_indices).to_numpy(),
                    dataset[par2_name].sel(index = best_indices).to_numpy(),
                    color = 'red',
                    )
                axs[i].plot(
                    [param_bounds1[0], param_bounds1[1], param_bounds1[1], param_bounds1[0], param_bounds1[0]],
                    [param_bounds2[0], param_bounds2[0], param_bounds2[1], param_bounds2[1], param_bounds2[0]],
                    '-k')
                axs[i].set_xlabel(par1_name)
                axs[i].set_ylabel(par2_name)
            fig.tight_layout()
            plt.show()
        return new_bounds#, reward_threshold

    def _merge_data_into_xarray(self, index, all_rewards, all_obs, all_params):
        """Merges the data into an xarray dataset."""
        nr_indices = len(all_rewards)
        dataset = xr.Dataset()
        dataset['rewards'] = xr.DataArray(
            all_rewards,
            coords = {'index':np.arange(nr_indices)},
            dims = ('index')
            )
        dataset['params'] = xr.DataArray(
            np.array(all_params),
            coords = {'index':np.arange(nr_indices)},
            dims = ('index')
            )
        dataset['obs'] = xr.DataArray(
            np.array(all_obs),
            coords = {'index':np.arange(nr_indices),
                      'shot_nr': np.arange(self.measurement.sweep_size)},
            dims = ('index', 'shot_nr')
            )
        return dataset

def sobol_sampling(num_samples: int, bound_dict: dict) -> np.ndarray:
    """
    Generate Sobol sequence devices for the given parameters.
    
    Args:
        num_samples (int): Number of devices to generate.
        parameter_dict (dict): Dictionary containing the parameters to device.
            Must have bounds as a key for each parameter.
        
    Returns:
        dict: Dictionary containing the parameters as keys and the devices as values.
    """
    # Generate Sobol sequence devices and truncate devices to the desired number
    sobol_engine = qmc.Sobol(d=len(bound_dict), scramble=True)
    sobol_samples = sobol_engine.random_base2(m=int(np.ceil(np.log2(num_samples))))
    sobol_samples = np.array(random.sample(sobol_samples.tolist(), num_samples))

    # Scale devices to the desired domain
    for i, (_, config) in enumerate(bound_dict.items()):
        l_bound = config[0]
        u_bound = config[1]
        sobol_samples[:,i] = l_bound + (u_bound - l_bound) * sobol_samples[:,i]
    return sobol_samples
