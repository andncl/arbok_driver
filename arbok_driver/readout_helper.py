"""
General readout class to manage measurements

SSR
24/06/2022
"""

from qm.qua import *
import matplotlib.pyplot as plt
from arbok_driver.read_sequence import ReadSequence

class Readout():
    """
    Helper class to summarize and handlemultiple streaming results.
    TODO: Can probably be removed and be replaced by more specic helpers
        e.g: Set spin readout, set current read .. etc
    """
    def __init__(self, name: str, sequence: ReadSequence, read_label: str,
                 threshold: float = 0):
        """ 
        Constructor Method for readout helper class
        
        Args:
            name (str): Name of the Readout helper
            sequence (ReadSequence): ReadSequence that uses this helper
            read_label (str): name of the label
            threshold (float): Current threshold for spin state readout
        """
        self.name = name
        self.sequence =  sequence
        self.read_label = read_label
        self.threshold = threshold
        
        self.read_I = None
        self.read_Q = None
        self.read = None
        self.state = None

        self.read_I_stream = None
        self.read_Q_stream = None
        self.read_stream = None
        self.state_stream = None
        self.chopRef_stream = None
        self.stream_list = ['read_I', 'read_Q', 'read', 'chopRef', 'state']

    #def get(self):
    #    return self.program_handler.get_result(self.name)
    
    def init_qua_vars(self):
        self.read_I = declare(fixed)
        self.read_Q = declare(fixed)
        self.read = declare(fixed)
        self.state = declare(bool)
        self.chopN = declare(int)
        self.chopRef = declare(fixed)
        
        self.read_I_stream = declare_stream()
        self.read_Q_stream = declare_stream()
        self.read_stream = declare_stream()
        self.chopRef_stream = declare_stream()
        self.state_stream = declare_stream()

    def measure(self):
        measure('measure', self.read_label, None,
                demod.full('x',self.read_I),
                demod.full('y',self.read_Q))
        
    def save(self):
        assign(self.read, self.read_I + self.read_Q)   
        assign(self.state, self.read > self.threshold)
        
        assign(self.chopRef, self.read)
        
        save(self.read_I, self.read_I_stream)
        save(self.read_Q, self.read_Q_stream)
        save(self.read, self.read_stream)
        save(self.chopRef, self.chopRef_stream)
        save(self.state, self.state_stream)
    
    def measureAndSave(self):
        """ Performs a measurement and saves the streams """
        align()
        self.measure()
        self.save()
        align()
        
    def takeDiff(self, read, ref, thr = None):
        """This functions saves streams for a Readout object that is calculated
        without a measurement. e.g., the difference between 2 readouts. """
        
        assign(self.read_I, read.read_I - ref.read_I)
        assign(self.read_Q, read.read_Q - ref.read_Q)
        assign(self.read, read.read - ref.read)
        
        save(self.read_I, self.read_I_stream)
        save(self.read_Q, self.read_Q_stream)
        save(self.read, self.read_stream)
        
        assign(self.chopRef, self.read)
        save(self.chopRef, self.chopRef_stream)
        
        if(thr == None):
            thr = self.threshold
        
        self.aboveThreshold(thr)
    
    def aboveThreshold(self, thr):
        assign(self.state, self.read > thr)
        save(self.state, self.state_stream)
    
    def save_streams(self):
        sweep_size = self.sequence.root_instrument.sweep_size()

        self.read_I_stream.buffer(sweep_size).save(self.name+"_read_I_buffer")
        self.read_Q_stream.buffer(sweep_size).save(self.name+"_read_Q_buffer")
        self.read_stream.buffer(sweep_size).save(self.name+"_read_buffer")
        self.chopRef_stream.buffer(sweep_size).save(self.name+"_chopRef_buffer")
        self.state_stream.buffer(sweep_size).save(self.name+"_state_buffer")

        self.read_I_stream.save_all(self.name+"_read_I")
        self.read_Q_stream.save_all(self.name+"_read_Q")
        self.read_stream.save_all(self.name+"_read")
        self.chopRef_stream.save_all(self.name+"_chopRef")
        self.state_stream.save_all(self.name+"_state")
        
        #self.read_stream.timestamps().save_all(self.name+"TIMES")
    
    def fetch_streams(self, res):
        self.READ_I = res.get(self.name + '_read_I').fetch_all()['value']
        self.READ_Q = res.get(self.name + '_read_Q').fetch_all()['value']
        self.READ = res.get(self.name + '_read').fetch_all()['value']
        self.CHOP_REF = res.get(self.name + '_chopRef').fetch_all()['value']
        self.STATE = res.get(self.name + '_state').fetch_all()['value']
        
        TIMES_ns = res.get(self.name + '_TIMES').fetch_all()['value']
        self.TIMES = TIMES_ns * 1e-9
        
        
    def plot_histogram(self, title = 'Histogram', bins = 500, color = 'r'):
        data = self.READ
        plt.hist(data,bins=bins,alpha = 0.7)
        plt.xlabel(self.name + '_READ')
        plt.ylabel('Counts')
        plt.title(title)
        plt.axvline(x=self.threshold*(tReadInt_nominal/tReadInt),color=color)
        plt.show()