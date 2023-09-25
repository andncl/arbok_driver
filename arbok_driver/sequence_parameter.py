""" Module containing SequenceParameter class """

from qcodes.parameters import Parameter

class SequenceParameter(Parameter):
    """
    A parameter wrapper that adds the respective element as attribute

    TODO: Write get_raw abstract method without crashing sequence compilation
    """
    def __init__(self, element, config_name, *args, **kwargs):
        """
        Constructor for 'SequenceParameter' class

        Args:
            elements (list): Elements that should be influenced by parameter
            batched (bool): Is the variab
        """
        super().__init__(*args, **kwargs)
        self.element = element
        self.config_name = config_name
        self.qua_sweeped = False
        self.qua_sweep_arr = None
        self.qua_var = None
        self.value = None

    def __call__(self, *args, **kwargs):
        if len(args) == 1:
            self.set_raw(*args)
        elif self.qua_sweeped:
            return self.qua_var
        else:
            return self.get()

    def set_raw(self, value):
        self.value = value

    def set_on_program(self, *args):
        """ Adds parameter as settable on OPX program """
        self.root_instrument.settables.append(*args[0])
