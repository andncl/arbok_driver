"""Module containing various utils"""
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

def plotly_qmm_simulation_results(simulated_samples):
    """
    Plots one graph for each analog and digital simulation result per controller
    
    Args:
        simulated_results: simulated samples from qm simulator
        
    Returns:
        plotly figure
    """
    controller_dict = get_all_controller_results(simulated_samples)
    subplot_titles = []
    for index, _ in controller_dict.items():
        subplot_titles.append(f"Con{index}: analog")
        subplot_titles.append(f"Con{index}: digital")
    fig = make_subplots(
        rows=2*len(controller_dict),
        cols=1,
        subplot_titles=subplot_titles,
        vertical_spacing = 0.1,
    )
    plot_counter = 0
    for index, results in controller_dict.items():
        plot_counter +=1 
        for i in range(1, 11):
            row = (index-1)*2+1 
            if str(i) in results.analog:
                fig.add_trace(
                    go.Scatter(
                        x = list(range(len(results.analog[str(i)]))),
                        y = results.analog[str(i)],
                        mode='lines',
                        name = f'con{index} analog ch{i}',
                        #legendgroup= str(row),
                        visible = True
                        ),
                    row=(index-1)*2+1,
                    col=1
                    )
        fig.update_xaxes(title_text="time in ns", row=row, col=1)
        fig.update_yaxes(title_text="voltage in V", row=row, col=1)
        #fig.update_legends(yanchor = 'top', row = row, col = 1)
        for i in range(1, len(results.digital)):
            plot_counter +=1 
            row = index*2
            if str(i) in results.digital:
                fig.add_trace(
                    go.Scatter(
                        x = list(range(len(results.digital[str(i)]))),
                        y = np.array(results.digital[str(i)], dtype = int),
                        mode='lines',
                        name = f'con{index} digital ch{i}',
                        visible = True,
                        #legendgroup= str(row),
                        ),
                    row=index*2,
                    col=1,
                    )
        fig.update_xaxes(title_text="time in ns", row=row, col=1)
        fig.update_yaxes(title_text="voltage in V", row=row, col=1)

    fig.update_layout(
        autosize=False,
        width=800,
        height=plot_counter*400,
        margin=dict(l=50, r=50, t=50, b=50),
        title_text="Simulation results on all available quantum machines",
        legend_tracegroupgap = 100,
        #xaxis={"title":'X-axis Title'},
        #yaxis=dict(title='Y-axis Title')
    )
    fig.show()
    return fig

def get_all_controller_results(simulated_samples):
    all_controllers_found = False
    controller_nr = 1
    controller_dict = {}
    while not all_controllers_found:
        if hasattr(simulated_samples, f"con{controller_nr}"):
            controller = getattr(simulated_samples, f"con{controller_nr}")
            controller_dict[controller_nr] = controller
            controller_nr += 1
        else:
            all_controllers_found = True
    return controller_dict
