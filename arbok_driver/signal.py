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
            read_sequence (arbok_driver.ReadSequence): ReadSequence performing the
                abstract readout
        """
        self.name = name
        self.read_sequence = read_sequence

        self._gettables = {}

    @property
    def gettables(self):
        """Dictionary with all gettables registered on the signal"""
        return self._gettables

    def add_gettable(self, gettable: 'GettableParameter') -> None:
        """
        Adds a gettable parameter to the signal

        Args:
            gettable (GettableParameter): Gettable parameter to be added
        """
        logging.debug(
            "Adding gettable %s to signal %s", gettable.name, self.name)
        if gettable.name in self._gettables:
            raise ValueError(
                f"gettable with name {gettable.name} already exists in"
                f" signal '{self.name}'."
            )
        self._gettables[gettable.name] = gettable
        if hasattr(self, gettable.name):
            raise ValueError(
                f"Attribute with name {gettable.name} already exists on"
                f" signal '{self.name}'. Choose a different name for the gettable."
            )
        setattr(self, gettable.name, gettable)
