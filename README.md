# Printed Part Data Pipeline

This repository contains a small synthetic 3D printer data pipeline. It generates extruded 3D letter samples, estimates deposited material, creates a mesh, maps the material to a polar grid, doubles the physical domain, and writes a Cartesian HDF5 file.

## Requirements

Install the Python dependencies with:

```bash
python3 -m pip install numpy scipy scikit-image h5py matplotlib
```

## Pipeline

### 1. Generate printer data

`diw.py` generates printer path data with the columns `x`, `y`, `z`, and `ink_flow`.

The supported logos are `LLNL`, `llnl`, and `Siemens`.

```bash
./diw.py PART-001 --logo Siemens -n 1000 -o diw.csv
```

The part number is used to make the generated data repeatable.

### 2. Estimate deposited material

`diw_post.py` loads the DIW script, resamples the path, and estimates material amount from ink flow and local path spacing.

```bash
./diw_post.py ./diw.py PART-001 2000 \
  --logo Siemens \
  --source-samples 1000 \
  -o polar.csv
```

The output CSV contains `r`, `theta`, `z`, and `material_amount`.

### 3. Create the engineering mesh

`engineering.py` converts polar coordinates to Cartesian coordinates, voxelizes the material field, extracts an isosurface mesh with marching cubes, and stores NumPy arrays, mesh vertices, and triangular faces in an `.npz` archive.

```bash
./engineering.py polar.csv -o mesh.npz
```

The archive contains `x`, `y`, `z`, `material_amount`, `vertices`, and `faces`.

### 4. Build the polar physics grid

`physics_pre.py` maps the engineering data to a 3D polar grid and applies a small, repeatable random modification.

```bash
./physics_pre.py mesh.npz \
  --radial 32 \
  --angular 64 \
  --vertical 32 \
  --noise 0.02 \
  --seed 0 \
  -o polar_grid.npz
```

### 5. Create the doubled Cartesian HDF5 grid

`physics.py` converts the polar grid to Cartesian coordinates and doubles the physical domain size.

```bash
./physics.py polar_grid.npz \
  --x-points 64 \
  --y-points 64 \
  --z-points 32 \
  -o physics.h5
```

The HDF5 file contains:

- `x`, `y`, `z`: one-dimensional Cartesian coordinate axes
- `density`: three-dimensional material amount field
- `grid_type`: `cartesian`
- `scale_factor`: `2.0`

## Release

The code of this site is released under the MIT License. For more details, see the [LICENSE](LICENSE) File.

LLNL-CODE-2027063

SPDX-License-Identifier: MIT

