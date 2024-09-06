"""Module defining a qua to python callback"""

from qm import qua

class QuaCallback:
    """
    Defines methods required for executing a callback on qua pausing
    """

    _id = None
    _pause_id_qua_stream = None
    _pause_id_qua_var = None

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if value != int(value):
            raise TypeError("id must be an integer")
        self._id = int(value)

    @property
    def pause_id_qua_stream(self):
        return self._pause_id_qua_stream

    @pause_id_qua_stream.setter
    def pause_id_qua_stream(self, value):
        self._pause_id_qua_stream = value

    @property
    def pause_id_qua_var(self):
        return self._pause_id_qua_var

    @pause_id_qua_var.setter
    def pause_id_qua_var(self, value):
        self._pause_id_qua_var = value

    def process(self, id):
        """
        overload this method with your callback
        """
        if _id != id:
            raise ValueError(f"id mismatch, expecting {_id} but received {id}")

    def qua_set_id_and_pause(self):
        """
        Set the qua pause id and then pause
        """
        qua.assign(self.pause_id_qua_var, self.id)
        qua.save(self.pause_id_qua_var, self.pause_id_qua_stream)
        qua.pause()
        qua.assign(self.pause_id_qua_var, -1)
