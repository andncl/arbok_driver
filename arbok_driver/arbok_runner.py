"""Module providing a non-recursive implementation of measurement loop functionality"""
import copy
import logging
import itertools

import numpy as np
from rich.progress import Progress

class ArbokRunner:
    """
    A non-recursive implementation of the measurement loop functionality for arbok_driver.
    Replaces the recursive approach in measurement_helpers.py with a clearer, iterative approach.
    """
    
    def __init__(self, sequence=None):
        """
        Initialize the ArbokRunner
        
        Args:
            sequence: Optional sequence to work with
        """
        self.sequence = sequence
    
    def run_measurement(self, sequence=None, qc_measurement=None, sweep_list=None, 
                      inner_function=None, register_all=False, **kwargs):
        """
        Run a measurement with an iterative approach instead of recursion
        
        Args:
            sequence: The measurement sequence (optional if already set in constructor)
            qc_measurement: QCoDeS measurement object to use
            sweep_list: List of sweep dictionaries for external instruments
            inner_function: Function to call at each measurement point
            register_all: Whether to register all parameters or just one per sweep
            **kwargs: Additional arguments passed to inner_function
            
        Returns:
            QCoDeS dataset from the measurement
        """
        # Set sequence if provided
        if sequence is not None:
            self.sequence = sequence
            
        # Validate inputs
        if self.sequence is None or qc_measurement is None:
            raise ValueError("Sequence and QCoDeS measurement must be provided")
        
        # Initialize sweep list if None
        if sweep_list is None:
            sweep_list = []
            
        # Calculate total points for progress tracking
        sweep_lengths = [len(next(iter(dic.values()))) for dic in sweep_list if dic]
        nr_sweep_list_points = np.prod(sweep_lengths) if sweep_lengths else 1
        
        # Register parameters
        result_args_dict = self._get_result_arguments(sweep_list, register_all)
        
        # Register settables in the measurement
        for param, _ in result_args_dict.items():
            logging.debug("Registering sequence parameter %s", param.full_name)
            qc_measurement.register_parameter(param)
        
        # Register gettables in the measurement
        for gettable in self.sequence.gettables:
            logging.debug("Registering gettable with setpoints %s", tuple(result_args_dict.keys()))
            qc_measurement.register_parameter(
                gettable, setpoints=tuple(result_args_dict.keys()))
                
        # Run the measurement
        with qc_measurement.run() as datasaver:
            # Set up progress tracking
            with Progress() as progress_tracker:
                progress_bars = {
                    'total_progress': progress_tracker.add_task(
                        "[green]Total progress...", total=nr_sweep_list_points),
                    'batch_progress': progress_tracker.add_task(
                        "[cyan]Batch progress...", total=self.sequence.sweep_size)
                }
                
                # Generate all parameter combinations
                param_combinations = self._generate_parameter_combinations(sweep_list)
                
                # Iterate through all parameter combinations
                for param_values in param_combinations:
                    # Set parameter values
                    for param, value in param_values.items():
                        logging.debug('Setting %s to %s', param.instrument.name, value)
                        param.set(value)
                        
                        # Update result arguments dictionary
                        if param in result_args_dict:
                            result_args_dict[param] = (param, value)
                    
                    # Call inner function if provided
                    if inner_function is not None:
                        inner_function(**kwargs)
                    
                    # Resume quantum job
                    self.sequence.driver.qm_job.resume()
                    
                    # Collect results from gettables
                    result_args = []
                    for gettable in self.sequence.gettables:
                        result_args.append(
                            (gettable, gettable.get_raw(
                                progress_bar=(
                                    progress_bars['batch_progress'], 
                                    progress_tracker
                                )
                            ))
                        )
                    
                    # Add parameter values to results
                    result_args.extend(list(result_args_dict.values()))
                    
                    # Save results
                    datasaver.add_result(*result_args)
                    
                    # Update progress
                    progress_tracker.update(
                        progress_bars['total_progress'], advance=1)
            
            print("Measurement finished!")
            return datasaver.dataset
    
    def _get_result_arguments(self, sweep_list, register_all=False):
        """
        Generate a dictionary of parameters to be registered in the measurement
        
        Args:
            sweep_list: List of sweep dictionaries
            register_all: Whether to register all parameters or just one per sweep
            
        Returns:
            Dictionary with parameters as keys and empty tuples as values
        """
        result_args_dict = {}
        for sweep_dict in sweep_list:
            for j, param in enumerate(list(sweep_dict.keys())):
                if j == 0 or register_all:
                    result_args_dict[param] = ()
                    
        return result_args_dict
    
    def _generate_parameter_combinations(self, sweep_list):
        """
        Generate all combinations of parameter values from the sweep list
        
        Args:
            sweep_list: List of sweep dictionaries
            
        Returns:
            List of dictionaries with parameter-value pairs for each measurement point
        """
        # Early return for empty sweep list
        if not sweep_list:
            return [{}]
        
        # Prepare dimension parameters and values
        dimensions = []
        for sweep_dict in sweep_list:
            if not sweep_dict:
                continue
                
            # Extract params and their values
            params = list(sweep_dict.keys())
            values = list(sweep_dict.values())
            
            # Check all value arrays have the same length
            if values:
                sweep_length = len(values[0])
                if not all(len(v) == sweep_length for v in values):
                    raise ValueError(
                        f"All parameter arrays must have the same length for sweep {sweep_dict}")
                
                # Add this dimension to our list
                dimensions.append((params, list(zip(*values))))
        
        # Early return if no dimensions found
        if not dimensions:
            return [{}]
            
        # Generate all combinations
        all_combinations = []
        
        # Start with an empty combination
        current_combinations = [{}]
        
        # For each dimension
        for params, value_tuples in dimensions:
            new_combinations = []
            
            # For each existing combination
            for combination in current_combinations:
                # For each value in this dimension
                for value_tuple in value_tuples:
                    new_combination = combination.copy()
                    # Set each parameter to its corresponding value
                    for param, value in zip(params, value_tuple):
                        new_combination[param] = value
                    new_combinations.append(new_combination)
            
            # Update current combinations
            current_combinations = new_combinations
            
        return current_combinations
