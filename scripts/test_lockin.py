from cryo_fts.lockin import LockInController
import numpy as np

lockin = LockInController()
lockin.init()

NSTEPS = 10
NSAMPS = 10

data = []
try:
    for n in range(NSTEPS):
        d = lockin.record(N=NSAMPS)
        data.append(d)
        print(f'Count: {n}')
    data = np.vstack(data)
    db = {
        'NINT': NSAMPS,
        'NSTEPS': NSTEPS,
        'X_V': data[:, 0],
        'Y_V': data[:, 1],
        'R_V': data[:, 2],
        'THETA_deg': data[:, 3]
    }
    np.savez('data/test_lockin_vf01.npz', **db)
finally:
    lockin.close()