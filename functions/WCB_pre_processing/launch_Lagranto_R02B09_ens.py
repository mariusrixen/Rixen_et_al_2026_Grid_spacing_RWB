import subprocess
import os
import xarray as xr
import numpy as np
import glob
import re

# ens number
ens = os.environ.get("ENS_NUM_PADDED", "007")  # default for testing

# list of reference times
ref_times = [
    "20200212_0000",
    "20200212_0600",
    "20200212_1200",
    "20200212_1800",
    "20200213_0000"
]

prog = "/highres_nobackup/mrixen/lagranto.icon.fortran/"
work_dir = "/highres_nobackup/mrixen/simulations/Dennis_v1/R02B09/Lagranto_ens"
data_dir = "/highres_nobackup/mrixen/simulations/Dennis_v1/R02B09/Ensembles_IC_perturb/Lagranto"
converter = "/home/mrixen/Tools/Lagranto_tools/convert_trajectory_to_nc_Lagranto_tracing.py"

combined_out_dir = "/home/mrixen/Case_studies/Clean_code/TEST_REMAPCON/output_Lagranto"
os.makedirs(combined_out_dir, exist_ok=True)
combined_file = os.path.join(combined_out_dir, f"trajectories_R02B09_ens{ens}_remapcon.nc")

# === Step 1: Create symlinks to input data ===
print("\n=== Linking ensemble data files ===")
# Patterns: out6 → S..., out7 → P...
patterns = [
    (f"{ens}_out6_*_regridded_ERA.nc", "S"),
    (f"{ens}_out7_*_regridded_ERA_remapcon.nc", "P"),
]
for pattern_str, prefix in patterns:
    pattern = os.path.join(
        data_dir, f"Dennis_ensemble_R02B09_IC_{pattern_str}"
    )
    src_files = glob.glob(pattern)
    if not src_files:
        print(f"⚠️ No files found for pattern {pattern}")
        continue

    for src in sorted(src_files):
        basename = os.path.basename(src)

        # Extract 8-digit date before 'T000000Z' (like in your Bash)
        m = re.search(r"(\d{8})(?=T000000Z)", basename)
        if not m:
            print(f"❌ Could not extract date from {basename}, skipping.")
            continue
        date = m.group(1)

        # Construct link name exactly like your Bash: SYYYYMMDD or PYYYYMMDD
        link_name = os.path.join(work_dir, f"{prefix}{date}")

        # Create or replace symlink
        if os.path.islink(link_name) or os.path.exists(link_name):
            os.remove(link_name)
        os.symlink(src, link_name)
        print(f"Linked {src} → {link_name}")

print("✅ All data symlinks created.\n")


datasets = []

for ref in ref_times:
    print(f"\n=== Processing reference time {ref} ===")
    out_file = f"trajectory_fwd_{ref}"
    ascii_file = os.path.join(work_dir, out_file)  # output of caltra
    traced_file = os.path.join(work_dir, f"{out_file}_trace")  # output of trace
    nc_file = os.path.join(work_dir, f"{out_file}.nc")

    # === Run Lagranto (caltra) only if ASCII file does not exist ===
    if not os.path.exists(ascii_file):
        print(f"Running Lagranto caltra for {ref}")
        # Temporarily link the correct tracevars file
        src_vars = os.path.join(work_dir, "tracevars_caltra")
        dst_vars = os.path.join(work_dir, "tracevars")
        if os.path.exists(dst_vars):
            os.remove(dst_vars)
        os.symlink(src_vars, dst_vars)

        caltra_cmd = f"{prog}/caltra/caltra /home/mrixen/Tools/Lagranto_tools/startf 48 {out_file} -ref {ref} -i 60 -ts 5 -o 60"
        subprocess.run(
            ["/bin/csh", "-c", f"module load dyn_tools; {caltra_cmd}"],
            cwd=work_dir,
            check=True,
        )

        # Clean up
        os.remove(dst_vars)
    else:
        print(f"Skipping caltra for {ref} (file already exists)")

    # === Run Lagranto trace step ===
    if not os.path.exists(traced_file):
        print(f"Running Lagranto trace for {ref}")
        # Temporarily link the correct tracevars file
        src_vars = os.path.join(work_dir, "tracevars_tracing")
        dst_vars = os.path.join(work_dir, "tracevars")
        if os.path.exists(dst_vars):
            os.remove(dst_vars)
        os.symlink(src_vars, dst_vars)

        trace_cmd = f"{prog}/trace/trace {out_file} {out_file}_trace -i 180"
        subprocess.run(
            ["/bin/csh", "-c", f"module load dyn_tools; {trace_cmd}"],
            cwd=work_dir,
            check=True,
        )
        
        # Clean up
        os.remove(dst_vars)
    else:
        print(f"Skipping trace for {ref} (file already exists)")

    # === Convert traced file to NetCDF ===
    if not os.path.exists(nc_file):
        print(f"Converting traced file {out_file}_trace to NetCDF...")
        subprocess.run(
            ["python3", converter, f"{out_file}_trace", nc_file],
            cwd=work_dir,
            check=True,
        )
    else:
        print(f"Skipping conversion for {out_file} (NetCDF already exists)")

    # Open dataset
    ds = xr.open_dataset(nc_file)

    # Ensure time_abs is a coordinate
    if "time_abs" not in ds.coords:
        ds = ds.assign_coords(time_abs=(("trajectory", "time"), ds["time_abs"].data))

    datasets.append(ds)

# === Combine datasets along a common time_abs axis ===
all_times = np.unique(np.concatenate([ds.time_abs.values.ravel() for ds in datasets]))

reindexed_datasets = []
for ds in datasets:
    reindexed_datasets.append(ds.reindex({"time_abs": all_times}))

ds_combined = xr.concat(reindexed_datasets, dim="trajectory")
ds_combined.to_netcdf(combined_file)
print(f"\n✅ Combined NetCDF saved to: {combined_file}")


# === Final step: Clean up working directory ===
print("\n=== Cleaning up working directory ===")

# Files/folders to keep
keep_files = {"tracevars_caltra", "tracevars_tracing"}

for item in os.listdir(work_dir):
    item_path = os.path.join(work_dir, item)
    if item in keep_files:
        continue
    try:
        if os.path.isdir(item_path) and not os.path.islink(item_path):
            # remove entire directory tree
            import shutil
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
        print(f"Deleted: {item}")
    except Exception as e:
        print(f"⚠️ Could not delete {item}: {e}")

print("✅ Cleanup complete.\n")