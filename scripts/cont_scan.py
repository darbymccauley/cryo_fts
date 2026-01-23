from cryo_fts.mirror import MirrorController
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--velocity', help='Magnitude of scan velocity', default=None)
parser.add_argument('--units', help='Units of scan velocity', default=None)
parser.add_argument('--csv_file', help='Where to save collected data', required=True)

args = parser.parse_args()
VEL = float(args.velocity) if args.velocity is not None else None
UNITS = str(args.units) if args.units is not None else None
CSV = str(args.csv_file) if args.csv_file is not None else None

fts = MirrorController()
fts.init()
# AXIS_MAX = fts.motor.AXIS_MAX
# fts.move_absolute(0, 'mm')

# fts.scan_and_collect(velocity=VEL, velocity_unit=UNITS, save_to_csv=CSV)

# if np.allclose(AXIS_MAX, fts.get_position(), rtol=1e-2):
#     fts.stop_scan()