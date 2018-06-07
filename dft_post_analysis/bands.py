#!/usr/bin/env python

"""Plot bands.

Author: Johanness Voss mostly
"""

#| - IMPORT MODULES
import plotly.graph_objs as go
#__|

#| - Methods
def plot_band_series(
    x_data,
    y_data,
    showlegend=False,
    ):
    """Plot band data series.

    Args:
        x_data:
        y_data:
    """
    #| - plot_dos_series
    # trace = go.Scatter(
    trace = go.Scattergl(
        x=x_data,
        y=y_data,
        hoverinfo="none",
        showlegend=showlegend,
        name="Bands",
        legendgroup="bands_group",
        line=dict(
            color=('rgb(22, 96, 167)'),
            width=1,
            )
        )

    return(trace)
    #__|

#__|

def plot_bands(
    bands_data,
    plot_title="Projected Density of States",
    ):
    """Create bands plot data.

    Args:
        bands_data:
        plot_title:
    """
    #| - plot_bands

    #| - SCRIPT PARAMETERS
    # COMBAK
    emin = -20
    emax = 20
    plot_title = "Band diagram"
    #__|

    s, k, x, X, e = bands_data

    # symbols = [t.replace('Gamma', '$\Gamma$') for t in s]
    symbols = [t.replace("Gamma", "G") for t in s]

    #| - Checking if Atomic Projections Present
    # If atomic projections in "e" variable
    if isinstance(e, tuple) and len(e) == 2:
        # For the time being I'll just redefine e

        e = e[0]
    #__|

    #| - Checking for Spin Polarization
    # If spinpol = True, then e will have added dimension
    if e.shape[0] == 2:
        spinpol = True
    else:
        spinpol = False
    #__|

    data_list = []

    #| - Plotting Bands
    if spinpol is False:

        #| - Spinpol: False
        for n in range(len(e[0])):
            if n == 0:
                showleg = True
            else:
                showleg = False

            data_list.append(plot_band_series(x, e[:, n], showlegend=showleg))
        #__|

    elif spinpol is True:
        #| - Spinpol: True
        for n in range(len(e[0][0])):
            if n == 0:
                showleg = True
            else:
                showleg = False

            data_list.append(
                plot_band_series(x, e[0][:, n], showlegend=showleg),
                )

            data_list.append(
                plot_band_series(x, e[1][:, n], showlegend=showleg),
                )
        #__|

    #__|

    #| - Plot y=0 (Fermi Level)
    fermi_level = go.Scattergl(
        x=[X[0], X[-1]],
        y=[0, 0],
        mode="lines",
        hoverinfo="none",
        showlegend=False,
        line=dict(
            color=("black"),
            width=1,
            dash="dash",
            )
        )

    data_list.append(fermi_level)
    #__|

    #| - Plot Vertical Lines at Special K-Points
    for p in X:
        trace = go.Scattergl(
            x=[p, p],
            y=[emin, emax],
            hoverinfo="none",
            showlegend=False,
            mode="lines",
            line=dict(
                color=("red"),
                width=1,
                )
            )
        data_list.append(trace)
    #__|

    #| - Plotly

    #| - Plot Settings
    plot_title_size = 18
    tick_lab_size = 16
    axes_lab_size = 18
    legend_size = 18
    #__|

    #| - Plot Layout
    layout = {
        "title": plot_title,
        "showlegend": False,
        "font": {
            "family": "Courier New, monospace",
            "size": plot_title_size,
            "color": "black",
            },

        #| - Axes --------------------------------------------------------------
        "yaxis": {
            "title": "Energy [eV]",
            "range": [emin, emax],
            "zeroline": True,
            "titlefont": dict(size=axes_lab_size),
            "showgrid": False,
            "tickfont": dict(
                size=tick_lab_size,
                ),
            },

        "xaxis": {
            "range": [0, X[-1]],
            "zeroline": False,
            # "ticktext": s,
            "ticktext": symbols,
            # "ticktext": ['G', 'X', 'W', 'K', 'L', 'G'],
            # "tickvals": [1.5 * i + 0.5 for i in range(len(xax_labels))],
            "tickvals": X,
            "tickfont": dict(
                size=tick_lab_size,
                ),
            },


        #__| -------------------------------------------------------------------

        #| - Legend ------------------------------------------------------------
        "legend": {
            "traceorder": "normal",
            "font": dict(size=legend_size)
            },
        #__| -------------------------------------------------------------------

        #| - Plot Size
        "width": 200 * 4.,
        "height": 200 * 3.,
        #__|

        }
    #__|

    #__|

    return(data_list, layout)
    #__|
