#!/usr/bin/env python

"""ORR energetics classes and methods.

Author: Raul A. Flores
"""

#| - IMPORT MODULES
import copy
import numpy as np
import pandas as pd

from plotly.graph_objs import Scatter

pd.options.mode.chained_assignment = None
#__|

class ORR_Free_E_Plot:
    """ORR free energy diagram class.

    Development Notes:
        # TODO Should we consider the case where the bulk energy is not 0, and
        we have to normalize all of the species energies by it?
    """

    #| - ORR_Free_E_Plot *******************************************************

    def __init__(self,
        free_energy_df=None,
        system_properties=None,
        state_title="adsorbate",
        free_e_title="ads_e"
        ):
        """
        Input variables to class instance.

        Args:
            free_energy_df:
                Pandas dataframe containing the adsorbates as rows
                Required columns, adsorbate, free energy
            system_properties:
            state_title:
            free_e_title:
        """
        #| - __init__

        #| - Setting Instance Attributes
        self.fe_df = free_energy_df
        self.sys_props = system_properties
        self.state_title = state_title
        self.fe_title = free_e_title

        self.rxn_mech_states = ["bulk", "ooh", "o", "oh", "bulk"]
        self.ideal_energy = [4.92, 3.69, 2.46, 1.23, 0]
        #__|

        if free_energy_df is not None:
            self.add_bulk_entry()
            self.fill_missing_data()

            self.num_of_states = len(self.fe_df) + 1  # bulk, OOH, O, OH, bulk
            self.energy_lst = self.rxn_energy_lst()
            self.num_of_elec = range(self.num_of_states)[::-1]
            self.overpotential = self.calc_overpotential()[0]
            self.limiting_step = self.calc_overpotential()[1]
            # self.ideal_energy = [4.92, 3.69, 2.46, 1.23, 0]
            self.energy_lst_h2o2 = self.rxn_energy_lst_h2o2()
            self.overpotential_h2o2 = self.calc_overpotential_h2o2()
        #__|

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    #| - ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    def add_bulk_entry(self,
        bulk_e=0.0,
        ):
        """
        Append a row entry to data frame corresponding to bulk state.

        Args:
            bulk_e:
        """
        #| - add_bulk_entry
        df = self.fe_df
        bulk_df = pd.DataFrame([{
            "adsorbate": "bulk",
            "ads_e": bulk_e,
            }])

        df = df.append(bulk_df, ignore_index=True)

        self.fe_df = df
        #__|

    def rxn_energy_lst_h2o2(self):
        """Construct energy list of h2o2 FED."""
        #| - rxn_energy_lst_h2o2
        # h2o2_e = 3.52

        df = self.fe_df

        free_energy_list = []
        for index, row in df.iterrows():
            if row["adsorbate"] == "bulk" or row["adsorbate"] == "ooh":
                free_energy_list.append(row["ads_e"])

        # Checking length of energy list
        if len(free_energy_list) != 2:
            raise ValueError("Not the correct # of steps for H2O2")

        free_energy_list[0] += 4.92
        free_energy_list.append(3.52)

        return(free_energy_list)
        #__|

    def property_list(self, column_name):
        """General method to create a list from a column in the dataframe.

        The length of the list will correspond to the steps in the ORR
        mechanism.

        Args:
            column_name:
        """
        #| - property_list
        df = self.fe_df

        property_list = []
        for state in self.rxn_mech_states:
            tmp = df.loc[df[self.state_title] == state]
            tmp1 = tmp.iloc[0][column_name]
            property_list.append(tmp1)

        # free_energy_list[0] += 4.92

        return(property_list)
        #__|

    def fill_missing_data(self):
        """
        """
        #| - fill_missing_data
        df = self.fe_df
        df_missing_data = pd.DataFrame()
        for state in self.rxn_mech_states:
            df_state = df.loc[df[self.state_title] == state]

            #| - If df is missing state fill in row with NaN for energy
            if df_state.empty:
                df_state = pd.DataFrame([{
                    self.state_title: state,
                    self.fe_title: np.nan,
                    }])
                df_missing_data = df_missing_data.append(df_state)
            #__|

        self.fe_df = self.fe_df.append(df_missing_data)
        #__|

    def rxn_energy_lst(self):
        """List corresponding to the steps of ORR.

        (1. O2, 2. *OOH, 3. *O, 4. *OH, 5. 2H2O)
        """
        #| - rxn_energy_lst
        df = self.fe_df
        free_energy_list = []
        for state in self.rxn_mech_states:

            df_state = df.loc[df[self.state_title] == state]

            #| - If df is missing state fill in row with NaN for energy
            if df_state.empty:
                df_state = pd.DataFrame([{
                    self.state_title: state,
                    self.fe_title: np.nan,
                    }])
            #__|

            tmp1 = df_state.iloc[0][self.fe_title]
            free_energy_list.append(tmp1)

        free_energy_list[0] += 4.92

        return(free_energy_list)
        #__|

    def apply_bias(self, bias, energy_list):
        """Apply bias to free energies.

        Applies a potential to every species in the 4 and 2-electron process
        and adjusts their free energies accordingly
        """
        #| - apply_bias
        mod_free_e_lst = []        # Free energy reaction path at applied bias
        for energy, elec in zip(energy_list, range(len(energy_list))[::-1]):
            mod_free_e_lst.append(energy - elec * bias)

        return(mod_free_e_lst)
        #__|

    def calc_overpotential(self):
        """
        Calculate overpotential for 4e- process.

        Returns the limiting overpotential for the given species and the
        limiting reaction step in the form of a list, species_A -> species_B is
        [species_A, species_B]
        """
        #| - calc_overpotential
        rxn_spec = self.rxn_mech_states

        overpotential_lst = []
        for energy_i in enumerate(self.energy_lst[:-1]):
            energy_i_plus1 = self.energy_lst[energy_i[0] + 1]
            overpotential_i = 1.23 + energy_i_plus1 - energy_i[1]
            overpotential_lst.append(overpotential_i)

        overpotential = max(overpotential_lst)
        lim_step_index = overpotential_lst.index(overpotential)

        limiting_step = [rxn_spec[lim_step_index], rxn_spec[lim_step_index + 1]]
        out_list = [overpotential, limiting_step]

        return(out_list)
        #__|

    def calc_overpotential_h2o2(self):
        """
        Calculate overpotential for 2e- process.

        The overpotential for the 2e- process depends only on the energy of the
        *OOH intermediate
        """
        #| - calc_overpotential_h2o2
        df = self.fe_df
        ooh_row = df[df["adsorbate"] == "ooh"]
        ooh_ads_e = ooh_row.iloc[0]["ads_e"]

        op_4e = ooh_ads_e - 4.22

        return(op_4e)
        #__|

    def create_rxn_coord_array(self,
        rxn_steps,
        spacing=0,
        step_size=1,
        ):
        """
        Create a reaction coordinate array ([0, 1, 1, 2, 2, 3]) for plotting.

        Args:
            rxn_steps: <type 'int'>
                Number of steps in reaction coordinate including initial
                and final state.
                Ex. A -> Intermediate -> C has 3 steps/states

            spacing: <type 'float'>
                Spacing inbetween the energy levels. The default of 0 creates
                a free energy diagram that looks like steps
        """
        #| - create_rxn_coord_array
        lst = []
        for i in range(1, rxn_steps):
            if i == 1:
                lst.append(step_size)
                lst.append(step_size + spacing)
            if i != 1:
                lst.append(lst[-1] + step_size)
                lst.append(lst[-2] + step_size + spacing)

        lst.insert(0, 0)
        lst.append(lst[-1] + step_size)

        return(lst)
        #__|

    #__| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    #| - Plotting @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    def convert_to_plotting_list(self,
        energy_lst,
        spacing=0.5,
        step_size=1,
        ):
        """
        Repeat entries in energy list to conform to FED plot.

        Modifies an energy list for plotting by repeating each entry
        Ex. [4.92, 3.69, ... ] -> [4.92, 4.92, 3.69, 3.69, ... ]

        Args:
            energy_lst: <type 'list'>
            spacing:
            step_size:
        """
        #| - convert_to_plotting_list
        tmp_list = range(len(energy_lst) * 2)
        energy_dupl_lst = [energy_lst[i // 2] for i in tmp_list]

        rxn_coord_steps = self.create_rxn_coord_array(
            len(energy_lst),
            spacing=spacing,
            step_size=step_size,
            )
        out_list = [rxn_coord_steps, energy_dupl_lst]

        return(out_list)
        #__|

    def plot_fed_series(self,
        bias=0.,
        opt_name=None,
        properties=None,
        color_list=None,
        i_cnt=0,
        hover_text_col=None,
        plot_mode="all",
        smart_format=None,
        ):
        """
        Process data for FED plot.

        Args:
            bias:
            opt_name
            properties:
            color_list:
            i_cnt:
            hover_text_col:
                Dataframe column name to be used for hover text

        #FIXME | This is  fairly rough as of right now
        """
        #| - plot_fed_series
        key = properties
        if type(key) == tuple:
            pass

        elif key is None:
            key = None
        else:
            key = (key,)

        e_list = self.energy_lst
        e_list = self.apply_bias(bias, e_list)

        overpot_i = self.overpotential

        for n, i in enumerate(e_list):
            if np.isnan(i) is True:
                e_list[n] = None

        if color_list is None:
            color_list = ["red"]


        if key is None:
            prop_name = ""
        else:
            prop_name = "_".join([str(i) for i in key])

        if opt_name is not None:
            name_i = opt_name + ": " + prop_name + \
                " (OP: " + str(round(overpot_i, 2)) + ")"

        else:
            name_i = prop_name + \
                " (OP: " + str(round(overpot_i, 2)) + ")"

        #| - Hover Text
        if hover_text_col is not None:

            if type(hover_text_col) is not list:
                hover_text_list = self.property_list(hover_text_col)

            else:

                hover_text_lists = []
                for col_i in hover_text_col:

                    # replacing nan with ""
                    tmp = self.property_list(col_i)
                    hover_text_i = ["" if x is np.nan else x for x in tmp]
                    hover_text_lists.append(hover_text_i)

                # TODO Removed last trailing " | "
                hover_text_list = []
                for items in zip(*hover_text_lists):

                    if all([True if i == "" else False for i in items]) is True:
                        hover_col_state_i = ""
                    else:
                        hover_col_state_i = " | ".join(items)

                    hover_text_list.append(hover_col_state_i)

        else:
            hover_text_list = [np.nan for j_cnt in list(range(5))]
        #__|

        dat_lst = self.create_plotly_series(
            e_list,
            group=name_i,
            name=name_i,
            hover_text=hover_text_list,
            color=color_list[i_cnt - 1],
            plot_mode=plot_mode,
            smart_format=smart_format,
            )

        return(dat_lst)
        #__|

    def create_plotly_series(self,
        energy_lst,
        name="TEMP",
        group="group1",
        hover_text=None,
        color="rgb(22, 96, 167)",
        plot_mode="all",
        smart_format=None,
        ):
        """
        Create a plotly series for the current instance.

        Args:
            energy_lst:
            name:
            group:
            color:
            plot_mode:
                "all"
                "states_only"
                "full_lines"
        """
        #| - create_plotly_series
        e_list = self.convert_to_plotting_list(energy_lst)
        x_dat = e_list[0]
        y_dat = e_list[1]

        if hover_text is None:
            hover_text = [np.nan for i_ind in range(5)]

        #| - Parameters
        if plot_mode == "all":
            show_leg_2 = False
        elif plot_mode == "states_only":
            show_leg_2 = False
        elif plot_mode == "full_lines":
            show_leg_2 = True
        #__|

        #| - Adding Breaks in Data
        new_x_dat = copy.copy(x_dat)
        new_y_dat = copy.copy(y_dat)

        cnt = 2
        for i_ind in range(int(len(x_dat) / 2 - 1)):
            fill = new_x_dat[cnt - 1]
            new_x_dat.insert(cnt, fill)
            new_y_dat.insert(cnt, None)
            cnt += 3
        #__|

        #| - Creating x-data in middle of states
        short_y = np.array(y_dat)[::2]

        xdat = list(set(new_x_dat))
        xdat.sort()

        cnt = 0
        short_x = []
        for i_ind in range(int(len(xdat) / 2)):
            short_x.append(xdat[cnt] + 0.5)  # FIXME Replace 0.5 with variable
            cnt += 2
        #__|


        #| - Smart Format Dict ************************************************

        #| - DICTS
        plot_parameter_dict = {
            "dash": None,
            }

        # smart_format = [
        #
        #     # [
        #     #     {"spinpol": True},
        #     #     {"dash": "dot"},
        #     #     ],
        #
        #     [
        #         {"system": "Fe_slab"},
        #         {"dash": "dashdot"},
        #         ],
        #
        #     [
        #         {"system": "N_graph_Fe"},
        #         {"dash": "dot"},
        #         ],
        #
        #     [
        #         {"system": "graph_Fe"},
        #         {"dash": "dash"},
        #         ],
        #
        #     [
        #         {"system": "graphene"},
        #         {"dash": None},
        #         ],
        #
        #     ]

        #__|

        if self.fe_df is not None and smart_format is not None:
            for format_i in smart_format:

                # format_i key:values
                df_col_name = list(format_i[0])[0]
                value_i = list(format_i[0].values())[0]
                setting_name = list(format_i[1])[0]
                setting_value = list(format_i[1].values())[0]


                if df_col_name in list(self.fe_df):

                    # *OOH, *O, *OH entries must have value_i as the
                    # column entries in the column df_col_name

                    df = self.fe_df
                    df_wo_bulk = df[df["adsorbate"] != "bulk"]

                    if all(df_wo_bulk[df_col_name] == value_i):
                        plot_parameter_dict.update({setting_name: setting_value})

                else:
                    print("Dataframe column " + df_col_name + " not present")

        #__| ******************************************************************

        #| - Series Color
        if "color" in list(plot_parameter_dict):
            color_out = plot_parameter_dict["color"]
        else:
            plot_parameter_dict["color"] = color
        #__|

        #| - Plotly Scatter Plot Instances

        #| - Thick horizontal state lines
        data_1 = Scatter(
            x=new_x_dat,
            y=new_y_dat,
            legendgroup=group,
            showlegend=True,
            name=name,
            hoverinfo="none",  # TEMP - 180317
            # text=hover_text,

            connectgaps=False,
            line=dict(
                # color=color,
                color=plot_parameter_dict["color"],
                width=6,
                # dash="dot",  # TEMP
                dash=plot_parameter_dict["dash"],  # TEMP
                ),
            mode="lines",
            )
        #__|

        #| - Full, thin line
        data_2 = Scatter(
            x=new_x_dat,
            y=new_y_dat,
            legendgroup=group,
            name=name,
            connectgaps=True,
            showlegend=show_leg_2,
            hoverinfo="none",
            text=hover_text,

            line=dict(
                # color=color,
                color=plot_parameter_dict["color"],
                width=1,
                ),
            mode="lines",
            )
        #__|

        #| - Points in middle of energy states
        data_3 = Scatter(
            x=short_x,
            y=short_y,
            legendgroup=group,
            name=name,
            showlegend=False,
            hoverinfo="y+text",
            text=hover_text,
            marker=dict(
                size=14,
                color=color,
                opacity=0.,
                ),
            mode="markers",
            )
        #__|

        #__|

        #| - Plot Mode (which data series to plot)
        if plot_mode == "all":
            data_lst = [data_1, data_2, data_3]
        elif plot_mode == "states_only":
            data_lst = [data_1, data_3]
        elif plot_mode == "full_lines":
            data_lst = [data_2, data_3]
        #__|

        return(data_lst)
        #__|


    #__| @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    #__| **********************************************************************


#| - MISC Methods

def plotly_fed_layout(
    plot_title="FED",
    plot_title_size=18,
    tick_lab_size=16,
    axes_lab_size=18,
    legend_size=18,
    ):
    """
    """
    #| - plotly_fed_layout

    xax_labels = ["O2", "OOH", "O", "OH", "H2O"]
    layout = {

        "title": plot_title,

        "font": {
            "family": "Courier New, monospace",
            "size": plot_title_size,
            "color": "black",
            },

        #| - Axes --------------------------------------------------------------
        "yaxis": {
            "title": "Free Energy [eV]",
            "zeroline": True,
            "titlefont": dict(size=axes_lab_size),
            "showgrid": False,
            "tickfont": dict(
                size=tick_lab_size,
                ),
            },

        "xaxis": {
            "title": "Reaction Coordinate",
            "zeroline": True,
            "titlefont": dict(size=axes_lab_size),
            "showgrid": False,

            # "showticklabels": False,

            "ticktext": xax_labels,
            "tickvals": [1.5 * i + 0.5 for i in range(len(xax_labels))],

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
        # "width": 200 * 4.,
        # "height": 200 * 3.,
        #__|

        }

    return(layout)

    #__|

def calc_ads_e(
    df_row,
    bare_raw_e,
    correction=0.,
    oxy_ref_e=-443.70964,
    hyd_ref_e=-16.46018,
    ):
    """Calculate adsorption energies from raw DFT energetics.

    Default oxygen reference energy is based on water

    Args:
        df_row: Pandas dataframe row
        bare_raw_e: Bare slab raw DFT energy
        correction: Energy correction (ZPE, entropy, solvation, etc.)
        oxy_ref_e:
        hyd_ref_e:
    """
    #| - calc_ads_e
    row = df_row
    bare_slab = bare_raw_e
    oxy_ref = oxy_ref_e
    hyd_ref = hyd_ref_e

    #| - Oxygen & Hydrogen Atom Count

    atoms_col = "atom_type_num_dict"
    if atoms_col in list(row):
        try:
            num_O = row[atoms_col][0]["O"]
        except:
            num_O = 0

        try:
            num_H = row[atoms_col][0]["H"]
        except:
            num_H = 0

    else:

        if row["adsorbate"] == "ooh":
            num_O = 2
            num_H = 1
        elif row["adsorbate"] == "o":
            num_O = 1
            num_H = 0
        elif row["adsorbate"] == "oh":
            num_O = 1
            num_H = 1

    #__|

    try:
        raw_e = row["elec_energy"]
        ads_e_i = raw_e - (bare_slab + num_O * oxy_ref + num_H * hyd_ref)
        ads_e_i += correction

        # ads_e_i = raw_e - bare_slab - num_O * oxy_ref - num_H * hyd_ref
        # ads_e_i += correction
    except:
        ads_e_i = None

    return(ads_e_i)
    #__|

def df_calc_adsorption_e(
    df,

    oxy_ref,
    hyd_ref,

    bare_slab_e,
    bare_slab_var=None,

    corrections_mode="df_column",  # corr_dict
    corrections_column="gibbs_correction",

    corrections_dict=None,
    ):
    """Calculate and add adsorption energy column to data_frame.

    Args:
        df:
    """
    #| - df_calc_adsorption_e
    ads_e_list = []
    for index, row in df.iterrows():
        bare_e = bare_slab_e


        #| - Correction
        corr = 0.
        # corr = fe_corr_dict[row["adsorbate"]]

        if corrections_mode == "df_column":
            corr = row[corrections_column]

            # If "df_column" method return 0. then try to use correction_dict
            if corr == 0.:
                if corrections_dict is not None:
                    corr = corrections_dict[row["adsorbate"]]

        elif corrections_mode == "corr_dict" and corrections_dict is not None:
            corr = corrections_dict[row["adsorbate"]]
        else:
            print("No correction being applied")
            corr = 0.
        #__|

        if type(bare_slab_e) == dict:
            bare_e = bare_slab_e[row[bare_slab_var]]

        elif type(bare_slab_e) == float:
            bare_e = bare_slab_e

        ads_e_i = calc_ads_e(
            row,
            # bare_slab,
            bare_e,
            correction=corr,
            oxy_ref_e=oxy_ref,
            hyd_ref_e=hyd_ref,
            )
        ads_e_list.append(ads_e_i)

    df["ads_e"] = np.array(ads_e_list)
    #__|

def lowest_e_path(
    df,
    jobs_variables,
    color_list,
    create_ideal_series=True,
    opt_name=None,
    bias=0.,
    manual_props="*TEMP*",
    plot_title="Free Energy Diagram for the Oxygen Reduction Reaction",
    smart_format=None,
    ):
    """Find the lowest energy pathway FED.

    COMBAK

    From a set of FE pathways corresponding to different sites, the lowest
    energy states will be selected to construct a new FED.

    Args:
        df:
        jobs_variables:
            Result of Jobs.tree_level_labels
        color_list:
        bias:

    """
    #| - lowest_e_path

    #| - Grouping By Adsorbate Type
    df = copy.deepcopy(df)
    groupby = copy.deepcopy(jobs_variables)

    groupby.remove("site")
    groupby.remove("adsorbate")

    data_master = {}
    if groupby == []:
        series_list = []
        for ads_i in df.groupby("adsorbate"):

            min_e_row = ads_i[1].loc[ads_i[1]["ads_e"].idxmin()]
            series_list.append(min_e_row)

        df_i = pd.DataFrame.from_items([(s.name, s) for s in series_list]).T
        data_master[manual_props] = df_i

    else:
        for group_i in df.groupby(groupby):
            series_list = []
            for ads_i in group_i[1].groupby("adsorbate"):

                min_e_row = ads_i[1].loc[ads_i[1]["ads_e"].idxmin()]
                series_list.append(min_e_row)

            df_i = pd.DataFrame.from_items([(s.name, s) for s in series_list]).T
            data_master[group_i[0]] = df_i

    #__|

    #| - Creating Data Sets

    #| - Creating FED Datasets
    data_list = []
    # for i_cnt, (key, fe_dict) in enumerate(data_master.iteritems()):
    for i_cnt, (key, fe_dict) in enumerate(data_master.items()):

        ORR = ORR_Free_E_Plot(
            free_energy_df=fe_dict,
            )

        dat_lst = ORR.plot_fed_series(
            bias=bias,
            opt_name=opt_name,
            properties=key,
            color_list=color_list,
            i_cnt=i_cnt,
            hover_text_col="site",
            smart_format=smart_format,
            )

        data_list.extend(dat_lst)
    #__|

    #| - Creating Ideal FED Dataset
    if create_ideal_series:
        e_list_ideal = ORR.apply_bias(bias, ORR.ideal_energy)

        dat_ideal = ORR.create_plotly_series(
            e_list_ideal,
            group="Ideal",
            name="Ideal",
            color=color_list[-1],
            plot_mode="full_lines",
            )

        dat_lst = data_list + dat_ideal

    else:

        dat_lst = data_list


    #__|

    # dat_lst = data_list + dat_ideal

    #__|

    #| - Plotting

    #| - Plot Settings
    plot_title_size = 18
    tick_lab_size = 16
    axes_lab_size = 18
    legend_size = 18
    #__|

    #| - Plot Layout
    # xax_labels = ["O2", "OOH", "O", "OH", "H2O"]
    # layout = {
    #
    #     "title": plot_title,
    #
    #     "font": {
    #         "family": "Courier New, monospace",
    #         "size": plot_title_size,
    #         "color": "black",
    #         },
    #
    #     #| - Axes --------------------------------------------------------------
    #     "yaxis": {
    #         "title": "Free Energy [eV]",
    #         "zeroline": True,
    #         "titlefont": dict(size=axes_lab_size),
    #         "showgrid": False,
    #         "tickfont": dict(
    #             size=tick_lab_size,
    #             ),
    #         },
    #
    #     "xaxis": {
    #         "title": "Reaction Coordinate",
    #         "zeroline": True,
    #         "titlefont": dict(size=axes_lab_size),
    #         "showgrid": False,
    #
    #         # "showticklabels": False,
    #
    #         "ticktext": xax_labels,
    #         "tickvals": [1.5 * i + 0.5 for i in range(len(xax_labels))],
    #
    #         "tickfont": dict(
    #             size=tick_lab_size,
    #             ),
    #         },
    #     #__| -------------------------------------------------------------------
    #
    #     #| - Legend ------------------------------------------------------------
    #     "legend": {
    #         "traceorder": "normal",
    #         "font": dict(size=legend_size)
    #         },
    #     #__| -------------------------------------------------------------------
    #
    #     #| - Plot Size
    #     # "width": 200 * 4.,
    #     # "height": 200 * 3.,
    #     #__|
    #
    #     }
    #__|

    layout = plotly_fed_layout(plot_title=plot_title)

    #__|

    return(dat_lst, layout)

    #__|

def plot_all_states(
    df,
    jobs_variables,
    color_list,
    bias=0.,
    hover_text_col="site",
    create_ideal_series=True,
    plot_title="Free Energy Diagram for the Oxygen Reduction Reaction",
    smart_format=None,
    ):
    """

    Args:
        df:
        jobs_variables:
        color_list:
        bias:
        plot_title:
    """
    #| - plot_all_states

    #| - Grouping By Adsorbate Type

    groupby = copy.deepcopy(jobs_variables)
    # groupby = copy.deepcopy(Jojobs_variablesbs.tree_level_labels)
    groupby.remove("adsorbate")

    data_master = {}
    for group_i in df.groupby(groupby):

        data_master[group_i[0]] = group_i[1]
    #__|

    #| - Creating Data Sets

    #| - Creating FED Datasets
    data_list = []
    # for i_cnt, (key, fe_dict) in enumerate(data_master.iteritems()):
    for i_cnt, (key, fe_dict) in enumerate(data_master.items()):
        ORR = ORR_Free_E_Plot(
            free_energy_df=fe_dict,
            )

        dat_lst = ORR.plot_fed_series(
            bias=bias,
            properties=key,
            color_list=color_list,
            i_cnt=i_cnt,
            # hover_text_col="site"
            hover_text_col=hover_text_col,
            plot_mode="states_only",
            smart_format=smart_format,
            )

        data_list.extend(dat_lst)
    #__|

    #| - Creating Ideal FED Dataset
    if create_ideal_series:

        e_list_ideal = ORR.apply_bias(bias, ORR.ideal_energy)

        dat_ideal = ORR.create_plotly_series(
            e_list_ideal,
            group="Ideal",
            name="Ideal",
            color="red",
            plot_mode="full_lines",
            )

        dat_lst = data_list + dat_ideal
    #__|

    else:
        dat_lst = data_list

    #__|

    #| - Plotting

    #| - Plot Settings
    plot_title_size = 18
    tick_lab_size = 16
    axes_lab_size = 18
    legend_size = 12
    #__|

    #| - Plot Layout
    # xax_labels = ["O2", "OOH", "O", "OH", "H2O"]
    # layout = {
    #
    #     "title": plot_title,
    #
    #     "font": {
    #         "family": "Courier New, monospace",
    #         "size": plot_title_size,
    #         "color": "black",
    #         },
    #
    #     #| - Axes --------------------------------------------------------------
    #     "yaxis": {
    #         "title": "Free Energy [eV]",
    #         "zeroline": True,
    #         "titlefont": dict(size=axes_lab_size),
    #         "showgrid": False,
    #         "tickfont": dict(
    #             size=tick_lab_size,
    #             ),
    #         },
    #
    #     "xaxis": {
    #         "title": "Reaction Coordinate",
    #         "zeroline": True,
    #         "titlefont": dict(size=axes_lab_size),
    #         "showgrid": False,
    #
    #         # "showticklabels": False,
    #
    #         "ticktext": xax_labels,
    #         "tickvals": [1.5 * i + 0.5 for i in range(len(xax_labels))],
    #
    #         "tickfont": dict(
    #             size=tick_lab_size,
    #             ),
    #         },
    #     #__| -------------------------------------------------------------------
    #
    #     #| - Legend ------------------------------------------------------------
    #     "legend": {
    #         "traceorder": "normal",
    #         "font": dict(size=legend_size)
    #         },
    #     #__| -------------------------------------------------------------------
    #
    #     #| - Plot Size
    #     "width": 200 * 4.,
    #     "height": 200 * 3.,
    #     #__|
    #
    #     }
    #__|

    layout = plotly_fed_layout(plot_title=plot_title)

    return(dat_lst, layout)

    #__|

    #__|

#__|





#| - __old__


#| - __old__

# class ORR_Free_E_Plot:
#     """ORR free energy diagram class.
#
#     Development Notes:
#         # TODO Should we consider the case where the bulk energy is not 0, and
#         we have to normalize all of the species energies by it?
#     """
#
#     #| - ORR_Free_E_Plot *******************************************************
#
#     def __init__(self,
#         free_energy_df=None,
#         ORR_Free_E_series_list=None,
#         # system_properties=None,
#         state_title="adsorbate",
#         free_e_title="ads_e",
#
#         smart_format=None,
#
#         bias=0.,
#
#         # opt_name=None,
#         # properties=None,
#
#         color_list=None,
#
#         # i_cnt=0,
#
#         hover_text_col=None,
#
#         # plot_mode="all",
#         # smart_format=None,
#         ):
#         """
#         Input variables to class instance.
#
#         Args:
#             free_energy_df:
#                 Pandas dataframe containing the adsorbates as rows
#                 Required columns, adsorbate, free energy
#             system_properties:
#             state_title:
#             free_e_title:
#         """
#         #| - __init__
#
#         #| - Setting Instance Attributes
#         self.fe_df = free_energy_df
#         # self.sys_props = system_properties
#         self.state_title = state_title
#         self.fe_title = free_e_title
#
#         self.rxn_mech_states = ["bulk", "ooh", "o", "oh", "bulk"]
#         self.ideal_energy = [4.92, 3.69, 2.46, 1.23, 0]
#
#         self.smart_format = smart_format
#
#         self.bias = bias
#         # self.opt_name = opt_name
#         # self.properties = properties
#         self.color_list = color_list
#         # self.i_cnt = i_cnt
#         self.hover_text_col = hover_text_col
#         # self.plot_mode = plot_mode
#         self.smart_format = smart_format
#
#         #__|
#
#         if ORR_Free_E_series_list is None:
#             self.series_list = []
#         else:
#             self.series_list = ORR_Free_E_series_list
#
#         #| - __old__
#         # if free_energy_df is not None:
#         #     self.add_bulk_entry()
#         #     self.fill_missing_data()
#         #
#         #     self.num_of_states = len(self.fe_df) + 1  # bulk, OOH, O, OH, bulk
#         #     self.energy_lst = self.rxn_energy_lst()
#         #     self.num_of_elec = range(self.num_of_states)[::-1]
#         #     self.overpotential = self.calc_overpotential()[0]
#         #     self.limiting_step = self.calc_overpotential()[1]
#         #     # self.ideal_energy = [4.92, 3.69, 2.46, 1.23, 0]
#         #     self.energy_lst_h2o2 = self.rxn_energy_lst_h2o2()
#         #     self.overpotential_h2o2 = self.calc_overpotential_h2o2()
#         #__|
#
#         #__|
#
#
#
#
#     #| - NEW METHODS - 180621
#
#     def ideal_ORR_series(self,
#         ):
#         """
#         """
#         #| - ideal_ORR_series
#
#         # self.ideal_energy = [4.92, 3.69, 2.46, 1.23, 0]
#
#         ideal_data_list = [
#
#             {
#                 "adsorbate": "ooh",
#                 "ads_e": 3.69,
#                 },
#
#             {
#                 "adsorbate": "o",
#                 "ads_e": 2.46,
#                 },
#
#             {
#                 "adsorbate": "oh",
#                 "ads_e": 1.23,
#                 },
#
#             ]
#
#         df_ideal = pd.DataFrame(ideal_data_list)
#
#
#         self.add_series(
#             df_ideal,
#             plot_mode="full_lines",  # ##########
#             opt_name="Ideal ORR Catalyst",
#             smart_format=False,
#
#             # state_title=self.state_title,
#             # free_e_title=self.fe_title,
#             # bias=self.bias,
#             #
#             # # opt_name=None,  # #######
#             # # properties=opt_name,
#             # # color_list=self.color_list,
#             # # i_cnt=0,  # ##########
#             # hover_text_col=self.hover_text_col,
#             #
#             # # smart_format=self.smart_format,
#             )
#
#         #__|
#
#
#     def add_series(self,
#         fe_df,
#         plot_mode="all",
#         opt_name=None,
#
#         smart_format=True,
#         ):
#         """
#         """
#         #| - add_series
#         if smart_format:
#             smart_format_i = self.smart_format
#         else:
#             smart_format_i = None
#
#         ORR_Series = ORR_Free_E_Series(
#             free_energy_df=fe_df,
#             # system_properties=None,
#             state_title=self.state_title,
#             free_e_title=self.fe_title,
#
#             bias=self.bias,
#             opt_name=opt_name,  # #######
#             # properties=opt_name,
#             color_list=self.color_list,
#             i_cnt=0,  # ##########
#             hover_text_col=self.hover_text_col,
#             plot_mode=plot_mode,  # ##########
#             smart_format=smart_format_i,
#             )
#
#         self.series_list.append(ORR_Series)
#         #__|
#
#     #__|
#
#
#     def plotly_data(self):
#         """
#         """
#         #| - plotly_data
#         master_data_list = []
#         for series_i in self.series_list:
#             master_data_list += series_i.series_plot
#
#         return(master_data_list)
#         #__|
#
#     def plotly_fed_layout(self,
#         plot_title="FED",
#         plot_title_size=18,
#         tick_lab_size=16,
#         axes_lab_size=18,
#         legend_size=18,
#         ):
#         """
#         """
#         #| - plotly_fed_layout
#
#         xax_labels = ["O2", "OOH", "O", "OH", "H2O"]
#         layout = {
#
#             "title": plot_title,
#
#             "font": {
#                 "family": "Courier New, monospace",
#                 "size": plot_title_size,
#                 "color": "black",
#                 },
#
#             #| - Axes --------------------------------------------------------------
#             "yaxis": {
#                 "title": "Free Energy [eV]",
#                 "zeroline": True,
#                 "titlefont": dict(size=axes_lab_size),
#                 "showgrid": False,
#                 "tickfont": dict(
#                     size=tick_lab_size,
#                     ),
#                 },
#
#             "xaxis": {
#                 "title": "Reaction Coordinate",
#                 "zeroline": True,
#                 "titlefont": dict(size=axes_lab_size),
#                 "showgrid": False,
#
#                 # "showticklabels": False,
#
#                 "ticktext": xax_labels,
#                 "tickvals": [1.5 * i + 0.5 for i in range(len(xax_labels))],
#
#                 "tickfont": dict(
#                     size=tick_lab_size,
#                     ),
#                 },
#             #__| -------------------------------------------------------------------
#
#             #| - Legend ------------------------------------------------------------
#             "legend": {
#                 "traceorder": "normal",
#                 "font": dict(size=legend_size)
#                 },
#             #__| -------------------------------------------------------------------
#
#             #| - Plot Size
#             # "width": 200 * 4.,
#             # "height": 200 * 3.,
#             #__|
#
#             }
#
#         return(layout)
#
#         #__|
#
#     # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
#     #| - ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#
#     # def add_bulk_entry(self,
#     #     bulk_e=0.0,
#     #     ):
#     #     """
#     #     Append a row entry to data frame corresponding to bulk state.
#     #
#     #     Args:
#     #         bulk_e:
#     #     """
#     #     #| - add_bulk_entry
#     #     df = self.fe_df
#     #     bulk_df = pd.DataFrame([{
#     #         "adsorbate": "bulk",
#     #         "ads_e": bulk_e,
#     #         }])
#     #
#     #     df = df.append(bulk_df, ignore_index=True)
#     #
#     #     self.fe_df = df
#     #     #__|
#     #
#     # def rxn_energy_lst_h2o2(self):
#     #     """Construct energy list of h2o2 FED."""
#     #     #| - rxn_energy_lst_h2o2
#     #     # h2o2_e = 3.52
#     #
#     #     df = self.fe_df
#     #
#     #     free_energy_list = []
#     #     for index, row in df.iterrows():
#     #         if row["adsorbate"] == "bulk" or row["adsorbate"] == "ooh":
#     #             free_energy_list.append(row["ads_e"])
#     #
#     #     # Checking length of energy list
#     #     if len(free_energy_list) != 2:
#     #         raise ValueError("Not the correct # of steps for H2O2")
#     #
#     #     free_energy_list[0] += 4.92
#     #     free_energy_list.append(3.52)
#     #
#     #     return(free_energy_list)
#     #     #__|
#     #
#     # def property_list(self, column_name):
#     #     """General method to create a list from a column in the dataframe.
#     #
#     #     The length of the list will correspond to the steps in the ORR
#     #     mechanism.
#     #
#     #     Args:
#     #         column_name:
#     #     """
#     #     #| - property_list
#     #     df = self.fe_df
#     #
#     #     property_list = []
#     #     for state in self.rxn_mech_states:
#     #         tmp = df.loc[df[self.state_title] == state]
#     #         tmp1 = tmp.iloc[0][column_name]
#     #         property_list.append(tmp1)
#     #
#     #     # free_energy_list[0] += 4.92
#     #
#     #     return(property_list)
#     #     #__|
#     #
#     # def fill_missing_data(self):
#     #     """
#     #     """
#     #     #| - fill_missing_data
#     #     df = self.fe_df
#     #     df_missing_data = pd.DataFrame()
#     #     for state in self.rxn_mech_states:
#     #         df_state = df.loc[df[self.state_title] == state]
#     #
#     #         #| - If df is missing state fill in row with NaN for energy
#     #         if df_state.empty:
#     #             df_state = pd.DataFrame([{
#     #                 self.state_title: state,
#     #                 self.fe_title: np.nan,
#     #                 }])
#     #             df_missing_data = df_missing_data.append(df_state)
#     #         #__|
#     #
#     #     self.fe_df = self.fe_df.append(df_missing_data)
#     #     #__|
#     #
#     # def rxn_energy_lst(self):
#     #     """List corresponding to the steps of ORR.
#     #
#     #     (1. O2, 2. *OOH, 3. *O, 4. *OH, 5. 2H2O)
#     #     """
#     #     #| - rxn_energy_lst
#     #     df = self.fe_df
#     #     free_energy_list = []
#     #     for state in self.rxn_mech_states:
#     #
#     #         df_state = df.loc[df[self.state_title] == state]
#     #
#     #         #| - If df is missing state fill in row with NaN for energy
#     #         if df_state.empty:
#     #             df_state = pd.DataFrame([{
#     #                 self.state_title: state,
#     #                 self.fe_title: np.nan,
#     #                 }])
#     #         #__|
#     #
#     #         tmp1 = df_state.iloc[0][self.fe_title]
#     #         free_energy_list.append(tmp1)
#     #
#     #     free_energy_list[0] += 4.92
#     #
#     #     return(free_energy_list)
#     #     #__|
#     #
#     # def apply_bias(self, bias, energy_list):
#     #     """Apply bias to free energies.
#     #
#     #     Applies a potential to every species in the 4 and 2-electron process
#     #     and adjusts their free energies accordingly
#     #     """
#     #     #| - apply_bias
#     #     mod_free_e_lst = []        # Free energy reaction path at applied bias
#     #     for energy, elec in zip(energy_list, range(len(energy_list))[::-1]):
#     #         mod_free_e_lst.append(energy - elec * bias)
#     #
#     #     return(mod_free_e_lst)
#     #     #__|
#     #
#     # def calc_overpotential(self):
#     #     """
#     #     Calculate overpotential for 4e- process.
#     #
#     #     Returns the limiting overpotential for the given species and the
#     #     limiting reaction step in the form of a list, species_A -> species_B is
#     #     [species_A, species_B]
#     #     """
#     #     #| - calc_overpotential
#     #     rxn_spec = self.rxn_mech_states
#     #
#     #     overpotential_lst = []
#     #     for energy_i in enumerate(self.energy_lst[:-1]):
#     #         energy_i_plus1 = self.energy_lst[energy_i[0] + 1]
#     #         overpotential_i = 1.23 + energy_i_plus1 - energy_i[1]
#     #         overpotential_lst.append(overpotential_i)
#     #
#     #     overpotential = max(overpotential_lst)
#     #     lim_step_index = overpotential_lst.index(overpotential)
#     #
#     #     limiting_step = [rxn_spec[lim_step_index], rxn_spec[lim_step_index + 1]]
#     #     out_list = [overpotential, limiting_step]
#     #
#     #     return(out_list)
#     #     #__|
#     #
#     # def calc_overpotential_h2o2(self):
#     #     """
#     #     Calculate overpotential for 2e- process.
#     #
#     #     The overpotential for the 2e- process depends only on the energy of the
#     #     *OOH intermediate
#     #     """
#     #     #| - calc_overpotential_h2o2
#     #     df = self.fe_df
#     #     ooh_row = df[df["adsorbate"] == "ooh"]
#     #     ooh_ads_e = ooh_row.iloc[0]["ads_e"]
#     #
#     #     op_4e = ooh_ads_e - 4.22
#     #
#     #     return(op_4e)
#     #     #__|
#     #
#     # def create_rxn_coord_array(self,
#     #     rxn_steps,
#     #     spacing=0,
#     #     step_size=1,
#     #     ):
#     #     """
#     #     Create a reaction coordinate array ([0, 1, 1, 2, 2, 3]) for plotting.
#     #
#     #     Args:
#     #         rxn_steps: <type 'int'>
#     #             Number of steps in reaction coordinate including initial
#     #             and final state.
#     #             Ex. A -> Intermediate -> C has 3 steps/states
#     #
#     #         spacing: <type 'float'>
#     #             Spacing inbetween the energy levels. The default of 0 creates
#     #             a free energy diagram that looks like steps
#     #     """
#     #     #| - create_rxn_coord_array
#     #     lst = []
#     #     for i in range(1, rxn_steps):
#     #         if i == 1:
#     #             lst.append(step_size)
#     #             lst.append(step_size + spacing)
#     #         if i != 1:
#     #             lst.append(lst[-1] + step_size)
#     #             lst.append(lst[-2] + step_size + spacing)
#     #
#     #     lst.insert(0, 0)
#     #     lst.append(lst[-1] + step_size)
#     #
#     #     return(lst)
#     #     #__|
#     #
#     #__| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#
#     # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
#     #| - Plotting @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#
#     def convert_to_plotting_list(self,
#         energy_lst,
#         spacing=0.5,
#         step_size=1,
#         ):
#         """
#         Repeat entries in energy list to conform to FED plot.
#
#         Modifies an energy list for plotting by repeating each entry
#         Ex. [4.92, 3.69, ... ] -> [4.92, 4.92, 3.69, 3.69, ... ]
#
#         Args:
#             energy_lst: <type 'list'>
#             spacing:
#             step_size:
#         """
#         #| - convert_to_plotting_list
#         tmp_list = range(len(energy_lst) * 2)
#         energy_dupl_lst = [energy_lst[i // 2] for i in tmp_list]
#
#         rxn_coord_steps = self.create_rxn_coord_array(
#             len(energy_lst),
#             spacing=spacing,
#             step_size=step_size,
#             )
#         out_list = [rxn_coord_steps, energy_dupl_lst]
#
#         return(out_list)
#         #__|
#
#     def plot_fed_series(self,
#         bias=0.,
#         opt_name=None,
#         properties=None,
#         color_list=None,
#         i_cnt=0,
#         hover_text_col=None,
#         plot_mode="all",
#         smart_format=None,
#         ):
#         """
#         Process data for FED plot.
#
#         Args:
#             bias:
#             opt_name
#             properties:
#             color_list:
#             i_cnt:
#             hover_text_col:
#                 Dataframe column name to be used for hover text
#
#         #FIXME | This is  fairly rough as of right now
#         """
#         #| - plot_fed_series
#         key = properties
#         if type(key) == tuple:
#             pass
#
#         elif key is None:
#             key = None
#         else:
#             key = (key,)
#
#         e_list = self.energy_lst
#         e_list = self.apply_bias(bias, e_list)
#
#         overpot_i = self.overpotential
#
#         for n, i in enumerate(e_list):
#             if np.isnan(i) is True:
#                 e_list[n] = None
#
#         if color_list is None:
#             color_list = ["red"]
#
#
#         if key is None:
#             prop_name = ""
#         else:
#             prop_name = "_".join([str(i) for i in key])
#
#         if opt_name is not None:
#             name_i = opt_name + ": " + prop_name + \
#                 " (OP: " + str(round(overpot_i, 2)) + ")"
#
#         else:
#             name_i = prop_name + \
#                 " (OP: " + str(round(overpot_i, 2)) + ")"
#
#         #| - Hover Text
#         if hover_text_col is not None:
#
#             if type(hover_text_col) is not list:
#                 hover_text_list = self.property_list(hover_text_col)
#
#             else:
#
#                 hover_text_lists = []
#                 for col_i in hover_text_col:
#
#                     # replacing nan with ""
#                     tmp = self.property_list(col_i)
#                     hover_text_i = ["" if x is np.nan else x for x in tmp]
#                     hover_text_lists.append(hover_text_i)
#
#                 # TODO Removed last trailing " | "
#                 hover_text_list = []
#                 for items in zip(*hover_text_lists):
#
#                     if all([True if i == "" else False for i in items]) is True:
#                         hover_col_state_i = ""
#                     else:
#                         hover_col_state_i = " | ".join(items)
#
#                     hover_text_list.append(hover_col_state_i)
#
#         else:
#             hover_text_list = [np.nan for j_cnt in list(range(5))]
#         #__|
#
#         dat_lst = self.create_plotly_series(
#             e_list,
#             group=name_i,
#             name=name_i,
#             hover_text=hover_text_list,
#             color=color_list[i_cnt - 1],
#             plot_mode=plot_mode,
#             smart_format=smart_format,
#             )
#
#         return(dat_lst)
#         #__|
#
#     def create_plotly_series(self,
#         energy_lst,
#         name="TEMP",
#         group="group1",
#         hover_text=None,
#         color="rgb(22, 96, 167)",
#         plot_mode="all",
#         smart_format=None,
#         ):
#         """
#         Create a plotly series for the current instance.
#
#         Args:
#             energy_lst:
#             name:
#             group:
#             color:
#             plot_mode:
#                 "all"
#                 "states_only"
#                 "full_lines"
#         """
#         #| - create_plotly_series
#         e_list = self.convert_to_plotting_list(energy_lst)
#         x_dat = e_list[0]
#         y_dat = e_list[1]
#
#         if hover_text is None:
#             hover_text = [np.nan for i_ind in range(5)]
#
#         #| - Parameters
#         if plot_mode == "all":
#             show_leg_2 = False
#         elif plot_mode == "states_only":
#             show_leg_2 = False
#         elif plot_mode == "full_lines":
#             show_leg_2 = True
#         #__|
#
#         #| - Adding Breaks in Data
#         new_x_dat = copy.copy(x_dat)
#         new_y_dat = copy.copy(y_dat)
#
#         cnt = 2
#         for i_ind in range(int(len(x_dat) / 2 - 1)):
#             fill = new_x_dat[cnt - 1]
#             new_x_dat.insert(cnt, fill)
#             new_y_dat.insert(cnt, None)
#             cnt += 3
#         #__|
#
#         #| - Creating x-data in middle of states
#         short_y = np.array(y_dat)[::2]
#
#         xdat = list(set(new_x_dat))
#         xdat.sort()
#
#         cnt = 0
#         short_x = []
#         for i_ind in range(int(len(xdat) / 2)):
#             short_x.append(xdat[cnt] + 0.5)  # FIXME Replace 0.5 with variable
#             cnt += 2
#         #__|
#
#
#         #| - Smart Format Dict ************************************************
#
#         #| - DICTS
#         plot_parameter_dict = {
#             "dash": None,
#             }
#
#         # smart_format = [
#         #
#         #     # [
#         #     #     {"spinpol": True},
#         #     #     {"dash": "dot"},
#         #     #     ],
#         #
#         #     [
#         #         {"system": "Fe_slab"},
#         #         {"dash": "dashdot"},
#         #         ],
#         #
#         #     [
#         #         {"system": "N_graph_Fe"},
#         #         {"dash": "dot"},
#         #         ],
#         #
#         #     [
#         #         {"system": "graph_Fe"},
#         #         {"dash": "dash"},
#         #         ],
#         #
#         #     [
#         #         {"system": "graphene"},
#         #         {"dash": None},
#         #         ],
#         #
#         #     ]
#
#         #__|
#
#         if self.fe_df is not None and smart_format is not None:
#             for format_i in smart_format:
#
#                 # format_i key:values
#                 df_col_name = list(format_i[0])[0]
#                 value_i = list(format_i[0].values())[0]
#                 setting_name = list(format_i[1])[0]
#                 setting_value = list(format_i[1].values())[0]
#
#
#                 if df_col_name in list(self.fe_df):
#
#                     # *OOH, *O, *OH entries must have value_i as the
#                     # column entries in the column df_col_name
#
#                     df = self.fe_df
#                     df_wo_bulk = df[df["adsorbate"] != "bulk"]
#
#                     if all(df_wo_bulk[df_col_name] == value_i):
#                         plot_parameter_dict.update({setting_name: setting_value})
#
#                 else:
#                     print("Dataframe column " + df_col_name + " not present")
#
#         #__| ******************************************************************
#
#         #| - Series Color
#         if "color" in list(plot_parameter_dict):
#             color_out = plot_parameter_dict["color"]
#         else:
#             plot_parameter_dict["color"] = color
#         #__|
#
#         #| - Plotly Scatter Plot Instances
#
#         #| - Thick horizontal state lines
#         data_1 = Scatter(
#             x=new_x_dat,
#             y=new_y_dat,
#             legendgroup=group,
#             showlegend=True,
#             name=name,
#             hoverinfo="none",  # TEMP - 180317
#             # text=hover_text,
#
#             connectgaps=False,
#             line=dict(
#                 # color=color,
#                 color=plot_parameter_dict["color"],
#                 width=6,
#                 # dash="dot",  # TEMP
#                 dash=plot_parameter_dict["dash"],  # TEMP
#                 ),
#             mode="lines",
#             )
#         #__|
#
#         #| - Full, thin line
#         data_2 = Scatter(
#             x=new_x_dat,
#             y=new_y_dat,
#             legendgroup=group,
#             name=name,
#             connectgaps=True,
#             showlegend=show_leg_2,
#             hoverinfo="none",
#             text=hover_text,
#
#             line=dict(
#                 # color=color,
#                 color=plot_parameter_dict["color"],
#                 width=1,
#                 ),
#             mode="lines",
#             )
#         #__|
#
#         #| - Points in middle of energy states
#         data_3 = Scatter(
#             x=short_x,
#             y=short_y,
#             legendgroup=group,
#             name=name,
#             showlegend=False,
#             hoverinfo="y+text",
#             text=hover_text,
#             marker=dict(
#                 size=14,
#                 color=color,
#                 opacity=0.,
#                 ),
#             mode="markers",
#             )
#         #__|
#
#         #__|
#
#         #| - Plot Mode (which data series to plot)
#         if plot_mode == "all":
#             data_lst = [data_1, data_2, data_3]
#         elif plot_mode == "states_only":
#             data_lst = [data_1, data_3]
#         elif plot_mode == "full_lines":
#             data_lst = [data_2, data_3]
#         #__|
#
#         return(data_lst)
#         #__|
#
#
#     #__| @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#
#     #__| **********************************************************************

#__|


#| - ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# def add_bulk_entry(self,
#     bulk_e=0.0,
#     ):
#     """
#     Append a row entry to data frame corresponding to bulk state.
#
#     Args:
#         bulk_e:
#     """
#     #| - add_bulk_entry
#     df = self.fe_df
#     bulk_df = pd.DataFrame([{
#         "adsorbate": "bulk",
#         "ads_e": bulk_e,
#         }])
#
#     df = df.append(bulk_df, ignore_index=True)
#
#     self.fe_df = df
#     #__|
#
# def rxn_energy_lst_h2o2(self):
#     """Construct energy list of h2o2 FED."""
#     #| - rxn_energy_lst_h2o2
#     # h2o2_e = 3.52
#
#     df = self.fe_df
#
#     free_energy_list = []
#     for index, row in df.iterrows():
#         if row["adsorbate"] == "bulk" or row["adsorbate"] == "ooh":
#             free_energy_list.append(row["ads_e"])
#
#     # Checking length of energy list
#     if len(free_energy_list) != 2:
#         raise ValueError("Not the correct # of steps for H2O2")
#
#     free_energy_list[0] += 4.92
#     free_energy_list.append(3.52)
#
#     return(free_energy_list)
#     #__|
#
# def property_list(self, column_name):
#     """General method to create a list from a column in the dataframe.
#
#     The length of the list will correspond to the steps in the ORR
#     mechanism.
#
#     Args:
#         column_name:
#     """
#     #| - property_list
#     df = self.fe_df
#
#     property_list = []
#     for state in self.rxn_mech_states:
#         tmp = df.loc[df[self.state_title] == state]
#         tmp1 = tmp.iloc[0][column_name]
#         property_list.append(tmp1)
#
#     # free_energy_list[0] += 4.92
#
#     return(property_list)
#     #__|
#
# def fill_missing_data(self):
#     """
#     """
#     #| - fill_missing_data
#     df = self.fe_df
#     df_missing_data = pd.DataFrame()
#     for state in self.rxn_mech_states:
#         df_state = df.loc[df[self.state_title] == state]
#
#         #| - If df is missing state fill in row with NaN for energy
#         if df_state.empty:
#             df_state = pd.DataFrame([{
#                 self.state_title: state,
#                 self.fe_title: np.nan,
#                 }])
#             df_missing_data = df_missing_data.append(df_state)
#         #__|
#
#     self.fe_df = self.fe_df.append(df_missing_data)
#     #__|
#
# def rxn_energy_lst(self):
#     """List corresponding to the steps of ORR.
#
#     (1. O2, 2. *OOH, 3. *O, 4. *OH, 5. 2H2O)
#     """
#     #| - rxn_energy_lst
#     df = self.fe_df
#     free_energy_list = []
#     for state in self.rxn_mech_states:
#
#         df_state = df.loc[df[self.state_title] == state]
#
#         #| - If df is missing state fill in row with NaN for energy
#         if df_state.empty:
#             df_state = pd.DataFrame([{
#                 self.state_title: state,
#                 self.fe_title: np.nan,
#                 }])
#         #__|
#
#         tmp1 = df_state.iloc[0][self.fe_title]
#         free_energy_list.append(tmp1)
#
#     free_energy_list[0] += 4.92
#
#     return(free_energy_list)
#     #__|
#
# def apply_bias(self, bias, energy_list):
#     """Apply bias to free energies.
#
#     Applies a potential to every species in the 4 and 2-electron process
#     and adjusts their free energies accordingly
#     """
#     #| - apply_bias
#     mod_free_e_lst = []        # Free energy reaction path at applied bias
#     for energy, elec in zip(energy_list, range(len(energy_list))[::-1]):
#         mod_free_e_lst.append(energy - elec * bias)
#
#     return(mod_free_e_lst)
#     #__|
#
# def calc_overpotential(self):
#     """
#     Calculate overpotential for 4e- process.
#
#     Returns the limiting overpotential for the given species and the
#     limiting reaction step in the form of a list, species_A -> species_B is
#     [species_A, species_B]
#     """
#     #| - calc_overpotential
#     rxn_spec = self.rxn_mech_states
#
#     overpotential_lst = []
#     for energy_i in enumerate(self.energy_lst[:-1]):
#         energy_i_plus1 = self.energy_lst[energy_i[0] + 1]
#         overpotential_i = 1.23 + energy_i_plus1 - energy_i[1]
#         overpotential_lst.append(overpotential_i)
#
#     overpotential = max(overpotential_lst)
#     lim_step_index = overpotential_lst.index(overpotential)
#
#     limiting_step = [rxn_spec[lim_step_index], rxn_spec[lim_step_index + 1]]
#     out_list = [overpotential, limiting_step]
#
#     return(out_list)
#     #__|
#
# def calc_overpotential_h2o2(self):
#     """
#     Calculate overpotential for 2e- process.
#
#     The overpotential for the 2e- process depends only on the energy of the
#     *OOH intermediate
#     """
#     #| - calc_overpotential_h2o2
#     df = self.fe_df
#     ooh_row = df[df["adsorbate"] == "ooh"]
#     ooh_ads_e = ooh_row.iloc[0]["ads_e"]
#
#     op_4e = ooh_ads_e - 4.22
#
#     return(op_4e)
#     #__|
#
# def create_rxn_coord_array(self,
#     rxn_steps,
#     spacing=0,
#     step_size=1,
#     ):
#     """
#     Create a reaction coordinate array ([0, 1, 1, 2, 2, 3]) for plotting.
#
#     Args:
#         rxn_steps: <type 'int'>
#             Number of steps in reaction coordinate including initial
#             and final state.
#             Ex. A -> Intermediate -> C has 3 steps/states
#
#         spacing: <type 'float'>
#             Spacing inbetween the energy levels. The default of 0 creates
#             a free energy diagram that looks like steps
#     """
#     #| - create_rxn_coord_array
#     lst = []
#     for i in range(1, rxn_steps):
#         if i == 1:
#             lst.append(step_size)
#             lst.append(step_size + spacing)
#         if i != 1:
#             lst.append(lst[-1] + step_size)
#             lst.append(lst[-2] + step_size + spacing)
#
#     lst.insert(0, 0)
#     lst.append(lst[-1] + step_size)
#
#     return(lst)
#     #__|
#
#__| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#| - Plotting @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

# def convert_to_plotting_list(self,
#     energy_lst,
#     spacing=0.5,
#     step_size=1,
#     ):
#     """
#     Repeat entries in energy list to conform to FED plot.
#
#     Modifies an energy list for plotting by repeating each entry
#     Ex. [4.92, 3.69, ... ] -> [4.92, 4.92, 3.69, 3.69, ... ]
#
#     Args:
#         energy_lst: <type 'list'>
#         spacing:
#         step_size:
#     """
#     #| - convert_to_plotting_list
#     tmp_list = range(len(energy_lst) * 2)
#     energy_dupl_lst = [energy_lst[i // 2] for i in tmp_list]
#
#     rxn_coord_steps = self.create_rxn_coord_array(
#         len(energy_lst),
#         spacing=spacing,
#         step_size=step_size,
#         )
#     out_list = [rxn_coord_steps, energy_dupl_lst]
#
#     return(out_list)
#     #__|
#
# def plot_fed_series(self,
#     bias=0.,
#     opt_name=None,
#     properties=None,
#     color_list=None,
#     i_cnt=0,
#     hover_text_col=None,
#     plot_mode="all",
#     smart_format=None,
#     ):
#     """
#     Process data for FED plot.
#
#     Args:
#         bias:
#         opt_name
#         properties:
#         color_list:
#         i_cnt:
#         hover_text_col:
#             Dataframe column name to be used for hover text
#
#     #FIXME | This is  fairly rough as of right now
#     """
#     #| - plot_fed_series
#     key = properties
#     if type(key) == tuple:
#         pass
#
#     elif key is None:
#         key = None
#     else:
#         key = (key,)
#
#     e_list = self.energy_lst
#     e_list = self.apply_bias(bias, e_list)
#
#     overpot_i = self.overpotential
#
#     for n, i in enumerate(e_list):
#         if np.isnan(i) is True:
#             e_list[n] = None
#
#     if color_list is None:
#         color_list = ["red"]
#
#
#     if key is None:
#         prop_name = ""
#     else:
#         prop_name = "_".join([str(i) for i in key])
#
#     if opt_name is not None:
#         name_i = opt_name + ": " + prop_name + \
#             " (OP: " + str(round(overpot_i, 2)) + ")"
#
#     else:
#         name_i = prop_name + \
#             " (OP: " + str(round(overpot_i, 2)) + ")"
#
#     #| - Hover Text
#     if hover_text_col is not None:
#
#         if type(hover_text_col) is not list:
#             hover_text_list = self.property_list(hover_text_col)
#
#         else:
#
#             hover_text_lists = []
#             for col_i in hover_text_col:
#
#                 # replacing nan with ""
#                 tmp = self.property_list(col_i)
#                 hover_text_i = ["" if x is np.nan else x for x in tmp]
#                 hover_text_lists.append(hover_text_i)
#
#             # TODO Removed last trailing " | "
#             hover_text_list = []
#             for items in zip(*hover_text_lists):
#
#                 if all([True if i == "" else False for i in items]) is True:
#                     hover_col_state_i = ""
#                 else:
#                     hover_col_state_i = " | ".join(items)
#
#                 hover_text_list.append(hover_col_state_i)
#
#     else:
#         hover_text_list = [np.nan for j_cnt in list(range(5))]
#     #__|
#
#     dat_lst = self.create_plotly_series(
#         e_list,
#         group=name_i,
#         name=name_i,
#         hover_text=hover_text_list,
#         color=color_list[i_cnt - 1],
#         plot_mode=plot_mode,
#         smart_format=smart_format,
#         )
#
#     return(dat_lst)
#     #__|
#
# def create_plotly_series(self,
#     energy_lst,
#     name="TEMP",
#     group="group1",
#     hover_text=None,
#     color="rgb(22, 96, 167)",
#     plot_mode="all",
#     smart_format=None,
#     ):
#     """
#     Create a plotly series for the current instance.
#
#     Args:
#         energy_lst:
#         name:
#         group:
#         color:
#         plot_mode:
#             "all"
#             "states_only"
#             "full_lines"
#     """
#     #| - create_plotly_series
#     e_list = self.convert_to_plotting_list(energy_lst)
#     x_dat = e_list[0]
#     y_dat = e_list[1]
#
#     if hover_text is None:
#         hover_text = [np.nan for i_ind in range(5)]
#
#     #| - Parameters
#     if plot_mode == "all":
#         show_leg_2 = False
#     elif plot_mode == "states_only":
#         show_leg_2 = False
#     elif plot_mode == "full_lines":
#         show_leg_2 = True
#     #__|
#
#     #| - Adding Breaks in Data
#     new_x_dat = copy.copy(x_dat)
#     new_y_dat = copy.copy(y_dat)
#
#     cnt = 2
#     for i_ind in range(int(len(x_dat) / 2 - 1)):
#         fill = new_x_dat[cnt - 1]
#         new_x_dat.insert(cnt, fill)
#         new_y_dat.insert(cnt, None)
#         cnt += 3
#     #__|
#
#     #| - Creating x-data in middle of states
#     short_y = np.array(y_dat)[::2]
#
#     xdat = list(set(new_x_dat))
#     xdat.sort()
#
#     cnt = 0
#     short_x = []
#     for i_ind in range(int(len(xdat) / 2)):
#         short_x.append(xdat[cnt] + 0.5)  # FIXME Replace 0.5 with variable
#         cnt += 2
#     #__|
#
#
#     #| - Smart Format Dict ************************************************
#
#     #| - DICTS
#     plot_parameter_dict = {
#         "dash": None,
#         }
#
#     # smart_format = [
#     #
#     #     # [
#     #     #     {"spinpol": True},
#     #     #     {"dash": "dot"},
#     #     #     ],
#     #
#     #     [
#     #         {"system": "Fe_slab"},
#     #         {"dash": "dashdot"},
#     #         ],
#     #
#     #     [
#     #         {"system": "N_graph_Fe"},
#     #         {"dash": "dot"},
#     #         ],
#     #
#     #     [
#     #         {"system": "graph_Fe"},
#     #         {"dash": "dash"},
#     #         ],
#     #
#     #     [
#     #         {"system": "graphene"},
#     #         {"dash": None},
#     #         ],
#     #
#     #     ]
#
#     #__|
#
#     if self.fe_df is not None and smart_format is not None:
#         for format_i in smart_format:
#
#             # format_i key:values
#             df_col_name = list(format_i[0])[0]
#             value_i = list(format_i[0].values())[0]
#             setting_name = list(format_i[1])[0]
#             setting_value = list(format_i[1].values())[0]
#
#
#             if df_col_name in list(self.fe_df):
#
#                 # *OOH, *O, *OH entries must have value_i as the
#                 # column entries in the column df_col_name
#
#                 df = self.fe_df
#                 df_wo_bulk = df[df["adsorbate"] != "bulk"]
#
#                 if all(df_wo_bulk[df_col_name] == value_i):
#                     plot_parameter_dict.update({setting_name: setting_value})
#
#             else:
#                 print("Dataframe column " + df_col_name + " not present")
#
#     #__| ******************************************************************
#
#     #| - Series Color
#     if "color" in list(plot_parameter_dict):
#         color_out = plot_parameter_dict["color"]
#     else:
#         plot_parameter_dict["color"] = color
#     #__|
#
#     #| - Plotly Scatter Plot Instances
#
#     #| - Thick horizontal state lines
#     data_1 = Scatter(
#         x=new_x_dat,
#         y=new_y_dat,
#         legendgroup=group,
#         showlegend=True,
#         name=name,
#         hoverinfo="none",  # TEMP - 180317
#         # text=hover_text,
#
#         connectgaps=False,
#         line=dict(
#             # color=color,
#             color=plot_parameter_dict["color"],
#             width=6,
#             # dash="dot",  # TEMP
#             dash=plot_parameter_dict["dash"],  # TEMP
#             ),
#         mode="lines",
#         )
#     #__|
#
#     #| - Full, thin line
#     data_2 = Scatter(
#         x=new_x_dat,
#         y=new_y_dat,
#         legendgroup=group,
#         name=name,
#         connectgaps=True,
#         showlegend=show_leg_2,
#         hoverinfo="none",
#         text=hover_text,
#
#         line=dict(
#             # color=color,
#             color=plot_parameter_dict["color"],
#             width=1,
#             ),
#         mode="lines",
#         )
#     #__|
#
#     #| - Points in middle of energy states
#     data_3 = Scatter(
#         x=short_x,
#         y=short_y,
#         legendgroup=group,
#         name=name,
#         showlegend=False,
#         hoverinfo="y+text",
#         text=hover_text,
#         marker=dict(
#             size=14,
#             color=color,
#             opacity=0.,
#             ),
#         mode="markers",
#         )
#     #__|
#
#     #__|
#
#     #| - Plot Mode (which data series to plot)
#     if plot_mode == "all":
#         data_lst = [data_1, data_2, data_3]
#     elif plot_mode == "states_only":
#         data_lst = [data_1, data_3]
#     elif plot_mode == "full_lines":
#         data_lst = [data_2, data_3]
#     #__|
#
#     return(data_lst)
#     #__|
#

#__| @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

#__|
