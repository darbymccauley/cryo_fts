import numpy as np
import astropy.units as u

def absorption_coefficient(kappa, wavelength):
    wavelength = wavelength.to(u.cm)
    return (4 * np.pi * kappa) / wavelength

def extinction_coefficient(alpha, wavelength):
    alpha = alpha.to(1/u.cm)
    wavelength = wavelength.to(u.cm)
    return (alpha * wavelength) / (4 * np.pi)

class Fresnel:
    def __init__(self, n1, n2, theta_i, kappa=None):
        self.n1 = n1
        self.theta_i = theta_i.to(u.radian)
        if kappa is not None:
            self.n2 = n2 + 1j * kappa.value
        else:
            self.n2 = n2
        self.kappa = kappa
        self.cos_i = np.cos(self.theta_i.value)
        self.theta_t = np.arcsin( (self.n1 / self.n2) * np.sin(self.theta_i.value) )
        self.cos_t = np.cos(self.theta_t)

    def amplitude_coefficients(self):
        rs = (self.n1 * self.cos_i - self.n2 * self.cos_t) / (self.n1 * self.cos_i + self.n2 * self.cos_t)
        rp = (self.n2 * self.cos_i - self.n1 * self.cos_t) / (self.n2 * self.cos_i + self.n1 * self.cos_t)
        ts = (2 * self.n1 * self.cos_i) / (self.n1 * self.cos_i + self.n2 * self.cos_t)
        tp = (2 * self.n1 * self.cos_i) / (self.n2 * self.cos_i + self.n1 * self.cos_t)
        return {'rs': rs, 'rp': rp, 'ts': ts, 'tp': tp}
        
    def power_coefficients(self):
        amps = self.amplitude_coefficients()
        Rs = np.abs(amps['rs'])**2
        Rp = np.abs(amps['rp'])**2
        Ts = (self.n2 * self.cos_t * np.abs(amps['ts'])**2) / (self.n1 * self.cos_i)
        Tp = (self.n2 * self.cos_t * np.abs(amps['tp'])**2) / (self.n1 * self.cos_i)
        return {'Rs': Rs, 'Rp': Rp, 'Ts': Ts, 'Tp': Tp}

    @staticmethod
    def effective_power(S, P):
        return (S + P) / 2

class BeamSplitter(Fresnel):
    def __init__(self, n1, n2, theta_i, thickness, sigma, kappa=None):
        super().__init__(n1, n2, theta_i, kappa)
        self.thickness = thickness.to(u.cm)
        self.sigma = sigma.to(1/u.cm)
        self.phase = 2 * np.pi * self.n2 * self.sigma.value * self.thickness.value * self.cos_t

    def double_beam_amplitude_coefficients(self):
        amps = self.amplitude_coefficients()
        rs_prime = -amps['rs']
        rp_prime = -amps['rp']
        ts_prime = (2 * self.n2 * self.cos_t) / (self.n2 * self.cos_t + self.n1 * self.cos_i)
        tp_prime = (2 * self.n2 * self.cos_t) / (self.n2 * self.cos_i + self.n1 * self.cos_t)
        return {'rs_prime': rs_prime, 'rp_prime': rp_prime, 'ts_prime': ts_prime, 'tp_prime': tp_prime}
    
    def double_beam_power_coefficients(self):
        amps = self.amplitude_coefficients()
        prime_amps = self.double_beam_amplitude_coefficients()
        Rs = np.abs(amps['rs'])**2 
        Rp = np.abs(amps['rp'])**2
        Ts = amps['ts'] * prime_amps['ts_prime']
        Tp = amps['tp'] * prime_amps['tp_prime']
        return {'Rs': Rs, 'Rp': Rp, 'Ts': Ts, 'Tp': Tp}
    
    def multibeam_power_coefficients(self):
        amps = self.amplitude_coefficients()
        prime_amps = self.double_beam_amplitude_coefficients()
        denom_s = 1 - amps['rs']**2 * np.exp(2j * self.phase)
        denom_p = 1 - amps['rp']**2 * np.exp(2j * self.phase)
        Rs = np.abs( amps['rs'] * (1 - np.exp(2j * self.phase)) / denom_s )**2
        Rp = np.abs( amps['rp'] * (1 - np.exp(2j * self.phase)) / denom_p )**2
        Ts = np.abs( (amps['ts'] * prime_amps['ts_prime']) * np.exp(1j * self.phase) / denom_s )**2 
        Tp = np.abs( (amps['tp'] * prime_amps['tp_prime']) * np.exp(1j * self.phase) / denom_p )**2 
        return {'Rs': Rs, 'Rp': Rp, 'Ts': Ts, 'Tp': Tp}
    
    @staticmethod
    def _beamsplitter_efficiency(R, T):
        return 4 * R * T
    
    def beamsplitter_efficiency(self):
        mb = self.multibeam_power_coefficients()
        Es = self._beamsplitter_efficiency(mb['Rs'], mb['Ts'])
        Ep = self._beamsplitter_efficiency(mb['Rp'], mb['Tp'])
        E_avg = self.effective_power(Es, Ep)
        return {'Es': Es, 'Ep': Ep, 'E_avg': E_avg}
    
    def evaluate(self):
        mb = self.multibeam_power_coefficients()
        eff = self.beamsplitter_efficiency()
        return {
            'Rs': mb['Rs'], 'Rp': mb['Rp'], 'R_avg': self.effective_power(mb['Rs'], mb['Rp']),
            'Ts': mb['Ts'], 'Tp': mb['Tp'], 'T_avg': self.effective_power(mb['Ts'], mb['Tp']),
            'Es': eff['Es'], 'Ep': eff['Ep'], 'E_avg': eff['E_avg']
            }