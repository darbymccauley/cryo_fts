import sys
import os
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
from mirror import MirrorController
from encoder import EncoderController
from motor import MotorController

parser = argparse.ArgumentParser()
parser.add_argument('--velocity', help='Magnitude of scan velocity', default=None)
parser.add_argument('--units', help='Units of scan velocity', default=None)
parser.add_argument('--csv_file', help='Where to save collected data', default = None)

args = parser.parse_args()
VEL = float(args.velocity) if args.velocity is not None else None
UNITS = str(args.units) if args.units is not None else None
CSV = str(args.csv_file) if args.csv_file is not None else None

fts = MirrorController()
fts.init()
print("Moving to start position")
fts.move_absolute(0, 'mm')
print(f"Scanning at velocity = {VEL} {UNITS}")
fts.scan_and_collect(velocity=VEL, velocity_unit=UNITS, save_to_csv=CSV)
while fts._scan_thread and fts._scan_thread.is_alive():
    fts._scan_thread.join(timeout=0.5)

fts.stop_scan()
fts.close()
print("Scan done")