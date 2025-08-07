import os
import serial
import time

class EncoderController:
    def __init__(self, baudrate=9600, timeout=0.1):
        self.port = None
        self.device = None
        self.connection = None
        self.transmitting = False

        ports = [os.path.join('/dev', port) for port in os.listdir('/dev/') if port.startswith('tty.')]
        for port in ports:
            try:
                conn = serial.Serial(port, baudrate=baudrate, timeout=timeout, rtscts=True)
                conn.write(b'v')
                response = conn.readall()
                try:
                    device = response.decode('utf-8').strip()
                except UnicodeDecodeError:
                    continue
                if not device:
                    conn.close()
                    continue
                self.device = device
                self.port = port
                self.connection = conn
                print(f'Established connection to {self.device} on {self.port}')
                break
            except Exception as e:
                continue
        if not self.device:
            raise RuntimeError('Cannot connect to encoder.')
        
    def init(self):
        cmds = [
            'B26/r' # set bit-length to 26
        ]
        for cmd in cmds:
            self.write(cmd, read=False)
        return True

    def close(self):
        if self.transmitting:
            self.stop_transmission()
        if self.connection and self.connection.is_open:
            self.connection.close()
        return True
    
    def write(self, cmd, encode_to='ascii', read=False, decode_to='utf-8', timeout=2.0):
        while self.connection.in_waiting:
            self.connection.read(self.connection.in_waiting)
        self.connection.write(cmd.encode(encode_to))
        if read:
            return self.read(decode_to, timeout)

    def read(self, decode_to='utf-8', timeout=2.0):
        if self.transmitting:
            raise ValueError('Cannot read while actively transmitting. Turn off continuous transmission first.')
        t0 = time.time()
        while True:
            rsp = self.connection.readall().strip()
            if rsp:
                try:
                    return rsp.decode(decode_to)
                except UnicodeDecodeError as e:
                    raise RuntimeError(f'Failed to decode response: {rsp} ({e})')
            if time.time() - t0 > timeout:
                raise TimeoutError('No response received from the encoder.')
    
    def get_count(self):
        if self.transmitting:
            rsp = self.connection.read(9)
        else:
            rsp = self.write('?', read=True)
        return int(rsp)
    
    def start_transmission(self):
        if self.transmitting:
            return True
        self.write('1')
        self.transmitting = True
        return True
    
    def stop_transmission(self):
        if not self.transmitting:
            return True
        self.write('0')
        self.transmitting = False
        return True
