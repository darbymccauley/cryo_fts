import os
import serial
import time
import threading
import queue
import numpy as np

class LockinController:
    def __init__(self, gpib_address = 8, baudrate=115200, timeout=1.0):
        """"
        Instantiate connection to SR865A lock-in amplifier via Prologix GPIB-USB controller.
        Inputs:
        gpib_address (int): GPIB address of SR865A (default = 8)
        baudrate (int): number of changes per second to the signal during transmission (default=115200)
        timeout (float): time [s] to wait for response before raising a time-out error (default=3.0)
        """
        self.gpib_address = gpib_address
        self.timeout = timeout
        self.port = None
        self.device = None
        self.connection = None
        self.transmitting = False
        self.data_queue = queue.Queue()
        self._reading_thread = None
        self._stop_thread = threading.Event()

        #find and connect to Prologix controller
        ports = [os.path.join('/dev', p) for p in os.listdir('/dev/') if p.startswith('tty.')]
        
        for port in ports:
            if 'Bluetooth' in port or 'BLTH' in port:
                continue
                
            try:
                print(f"Trying port: {port}")
                conn = serial.Serial(port, baudrate=baudrate, timeout=timeout)
                
                conn.reset_input_buffer()
                conn.reset_output_buffer()
                
                conn.write(b'++ver\r\n')
                time.sleep(0.1)
                response = conn.read(100).decode('utf-8', errors='ignore').strip()
                
                if 'Prologix' in response:
                    self.connection = conn
                    self.port = port
                    self.device = response
                    print(f'Established connection to Prologix controller: {response}')
                    print(f'Port: {self.port}')
                    break
                else:
                    conn.close()
                    
            except Exception as e:
                print(f"Failed on {port}: {e}") 
                continue
                
        if not self.connection:
            raise RuntimeError('Cannot connect to Prologix GPIB-USB controller. Check USB connection.')