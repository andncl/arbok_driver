"""Module containing signal class"""
import logging

class Signal:
    """
    Class managing voltage signal from certain readout elements of OPX
    """
    def __init__(
        self,
        name: str,
        read_sequence: 'ReadSequence',
        ):
        """
        Constructor method of Signal class
        a
        Args:
            name (str): Name of the signal
            readout_points (dict): List of readout points
            readout_elements (dict): List of readout elements
        """
        self.name = name
        self.read_sequence = read_sequence

        self._observables = {}

    @property
    def observables(self):
        """Dictionary with all observables registered on the signal"""
        return self._observables

    def add_observable(self, observable: 'Observable') -> None:
        """
        Adds an observable to the signal

        Args:
            observable (Observable): Observable to be added
        """
        logging.debug(
            "Adding observable %s to signal %s", observable.name, self.name)
        if observable.name in self._observables:
            raise ValueError(
                f"Observable with name {observable.name} already exists in"
                f" signal '{self.name}'."
            )
        self._observables[observable.name] = observable
