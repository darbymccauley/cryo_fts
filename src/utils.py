### Functions of utility for informing observing runs with the mirror module ###

import numpy as np
import astropy.units as u 
from astropy.constants import c

def calc_nyquist(freq_max):
    """Calculate Nyquist criterion."""
    return 2 * freq_max

def calc_delta_opd(freq_max):
    """Calculate the optical path difference resolution."""
    delta = c / (2 * freq_max)
    return delta.to(u.mm)

def calc_mirror_velocity(samp_rate, freq_max, N=1):
    """Calculate the mirror velocity required for Nyquist sampling."""
    v = (freq_max * samp_rate) / (4 * N)
    return v.to(u.mm/u.s)

def calc_fringe_freq(samp_rate):
    """Calculate the fringe frequency."""
    return samp_rate / 2

def calc_scan_time(track_length, mirror_velocity):
    """Calculate time to scan track."""
    t = track_length / mirror_velocity
    return t.to(u.s)