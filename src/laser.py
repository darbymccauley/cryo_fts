from toptica.lasersdk.client import Client, SerialConnection
import time

class TopticaController:
    def __init__(self, port='COM6', verbose=False):
        self.port = port
        self.verbose = verbose
        self.client = client(SerialConnection(port))
        self.client.__enter__() # ensure connection to Toptica via USB connection established
        self.dlc = self.client.get('general:system-type')
        self.user_level = self.client.get('ul')
        if verbose:
            print(f'Connected to {self.dlc}')

    def close(self):
        self.client.close()
        return True
    
    def emission_on(self):
        pass

    def emission_off(self):
        pass

    def set_frequency(self, freq_GHz):
        self.client.set('frequency:frequency-set', freq_GHz)
        time.sleep(2) # allow time to settle
        if self.verbose:
            return True
        
    def get_frequency(self):
        freq = self.client.get('frequency:frequency-act')
        return freq # GHz
    
    def init_lockin(self, freq_hz, int_time_ms, amp_gain, phase_deg): # actually don't think we need to do something like this, should set up in GUI (?)
        self.client.set('lockin:frequency', freq_hz)
        self.client.set('lockin:integration-time', int_time_ms)
        self.client.set('lockin:amplifier-gain', amp_gain) # in command reference what level we should be using
        self.client.set('lockin:phase', phase_deg)

    def get_lockin_value(self):
        self.client.exec('lockin:lock-in-reset')
        time.sleep(1) # should correspond to lock-in integration time, just throwing in 1 sec as placeholder for now
        lockin_value = self.client.get('lockin:lock-in-value')
        return lockin_value
    
    

    

    