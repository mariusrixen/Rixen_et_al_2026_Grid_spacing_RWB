import numpy as np
import xarray as xr
import sys
import re
from datetime import datetime, timedelta

def parse_reference_time(filename):
    """Try to extract reference time from filename (e.g., trajectory_fwd_20200213_1200)."""
    match = re.search(r'(\d{8}_\d{4})', filename)
    if match:
        return datetime.strptime(match.group(1), "%Y%m%d_%H%M")
    else:
        return None

def parse_trajectory_file(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()

    trajectories = []
    current_traj = []

    for line in lines:
        stripped = line.strip()

        if stripped == "":
            if current_traj:
                trajectories.append(current_traj)
                current_traj = []
            continue
        if any(s in stripped for s in ["Reference", "lon", "---", "time", "lat", "z"]):
            continue

        try:
            # Expecting: time lon lat z u v w u v w geopot rlon rlat pressure
            values = [float(x) for x in stripped.split()]
            current_traj.append(values)
        except ValueError:
            print(f"⚠️ Warning: Skipping line due to parse error:\n{line.strip()}")
            continue

    if current_traj:
        trajectories.append(current_traj)

    return trajectories

def main(input_file, output_file):
    traj_data = parse_trajectory_file(input_file)
    ref_time = parse_reference_time(input_file)

    ntraj = len(traj_data)
    maxt = max(len(t) for t in traj_data)

    # Arrays
    time_rel = np.full((ntraj, maxt), np.nan)
    time_abs = np.full((ntraj, maxt), np.datetime64("NaT", "s"), dtype="datetime64[s]")
    lon     = np.full((ntraj, maxt), np.nan)
    lat     = np.full((ntraj, maxt), np.nan)
    z       = np.full((ntraj, maxt), np.nan)
    u       = np.full((ntraj, maxt), np.nan)
    v       = np.full((ntraj, maxt), np.nan)
    w       = np.full((ntraj, maxt), np.nan)
    pv      = np.full((ntraj, maxt), np.nan)
    u_tr    = np.full((ntraj, maxt), np.nan)
    v_tr    = np.full((ntraj, maxt), np.nan)
    w_tr    = np.full((ntraj, maxt), np.nan)
    geopot  = np.full((ntraj, maxt), np.nan)
    rlon    = np.full((ntraj, maxt), np.nan)
    rlat    = np.full((ntraj, maxt), np.nan)
    pressure= np.full((ntraj, maxt), np.nan)
    temp    = np.full((ntraj, maxt), np.nan)

    for i, traj in enumerate(traj_data):
        for j, entry in enumerate(traj):
            (
                t,
                lon[i, j], lat[i, j], z[i, j],
                u[i, j], v[i, j], w[i, j], pv[i, j],
                u_tr[i, j], v_tr[i, j], w_tr[i, j],
                geopot[i, j], rlon[i, j], rlat[i, j], pressure[i, j], temp[i, j]
            ) = entry

            time_rel[i, j] = t
            if ref_time:
                py_dt = ref_time + timedelta(hours=t)
                time_abs[i, j] = np.datetime64(py_dt, "s")

    ds = xr.Dataset(
        {
            "time_rel": (("trajectory", "time"), time_rel),
            "time_abs": (("trajectory", "time"), time_abs),
            "lon":      (("trajectory", "time"), lon),
            "lat":      (("trajectory", "time"), lat),
            "z":        (("trajectory", "time"), z),
            "u":        (("trajectory", "time"), u),
            "v":        (("trajectory", "time"), v),
            "w":        (("trajectory", "time"), w),
            "pv":       (("trajectory", "time"), pv),
            "u_tr":     (("trajectory", "time"), u_tr),
            "v_tr":     (("trajectory", "time"), v_tr),
            "w_tr":     (("trajectory", "time"), w_tr),
            "geopot":   (("trajectory", "time"), geopot),
            "rlon":     (("trajectory", "time"), rlon),
            "rlat":     (("trajectory", "time"), rlat),
            "pressure": (("trajectory", "time"), pressure),
            "temp":     (("trajectory", "time"), temp)
        },
        coords={
            "trajectory": np.arange(ntraj),
            "time": np.arange(maxt),
        },
        attrs={
            "reference_time": str(ref_time) if ref_time else "unknown"
        }
    )

    ds.to_netcdf(output_file)
    print(f"✅ NetCDF saved to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_trajectory_to_nc_Lagranto.py <input_ascii_file> <output_nc_file>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
