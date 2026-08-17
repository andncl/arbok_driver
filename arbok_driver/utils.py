"""Module containing various utils"""
import logging
from importlib.util import spec_from_file_location, module_from_spec

from anytree import Node
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from qcodes.instrument import Instrument
from qcodes.station import Station

def plot_qmm_simulation_results(simulated_devices):
    """ 
    Visualizes analog and digital channel simulation results 
    TODO: Check type of `simulated_devices`
    """
    fig, [a, b] = plt.subplots(2, sharex= True)
    for channel, data in simulated_devices.analog.items():
        a.plot(data, label = channel)
    for channel, data in simulated_devices.digital.items():
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

def plotly_sim_results(simulated_devices):
    """
    Plots one graph for each analog and digital simulation result per controller
    
    Args:
        simulated_results: simulated devices from qm simulator
        
    Returns:
        plotly figure
    """
    controller_dict = get_all_controller_results(simulated_devices)
    fig = make_subplots(rows=1, cols=1)
    for index, results in controller_dict.items():
        for i in range(1, 11):
            if str(i) in results.analog:
                fig.add_trace(
                    go.Scatter(
                        x = list(range(len(results.analog[str(i)]))),
                        y = results.analog[str(i)],
                        mode='lines',
                        name = f'con{index} analog ch{i}',
                        opacity=0.8,
                        visible = True
                        ),
                    )
        for i in range(1, 11):
            if str(i) in results.digital:
                fig.add_trace(
                    go.Scatter(
                        x = list(range(len(results.digital[str(i)]))),
                        y = np.array(results.digital[str(i)], dtype = int),
                        mode='lines',
                        name = f'con{index} digital ch{i}',
                        opacity=0.8,
                        visible='legendonly',
                        ),
                    )
        fig.update_xaxes(title_text="time in ns", row=1, col=1)
        fig.update_yaxes(title_text="voltage in V", row=1, col=1)

    fig.update_layout(
        autosize=True,
        margin=dict(l=50, r=50, t=50, b=50),
        title_text="Simulation results on all available quantum machines",
        legend_tracegroupgap = 100,
    )
    return fig

def plotly_sim_results_separate(simulated_devices):
    """
    Plots one graph for each analog and digital simulation result per controller
    
    Args:
        simulated_results: simulated devices from qm simulator
        
    Returns:
        plotly figure
    """
    controller_dict = get_all_controller_results(simulated_devices)
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
                        opacity=0.8,
                        #legendgroup= str(row),
                        visible = True
                        ),
                    row=(index-1)*2+1,
                    col=1
                    )
        fig.update_xaxes(title_text="time in ns", row=row, col=1)
        fig.update_yaxes(title_text="voltage in V", row=row, col=1)
        for i in range(1, 11):
            if str(i) in results.digital:
                row = index*2
                plot_counter +=1
                fig.add_trace(
                    go.Scatter(
                        x = list(range(len(results.digital[str(i)]))),
                        y = np.array(results.digital[str(i)], dtype = int),
                        mode='lines',
                        name = f'con{index} digital ch{i}',
                        opacity=0.8,
                        visible=True,
                        #legendgroup= str(row),
                        ),
                    row=index*2,
                    #row=(index-1)*2+1,
                    col=1,
                    )
        fig.update_xaxes(title_text="time in ns", row=row, col=1)
        fig.update_yaxes(title_text="voltage in V", row=row, col=1)

    fig.update_layout(
        autosize=False,
        width=800,
        height=plot_counter*300,
        margin=dict(l=50, r=50, t=50, b=50),
        title_text="Simulation results on all available quantum machines",
        legend_tracegroupgap = 100,
    )
    return fig

def get_all_controller_results(simulated_devices: any) -> dict:
    """Takes simulated devices and returns a dict with all controller results"""
    controller_dict = {}

    for name, attr in simulated_devices.__dict__.items():
        if 'con' in name:
            controller_dict[name.split('con')[1]] = attr
    if len(controller_dict) == 0:
        raise ValueError("No controller results found!")
    return controller_dict

def set_qm_logging_to_file(filename):
    """Changes the standart logging handle (stdout) to the given file"""
    logger = logging.getLogger('qm')
    logger.setLevel('DEBUG')

    qm_log_file = open(filename, 'w')
    lh = logging.StreamHandler(qm_log_file)
    logger.addHandler(lh)
    for handler in logger.handlers:
        logger.removeHandler(handler)

def get_module(name: str = None, mod_path: str = None):
    """
    Dynamically loads a Python module from a specified file path.

    This function creates a module specification and loads the module from the
    provided file path.

    Args:
        name: The desired name for the loaded module.
        mod_path: The absolute path to the Python module file (.py).

    Returns:
        The loaded module object.

    Raises:
        ImportError: If the module specification cannot be created or if the
                     module cannot be loaded.
    """
    spec = spec_from_file_location(name, mod_path)
    if spec is None:
        raise ImportError(f"Cannot create module spec for {mod_path}.")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def get_element_port_mapping(opx_config: dict) -> dict:
    """
    Extracts a mapping from (controller, fem, port) to element name from the
    OPX configuration.

    Args:
        opx_config: The OPX configuration dictionary

    Returns:
        Dictionary mapping "fem-port" strings to element names, keyed by
        controller name. Structure:
        {controller: {"analog": {"fem-port": element_name, ...},
                      "digital": {"fem-port": element_name, ...}}}
    """
    mapping = {}
    elements = opx_config.get("elements", {})
    for element_name, element_cfg in elements.items():
        if "singleInput" in element_cfg:
            port_tuple = element_cfg["singleInput"]["port"]
            controller, fem, port = port_tuple
            mapping.setdefault(controller, {"analog": {}, "digital": {}})
            key = f"{fem}-{port}"
            mapping[controller]["analog"][key] = element_name

        if "mixInputs" in element_cfg:
            mix = element_cfg["mixInputs"]
            for channel in ("I", "Q"):
                if channel in mix:
                    controller, fem, port = mix[channel]
                    mapping.setdefault(controller, {"analog": {}, "digital": {}})
                    key = f"{fem}-{port}"
                    suffix = f"_{channel}" if key in mapping[controller]["analog"] else ""
                    mapping[controller]["analog"][key] = f"{element_name}{suffix}"

        if "MWInput" in element_cfg:
            mw = element_cfg["MWInput"]
            controller, fem, port = mw["port"]
            mapping.setdefault(controller, {"analog": {}, "digital": {}})
            key = f"{fem}-{port}"
            if key not in mapping[controller]["analog"]:
                mapping[controller]["analog"][key] = element_name

        if "digitalInputs" in element_cfg:
            for _, dig_cfg in element_cfg["digitalInputs"].items():
                controller, fem, port = dig_cfg["port"]
                mapping.setdefault(controller, {"analog": {}, "digital": {}})
                key = f"{fem}-{port}"
                mapping[controller]["digital"][key] = element_name

    return mapping


def plot_simulation(sim_results, opx_config: dict) -> go.Figure:
    """
    Creates an interactive plotly figure from simulation results, labeling
    traces with element names extracted from the OPX configuration.

    Args:
        sim_results: Simulated samples from sim_job.get_simulated_samples()
        opx_config: The OPX configuration dictionary used for the simulation

    Returns:
        Plotly Figure with all active analog and digital channels
    """
    port_mapping = get_element_port_mapping(opx_config)
    fig = go.Figure()

    for con_name, con_attr in sim_results.__dict__.items():
        if "con" not in con_name:
            continue
        con_mapping = port_mapping.get(con_name, {"analog": {}, "digital": {}})

        for channel_key, data in con_attr.analog.items():
            if not np.any(data):
                continue
            fs = con_attr.analog_sampling_rate.get(channel_key, 1e9)
            dt_ns = 1e9 / fs
            taxis = np.arange(len(data)) * dt_ns
            label = con_mapping["analog"].get(channel_key, f"{con_name}:{channel_key}")
            fig.add_trace(go.Scatter(
                x=taxis,
                y=data,
                mode="lines",
                name=label,
            ))

        for channel_key, data in con_attr.digital.items():
            if not np.any(data):
                continue
            taxis_dig = np.arange(len(data))
            label = con_mapping["digital"].get(
                channel_key, f"{con_name}:dig_{channel_key}")
            fig.add_trace(go.Scatter(
                x=taxis_dig,
                y=np.array(data, dtype=float) * 0.1,
                mode="lines",
                name=f"{label} (dig)",
                line=dict(dash="dot"),
            ))

    fig.update_layout(
        width=1500,
        height=500,
        xaxis=dict(
            title="Time (ns)",
            showgrid=True,
            gridcolor="lightgray",
        ),
        yaxis=dict(
            title="Voltage (V)",
            showgrid=True,
            gridcolor="lightgray",
        ),
        legend=dict(x=1.0, y=1.0),
        hovermode="x unified",
        template="plotly_dark",
    )
    return fig


def dict_to_anytree(name, d, parent=None):
    """Convert a nested dictionary to an anytree structure."""
    node = Node(name, parent=parent)
    for key, val in d.items():
        dict_to_anytree(key, val, parent=node)
    return node
