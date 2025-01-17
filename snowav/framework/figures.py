import copy
from datetime import datetime, timedelta
import numpy as np
import os
import pandas as pd

from tablizer.tablizer import get_existing_records
from snowav.plotting.swi import swi
from snowav.plotting.basin_total import basin_total
from snowav.plotting.cold_content import cold_content
from snowav.plotting.compare_runs import compare_runs
from snowav.plotting.density import density
from snowav.plotting.flt_image_change import flt_image_change
from snowav.plotting.image_change import image_change
from snowav.plotting.precip_depth import precip_depth
from snowav.plotting.stn_validate import stn_validate
from snowav.plotting.write_properties import write_properties
from snowav.plotting.swe_volume import swe_volume
from snowav.plotting.inputs import inputs
from snowav.inflow.inflow import inflow
from snowav.plotting.diagnostics import diagnostics
from snowav.plotting.point_values import point_values_csv, point_values_figures
from snowav.database.database import collect
from snowav.database.tables import Results
from snowav.plotting.plotlims import plotlims as plotlims
import matplotlib as mpl

if os.environ.get('DISPLAY', '') == '':
    mpl.use('Agg')


def figures(cfg, process, db):
    """ Set up and call snowav figures. See CoreConfig.ini and README.md for
    more on config options and use.

    swe_volume() must be called before cold_content() if you want to use
    the same ylims for each.

    Args
    ------
    cfg: config class
    process: process class
    db: database class
    """

    args = {'report_start': cfg.report_start.date().strftime("%Y-%-m-%-d"),
            'report_date': cfg.report_date.date().strftime("%Y-%-m-%-d"),
            'run_name': cfg.run_name,
            'start_date': cfg.start_date,
            'end_date': cfg.end_date,
            'directory': cfg.directory,
            'figs_path': cfg.figs_path,
            'edges': cfg.edges,
            'plotorder': cfg.plotorder,
            'labels': cfg.labels,
            'lims': plotlims(cfg.plotorder),
            'masks': cfg.masks,
            'figsize': cfg.figsize,
            'dpi': cfg.dpi,
            'depthlbl': cfg.depthlbl,
            'vollbl': cfg.vollbl,
            'elevlbl': cfg.elevlbl,
            'dplcs': cfg.dplcs,
            'barcolors': cfg.barcolors,
            'xlims': cfg.xlims,
            'depth_clip': cfg.depth_clip,
            'percent_min': cfg.clims_percent[0],
            'percent_max': cfg.clims_percent[1],
            'basins': cfg.basins,
            'wy': cfg.wy,
            'flag': False,
            'flt_flag': cfg.flt_flag}

    if cfg.flt_flag:
        args['flight_dates'] = cfg.flight_diff_dates

    fig_names = {}
    connector = cfg.connector
    edges_str = [str(x) for x in list(cfg.edges)] # + ['total']

    ##########################################################################
    #       For each figure, collect 2D array image, by-elevation            #
    #       DataFrame, and set any figure-specific args inputs               #
    ##########################################################################
    if cfg.flt_flag:
        names, df = flt_image_change(cfg.update_file, cfg.update_numbers,
                                     cfg.end_date, cfg.flight_outputs,
                                     cfg.pre_flight_outputs, cfg.masks,
                                     cfg.flt_image_change_clims, cfg.barcolors,
                                     cfg.edges, cfg.connector, cfg.plotorder,
                                     cfg.wy, cfg.depth_factor, cfg.basins,
                                     cfg.run_name, cfg.figsize, cfg.depthlbl,
                                     cfg.elevlbl, cfg.vollbl, cfg.dplcs,
                                     cfg.figs_path, dpi=cfg.dpi,
                                     logger=cfg._logger)

        if len(names) == 0:
            cfg.flt_flag = False
        else:
            cfg.assign_vars({'flight_diff_fig_names': names})
            cfg.assign_vars({'flight_delta_vol_df': df})

    if cfg.swi_flag:
        image = np.zeros_like(cfg.outputs['swi_z'][0])
        for n in range(cfg.ixs, cfg.ixe):
            image = image + cfg.outputs['swi_z'][n] * cfg.depth_factor

        params = {Results: [
            ('date_time', 'ge', cfg.start_date),
            ('date_time', 'le', cfg.end_date),
            ('variable', 'eq', 'swi_vol'),
            ('run_id', 'eq', cfg.run_id),
            ('value', 'ge', 0),
            ('elevation', 'gt', '0')
        ],
        }

        df = db.query(params)
        df = df.groupby('elevation').sum()
        df.rename(columns={'value': cfg.plotorder[0]}, inplace=True)
        df = df[cfg.plotorder].reindex(edges_str)

        title = 'Accumulated SWI\n{} to {}'.format(args['report_start'],
                                                   args['report_date'])

        swi(cfg.masks, image, df, cfg.plotorder, plotlims(cfg.plotorder),
            cfg.edges, cfg.labels, cfg.barcolors, cfg.vollbl, cfg.elevlbl,
            cfg.depthlbl, cfg.clims_percent, title, cfg.figsize, cfg.figs_path,
            cfg.swi_volume_fig_name, cfg.dplcs, cfg.xlims, dpi=200,
            logger=None)

    if cfg.image_change_flag:
        image = (cfg.outputs['swe_z'][cfg.ixe] -
                 cfg.outputs['swe_z'][cfg.ixs]) * cfg.depth_factor

        start = collect(connector, args['plotorder'], args['basins'],
                        args['start_date'], args['start_date'], 'swe_vol',
                        args['run_name'], args['edges'], 'end')
        end = collect(connector, args['plotorder'], args['basins'],
                      args['start_date'], args['end_date'], 'swe_vol',
                      args['run_name'], args['edges'], 'end')

        df = end - start
        title = 'Change in SWE Depth\n{} to {}'.format(args['report_start'],
                                                       args['report_date'])

        image_change(cfg.masks, image, df, cfg.plotorder,
                     plotlims(cfg.plotorder), cfg.edges, cfg.labels,
                     cfg.barcolors, cfg.clims_percent, cfg.vollbl, cfg.elevlbl,
                     cfg.depthlbl, cfg.xlims, cfg.figsize, title, cfg.dplcs,
                     cfg.figs_path, cfg.volume_change_fig_name, dpi=cfg.dpi,
                     logger=cfg._logger)

    if cfg.swe_volume_flag:
        df = collect(connector, cfg.plotorder, cfg.basins, cfg.start_date,
                     cfg.end_date, 'swe_vol', cfg.run_name, cfg.edges, 'end')

        image = cfg.outputs['swe_z'][cfg.ixe] * cfg.depth_factor
        args['image'] = image
        title = 'SWE {}'.format(args['report_date'])

        swe_ylims = swe_volume(cfg.masks, image, df, cfg.plotorder,
                               plotlims(cfg.plotorder), cfg.edges, cfg.labels,
                               cfg.barcolors, cfg.clims_percent, title,
                               cfg.depthlbl, cfg.vollbl, cfg.elevlbl,
                               cfg.xlims, cfg.dplcs, cfg.figs_path,
                               cfg.swe_volume_fig_name, cfg.figsize,
                               dpi=cfg.dpi, logger=cfg._logger)
    else:
        swe_ylims = None

    if cfg.cold_content_flag:
        swe = cfg.outputs['swe_z'][cfg.ixe]
        image = cfg.outputs['coldcont'][cfg.ixe] * 0.000001
        title = 'Cold Content {}'.format(args['report_date'])
        df = collect(connector, args['plotorder'], args['basins'],
                     args['start_date'], args['end_date'], 'swe_unavail',
                     args['run_name'], args['edges'], 'end')

        cold_content(cfg.masks, swe, image, df, cfg.plotorder,
                     plotlims(cfg.plotorder), cfg.edges, cfg.labels,
                     cfg.barcolors, title, cfg.vollbl, cfg.elevlbl,
                     cfg.figsize, cfg.dplcs, cfg.xlims, cfg.figs_path,
                     cfg.cold_content_fig_name, ylims=swe_ylims,
                     dpi=cfg.dpi, logger=cfg._logger)

    if cfg.density_flag:
        image = cfg.outputs['density'][cfg.ixe]
        title = 'Density {}'.format(args['report_date'])

        density(cfg.masks, image, process.density, cfg.plotorder,
                plotlims(cfg.plotorder), cfg.edges, cfg.barcolors,
                cfg.clims_percent, title, cfg.xlims, cfg.figsize, cfg.figs_path,
                cfg.density_fig_name, dpi=cfg.dpi, logger=cfg._logger)

    if cfg.basin_total_flag:
        wy_start = datetime(cfg.wy - 1, 10, 1)
        swi_summary = collect(connector, cfg.plotorder, cfg.basins, wy_start,
                              cfg.end_date, 'swi_vol', cfg.run_name, 'total',
                              'daily')
        df_swe = collect(connector, cfg.plotorder, cfg.basins, wy_start,
                         cfg.end_date, 'swe_vol', cfg.run_name, 'total',
                         'daily')
        df_swi = swi_summary.cumsum()

        basin_total(cfg.plotorder, cfg.labels, cfg.end_date, cfg.barcolors,
                    df_swi, df_swe, cfg.wy, cfg.vollbl, cfg.figsize,
                    cfg.figs_path, cfg.basin_total_fig_name, dpi=cfg.dpi,
                    flight_dates=cfg.flight_diff_dates, logger=cfg._logger,
                    flight_flag=cfg.flt_flag)

    if cfg.precip_depth_flag:
        swi_image = np.zeros_like(cfg.outputs['swi_z'][0])
        for n in range(cfg.ixs, cfg.ixe):
            swi_image = swi_image + cfg.outputs['swi_z'][n] * cfg.depth_factor

        swi_df = collect(connector, args['plotorder'], args['basins'],
                         args['start_date'], args['end_date'], 'swi_z',
                         args['run_name'], args['edges'], 'sum')
        precip_df = collect(connector, args['plotorder'], args['basins'],
                            args['start_date'], args['end_date'], 'precip_z',
                            args['run_name'], args['edges'], 'sum')
        rain_df = collect(connector, args['plotorder'], args['basins'],
                          args['start_date'], args['end_date'], 'rain_z',
                          args['run_name'], args['edges'], 'sum')

        precip_image = process.precip_total * cfg.depth_factor
        rain_image = process.rain_total * cfg.depth_factor
        title = 'Depth of SWI, Precipitation, and Rain\n{} to {}'.format(
            args['report_start'], args['report_date'])

        precip_depth(swi_image, precip_image, rain_image, swi_df, precip_df,
                     rain_df, cfg.plotorder, cfg.barcolors,
                     plotlims(cfg.plotorder), cfg.masks, cfg.edges, cfg.labels,
                     cfg.clims_percent, cfg.depthlbl, cfg.elevlbl, title,
                     cfg.xlims, cfg.figs_path, cfg.precip_fig_name,
                     logger=cfg._logger)

    if cfg.diagnostics_flag:
        wy_start = datetime(cfg.wy - 1, 10, 1)
        precip = collect(connector, args['plotorder'], args['basins'],
                         wy_start, args['end_date'], 'precip_z',
                         args['run_name'], args['edges'], 'daily')
        precip_per = collect(connector, args['plotorder'], args['basins'],
                             args['start_date'], args['end_date'], 'precip_z',
                             args['run_name'], args['edges'], 'daily')
        swe = collect(connector, args['plotorder'], args['basins'],
                      wy_start, args['end_date'], 'swe_z',
                      args['run_name'], args['edges'], 'daily')
        swe_per = collect(connector, args['plotorder'], args['basins'],
                          args['start_date'], args['end_date'], 'swe_z',
                          args['run_name'], args['edges'], 'daily')
        rho = collect(connector, args['plotorder'], args['basins'],
                      wy_start, args['end_date'], 'density',
                      args['run_name'], args['edges'], 'daily')
        rho_per = collect(connector, args['plotorder'], args['basins'],
                          args['start_date'], args['end_date'], 'density',
                          args['run_name'], args['edges'], 'daily')
        snow_line = collect(connector, args['plotorder'], args['basins'],
                            wy_start, args['end_date'], 'snow_line',
                            args['run_name'], args['edges'], 'daily')

        snow_line_per = collect(connector, args['plotorder'], args['basins'],
                                args['start_date'], args['end_date'], 'snow_line',
                                args['run_name'], args['edges'], 'daily')
        evap_z = collect(connector, args['plotorder'], args['basins'],
                         wy_start, args['end_date'], 'evap_z',
                         args['run_name'], args['edges'], 'daily')
        evap_z_per = collect(connector, args['plotorder'], args['basins'],
                             args['start_date'], args['end_date'], 'evap_z',
                             args['run_name'], args['edges'], 'daily')

        snow_line_per = snow_line_per.fillna(0)
        first_row = snow_line_per.iloc[[0]].values[0]
        snow_line_per = snow_line_per.apply(lambda row: row - first_row, axis=1)
        args['snow_line'] = snow_line
        args['snow_line_per'] = snow_line_per

        swe = swe.fillna(0)
        swe_per = swe_per.fillna(0)
        first_row = swe_per.iloc[[0]].values[0]
        swe_per = swe_per.apply(lambda row: row - first_row, axis=1)

        evap_z = evap_z.fillna(0)
        evap_z_per = evap_z_per.fillna(0)
        first_row = evap_z_per.iloc[[0]].values[0]
        evap_z_per = evap_z_per.apply(lambda row: row - first_row, axis=1)

        rho = rho.fillna(0)
        rho_per = rho_per.fillna(0)
        first_row = rho_per.iloc[[0]].values[0]
        rho_per = rho_per.apply(lambda row: row - first_row, axis=1)

        precip = precip.fillna(0)
        precip_per = precip_per.fillna(0)
        precip = precip.cumsum()
        precip_per = precip_per.cumsum()
        first_row = precip_per.iloc[[0]].values[0]
        precip_per = precip_per.apply(lambda row: row - first_row, axis=1)

        if cfg.diag_basins is None:
            args['dbasins'] = copy.deepcopy(cfg.plotorder)
        else:
            args['dbasins'] = cfg.diag_basins

        args['precip'] = precip
        args['precip_per'] = precip_per
        args['swe'] = swe
        args['swe_per'] = swe_per
        args['evap_z'] = evap_z
        args['evap_z_per'] = evap_z_per
        args['density'] = rho
        args['density_per'] = rho_per
        args['elevlbl'] = cfg.elevlbl

        diagnostics(args, cfg._logger)

    if cfg.stn_validate_flag:
        px = (1, 1, 1, 0, 0, 0, -1, -1, -1)
        py = (1, 0, -1, 1, 0, -1, 1, 0, -1)
        login = {'user': cfg.wxdb_user,
                 'password': cfg.wxdb_password,
                 'host': cfg.wxdb_host,
                 'port': cfg.wxdb_port}

        flag = stn_validate(cfg.all_dirs, cfg.val_lbls, cfg.val_client,
                            args['end_date'], args['wy'], cfg.snow_x,
                            cfg.snow_y, cfg.val_stns, px, py, login,
                            args['figs_path'], cfg.stn_validate_fig_name,
                            cfg.dem, logger=cfg._logger, elevlbl=cfg.elevlbl,
                            nash_sut_flag=cfg.nash_sut_flag)

        if not flag:
            cfg.stn_validate_flag = False

    else:
        # assign fig name to cfg for use in report.py
        cfg.assign_vars({'stn_validate_fig_name': ''})

    if cfg.point_values:
        cfg._logger.debug(" Beginning point values processing for "
                          "{}".format(cfg.point_values_csv))

        flag = True
        xy = (cfg.snow_x, cfg.snow_y)
        headings = ['name', 'latitude', 'longitude', cfg.point_values_heading]
        end_date_str = cfg.end_date.date().strftime("%Y-%m-%d")
        course_date = cfg.point_values_date.date().strftime('%Y-%m-%d')
        basin_name = cfg.plotorder[0].split(" ")[0].lower()
        pv_date = cfg.point_values_date
        nsubplots = (cfg.point_values_settings[3] *
                     cfg.point_values_settings[4] - 1) - 1

        while flag:
            df = pd.read_csv(cfg.point_values_csv)

            for head in headings:
                if head not in df.columns.tolist():
                    cfg._logger.warn(' Required csv column "{}" not found, '
                                     'exiting point values'.format(head))
                    if head == cfg.point_values_heading:
                        cfg._logger.warning(' User specified [validate] '
                                            'point_values_heading: {} not '
                                            'found'.format(head))
                    flag = False

            if pv_date is None:
                cfg._logger.info(' Value in [validate] point_values_date '
                                 'being assigned to {}'.format(end_date_str))
                pv_date = cfg.end_date

            if pv_date < cfg.start_date or pv_date > cfg.end_date:
                cfg._logger.info(' Value in [validate] point_values_date '
                                 'outside of range in [run] start_date - '
                                 'end_date, point_values_date being assigned '
                                 'to: {}'.format(end_date_str))
                idx = -1
            else:
                x = np.abs([date - pv_date for date in cfg.outputs['dates']])
                idx = x.argmin(0)

            model_date = cfg.outputs['dates'][idx].date().strftime('%Y-%m-%d')

            for value in cfg.point_values_properties:
                filename = '{}_pixel_{}_{}.csv'.format(basin_name, value,
                                                       end_date_str)
                csv_name = os.path.abspath(os.path.join(cfg.figs_path,
                                                        filename))

                if len(df.name.unique()) > nsubplots:
                    cfg._logger.warn(' Number of subplots in '
                                     'point_values() may not fit well with '
                                     'given settings, consider changing '
                                     'nrows and/or ncols in [validate] '
                                     'point_values_settings')
                    flag = False

                if value == 'swe_z':
                    factor = cfg.depth_factor
                elif value == 'depth':
                    factor = 39.37
                else:
                    factor = 1

                array = cfg.outputs[value][idx] * factor

                df_res = point_values_csv(array, value, df, xy, csv_name,
                                          model_date, cfg.plotorder[0],
                                          cfg.point_values_heading,
                                          cfg._logger)

                if cfg.point_values_flag:
                    head = cfg.point_values_heading
                    if head in df.columns.tolist():
                        point_values_figures(array, value, df_res, cfg.dem,
                                             cfg.figs_path, cfg.veg_type,
                                             model_date, course_date,
                                             cfg.point_values_settings,
                                             cfg.pixel, head, cfg._logger)
                    else:
                        cfg._logger.warn(' [validate] point_values_heading: '
                                         '{} not in csv, skipping figures '
                                         ''.format(cfg.point_values_heading))
                        cfg.point_values_flag = False

            # if everything is successful, set to False at the end
            flag = False

    if cfg.compare_runs_flag:
        args['variables'] = ['swe_vol', 'swi_vol']

        if cfg.flt_flag:
            args['flag'] = True
        else:
            args['flag'] = False

        dict = {}
        for var in args['variables']:
            dict[var] = {}
            for wy, run in zip(cfg.compare_run_wys, cfg.compare_run_names):
                wy_start = datetime(wy - 1, 10, 1)
                df = collect(connector, args['plotorder'][0], args['basins'],
                             wy_start, args['end_date'], var, run, 'total', 'daily')

                if wy != cfg.wy:
                    adj = cfg.wy - wy
                    df.index = df.index + timedelta(days=365 * adj)

                if var == 'swi_vol':
                    df = df.cumsum()

                dict[var][run] = df

        args['dict'] = dict

        compare_runs(args, cfg._logger)

    if cfg.inflow_flag:
        wy_start = datetime(cfg.wy - 1, 10, 1)
        swi_summary = collect(connector, args['plotorder'], args['basins'],
                              wy_start, args['end_date'], 'swi_vol',
                              args['run_name'], 'total', 'daily')
        df_swi = swi_summary.cumsum()

        args['swi_summary'] = df_swi

        if cfg.inflow_data is None:
            raw = pd.read_csv(cfg.summary_csv, skiprows=1,
                              parse_dates=[0], index_col=0)
            args['inflow_summary'] = raw[cfg.basin_headings]

        else:
            args['inflow_summary'] = pd.read_csv(cfg.summary_csv,
                                                 parse_dates=[0], index_col=0)

        args['inflow_headings'] = cfg.inflow_headings
        args['basin_headings'] = cfg.basin_headings

        inflow(args, cfg._logger)

    if cfg.write_properties is not None:
        write_properties(args['end_date'], cfg.connector, args['plotorder'],
                         args['basins'], datetime(cfg.wy - 1, 10, 1),
                         args['run_name'], args['figs_path'],
                         cfg.write_properties, vollbl=args['vollbl'],
                         logger=cfg._logger)

    if cfg.inputs_fig_flag:

        if cfg.mysql is not None:
            dbs = 'sql'
        else:
            dbs = 'sqlite'

        df = get_existing_records(connector, dbs)
        df = df.set_index('date_time')
        df.sort_index(inplace=True)

        ivalue = {}
        p = []

        for var in cfg.plots_inputs_variables:
            ivalue[var] = {}

            for basin in cfg.inputs_basins:
                bid = args['basins'][basin]['basin_id']
                ivalue[var][basin] = {}

                for func in cfg.inputs_methods:

                    if 'percentile' in func:
                        nfunc = '{}_{}'.format(func, str(cfg.inputs_percentiles[0]))

                        if ((var == cfg.plots_inputs_variables[0]) and
                                (basin == cfg.inputs_basins[0])):
                            p.append(nfunc)

                        ivalue[var][basin][nfunc] = df[(df['function'] == nfunc) &
                                                       (df['variable'] == var) &
                                                       (df['basin_id'] == int(bid)) &
                                                       (df['run_name'] == args['run_name'])]

                        nfunc = '{}_{}'.format(func, str(cfg.inputs_percentiles[1]))

                        if ((var == cfg.plots_inputs_variables[0]) and
                                (basin == cfg.inputs_basins[0])):
                            p.append(nfunc)

                        ivalue[var][basin][nfunc] = df[(df['function'] == nfunc) &
                                                       (df['variable'] == var) &
                                                       (df['basin_id'] == int(bid)) &
                                                       (df['run_name'] == args['run_name'])]
                    else:
                        ivalue[var][basin][func] = df[(df['function'] == func) &
                                                      (df['variable'] == var) &
                                                      (df['basin_id'] == int(bid)) &
                                                      (df['run_name'] == args['run_name'])]

                        if ((var == cfg.plots_inputs_variables[0]) and
                                (basin == cfg.inputs_basins[0])):
                            p.append(func)

        args['inputs'] = ivalue
        args['inputs_methods'] = p
        args['var_list'] = cfg.plots_inputs_variables
        args['inputs_basins'] = cfg.inputs_basins

        inputs(args, cfg._logger)

    cfg.fig_names = fig_names


def save_fig(fig, paths):
    '''
    Args
    ----------
    fig : object
        matplotlib figure object
    paths : list
        list of paths to save figure

    '''

    if type(paths) != list:
        paths = [paths]

    for path in paths:
        fig.savefig(path)
