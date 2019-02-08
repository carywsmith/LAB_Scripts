#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
#
#    Module to robustly measure lab Sinistro temperatures from superfin.
#
# Rob Siverd
# Created:       2015-07-30
# Last modified: 2017-04-28
#--------------------------------------------------------------------------
#**************************************************************************
#--------------------------------------------------------------------------

## Current version:
__version__ = "0.3.1"

## Modules:
import os
import sys
#import time
import numpy as np
import superfin as sf
from collections import OrderedDict

## Adjust socket timeout:
sf.socket.setdefaulttimeout(180) # seconds

## TT controller config:
#nres_tt_IP = '172.16.4.8'
#nres_tt_IP = '172.16.4.148'
#tcontrol = sf.Superfin(nres_tt_IP)

## TT controller status parsing:
tconfig = OrderedDict()
tconfig[ '24v_I'] = ['analog_in',    0]
tconfig[ '12v_I'] = ['analog_in',    1]
tconfig[  '5v_I'] = ['analog_in',    2]
tconfig[ '28v_I'] = ['analog_in',    3]
tconfig[ '33v_I'] = ['analog_in',    4]
tconfig['cryo_p'] = ['analog_in',    7]
tconfig['outlet'] = ['analog_in',   12]
tconfig[ 'inlet'] = ['analog_in',   13]
tconfig[ 'ccd_h'] = ['analog_out',   0]
tconfig['cryo_T'] = ['analog_in_24', 1]
tconfig[ 'ccd_T'] = ['analog_in_24', 0]

## Nonsense values for simulated mode:
sim_vals = [-999.999 for x in tconfig.keys()]
sim_response = dict(zip(tconfig.keys(), sim_vals))

##--------------------------------------------------------------------------##
## Temperature-fetcher class:
class TFetch(object):

    # Initialize:
    def __init__(self, ip_address):
        if ip_address == None:
            self.ip_address = 'SIMULATE'
            self.simulate = True
            self._sfin = None
        else:
            self.ip_address = ip_address
            self.simulate = False
            self._sfin = sf.Superfin(self.ip_address)
        self._tconf = tconfig
        self.reset_temps()

    # Reset before/after temperatures:
    def reset(self):
        self.reset_temps()

    def reset_temps(self):
        self.t_list = []

    # -----------------------------------------------------
    # Temperatures before exposure:
    def query_temps(self, nstack=5):
        #self.t_list.append(self._medianize(self._get_statuses(), self._tconf))
        self.t_list.append(self.get_values(nstack))

    # Average of listed temperatures:
    def calc_exptemps(self):
        return self._calc_dict_avg(self.t_list)
        #return self._calc_dict_avg([self.temps_1, self.temps_2])

    # -----------------------------------------------------
    # One-time polling:
    def get_values(self, nstack=1):
        if self.simulate:
            return sim_response
        else:
            return self._medianize(self._get_statuses(nstack), self._tconf)

    # -----------------------------------------------------
    # Query superfin multiple times:
    def _get_statuses(self, iters=3):
        statuses = []
        for i in range(iters):
            statuses.append(self._sfin.status())
        return statuses

    # Return median of selected superfin status data:
    def _medianize(self, status_list, parse_conf):
        results = {}
        for key in parse_conf.keys():
            tree, idx = parse_conf[key]
            vec = np.array([x[tree][idx]['value'] for x in status_list])
            results[key] = np.median(vec)
        return results

    # Average two robust temperature sets:
    def _calc_dict_avg(self, dict_list):
        dict_keys = dict_list[0].keys()
        mean_vals = np.array([x.values() for x in dict_list]).mean(axis=0)
        #sys.stderr.write("mean_vals: %s\n" % mean_vals)
        return dict(zip(dict_keys, mean_vals))



######################################################################
# CHANGELOG (tfetch.py):
#---------------------------------------------------------------------
#
#  2017-04-28:
#     -- Increased __version__ to 0.3.1.
#     -- Added explicit 'SIMULATE' for TT ip address in simulate mode.
#
#  2017-04-13:
#     -- Increased __version__ to 0.3.0.
#     -- TFetch() now works in simulate mode (with nonsense values) when
#           the specified TT address is None.
#     -- query_temps() method now uses get_values to retrieve data.
#
#  2017-01-27:
#     -- Increased __version__ to 0.3.0.
#     -- Added 24V, 12V, 5V, and 3.3V to list of currents monitored.
#     -- Replaced xrange() with range() in _get_statuses() method.
#
#  2016-07-21:
#     -- Increased __version__ to 0.2.6.
#     -- Now __init__() accepts/expects a superfin IP address argument.
#
#  2015-08-10:
#     -- Increased __version__ to 0.2.5.
#     -- Now also track cryostat vacuum pressure, +28V power supply current,
#           and normalized heater power.
#
#  2015-07-30:
#     -- Increased __version__ to 0.2.0.
#     -- First created tfetch.py.
#
