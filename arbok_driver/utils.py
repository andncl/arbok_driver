"""Module containing various utils"""
import matplotlib.pyplot as plt

def plot_qmm_simulation_results(simulated_samples):
    """ 
    Visualizes analog and digital channel simulation results 
    TODO: Check type of `simulated_samples`
    """
    fig, [a, b] = plt.subplots(2, sharex= True)
    for channel, data in simulated_samples.analog.items():
        a.plot(data, label = channel)
    for channel, data in simulated_samples.digital.items():
        b.plot(data, label = channel)

    ncols_a = int((len(a.lines)-1)/10) + 1
    a.legend(bbox_to_anchor=(1.0, 1.0), loc='upper left', fontsize = 8,
                title = 'analog', ncols = ncols_a)
    a.grid()
    a.set_ylabel("Voltage in V")
    a.set_title("simulated analog/digital outputs", loc = 'right')

    ncols_b = int((len(b.lines)-1)/10) + 1
    b.legend(bbox_to_anchor=(1.0, 1.0), loc='upper left', fontsize = 8,
                title = 'digital', ncols = ncols_b)
    b.grid()
    b.set_xlabel("Time in ns")
    b.set_ylabel("Digital Signal")
    fig.subplots_adjust(wspace=0, hspace=0)