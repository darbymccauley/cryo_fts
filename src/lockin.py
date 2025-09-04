import pyvisa
import time
import threading
import queue
import numpy as np

class LockinController:
    def __init__(self, gpib_address = 8, timeout = 3.0):
        """"
        Instantiate connection to SR865A lock-in amplifier via Prologix GPIB-USB controller.
        Inputs:
        gpib_address (int): GPIB address of SR865A (default = 8)
        timeout (float): time [s] to wait for response before raising a time-out error (default=3.0)
        """
        self.gpib_address = gpib_address
        self.timeout = timeout
        self.connection = None
        self.port = None
        self.device = None
        self.transmitting = False
        self.data_queue = queue.Queue()
        self._reading_thread = None
        self._stop_thread = threading.Event()

        #find and connect to Prologix controller
        rm = pyvisa.ResourceManager('@py')
        resources = rm.list_resources()

        for resource in resources:
            if 'ASRL' in resource or 'USB' in resource:
                try:
                    conn = rm.open_resource(resource)
                    conn.timeout = timeout * 1000
                    conn.write('++ver')
                    response = conn.read()
                    if 'Prologix' in response:
                        self.connection = conn
                        self.port = resource
                        print(f'Established connection to {self.device} on {self.port}')
                        break
                except Exception:
                    continue
                    
        if not self.connection:
            raise RuntimeError('Cannot connect to lock-in.')