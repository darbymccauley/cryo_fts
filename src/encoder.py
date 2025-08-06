import os
import serial

class EncoderController:
    def __init__(self, baudrate=9600, timeout=0.1):
        self.port = None
        self.device = None
        self.connection = None

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
            'B26/r'
        ]
        for cmd in cmds:
            self.write(cmd)
        self.connection.reset_input_buffer()
        return True

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
        return True
    
    def write(self, cmd, encode_to='ascii', read=False, decode_to='utf-8'):
        self.connection.reset_input_buffer()
        cmd = cmd.encode(encode_to)
        self.connection.write(cmd)
        if read:
            return self.read(decode_to)

    def read(self, decode_to='utf-8'):
        rsp = self.connection.readall().strip().decode(decode_to)
        return rsp
    
    def get_count(self):
        self.write('?')
        rsp = self.read()
        return int(rsp)
