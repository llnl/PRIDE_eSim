# PRIDE eSim

PRIDE eSim is a Python package for generating synthetic 3D printer samples and
converting them into engineering meshes, polar grids, and Cartesian HDF5 data.
It installs five command-line executables, one for each pipeline stage.

## Install

Install the package and its runtime dependencies from this checkout:

```bash
python3 -m pip install .
```

The package requires Python 3.10 or newer. Its dependencies are NumPy, SciPy,
scikit-image, h5py, and Matplotlib. NumPy is used throughout; Matplotlib's
text-path tools generate the logos; SciPy and scikit-image build the mesh; and
SciPy and h5py create the final HDF5 grid.

## Pipeline

Run the commands below in order. Each executable accepts `--help` for its full
set of options.

### 1. Generate printer data

`pride-esim-diw` writes a CSV with `x`, `y`, `z`, and `ink_flow` columns. The
part number makes generated data repeatable. Supported logos are `LLNL`,
`llnl`, and `Siemens`.

```bash
pride-esim-diw --part_number PART-001 --logo Siemens --samples 1000 --output diw.csv
```

### 2. Estimate deposited material

`pride-esim-diw-post` reads the printer-data CSV, resamples the path, and
estimates material amount from ink flow and local path spacing. The output CSV
contains `r`, `theta`, `z`, and `material_amount` columns.

```bash
pride-esim-diw-post --input_csv diw.csv --points 2000 --output polar.csv
```

### 3. Create the engineering mesh

`pride-esim-engineering` converts polar coordinates to Cartesian coordinates,
voxelizes the material field, extracts an isosurface mesh, and saves the arrays,
mesh vertices, and triangular faces in an `.npz` archive.

```bash
pride-esim-engineering --polar_csv polar.csv --output mesh.npz
```

### 4. Build the polar physics grid

`pride-esim-physics-pre` maps the engineering data to a 3D polar grid and
applies a repeatable random modification.

```bash
pride-esim-physics-pre --input_npz mesh.npz \
  --radial 32 \
  --angular 64 \
  --vertical 32 \
  --noise 0.02 \
  --seed 0 \
  --output polar_grid.npz
```

### 5. Create the Cartesian HDF5 grid

`pride-esim-physics` converts the polar grid to Cartesian coordinates and
doubles the physical scale of the part.

```bash
pride-esim-physics --polar_grid_npz polar_grid.npz \
  --x_points 64 \
  --y_points 64 \
  --z_points 32 \
  --output physics.h5
```

The HDF5 file contains one-dimensional `x`, `y`, and `z` coordinate axes, a
three-dimensional `density` field, and the `grid_type` and `scale_factor`
attributes.

## License

The package is distributed under the MIT License. See [LICENSE](LICENSE) and
[NOTICE](NOTICE) for details. LLNL code release identifier: LLNL-CODE-2027063.

