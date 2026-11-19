#!/usr/bin/env python3
"""Double the printed-part domain and write it as an HDF5 Cartesian grid."""

from __future__ import annotations

import argparse

import h5py
import numpy as np
from scipy.ndimage import gaussian_filter


def write_cartesian_hdf5(input_npz: str, output: str, x_points: int, y_points: int,
                         z_points: int, smoothing: float) -> None:
    source = np.load(input_npz)
    radius = np.asarray(source["radius"])
    theta = np.asarray(source["theta"])
    z = np.asarray(source["z"])
    density = np.asarray(source["density"])
    if not (radius.shape == theta.shape == z.shape == density.shape):
        raise ValueError("radius, theta, z, and density must have the same shape")
    if radius.ndim != 3 or radius.shape != theta.shape or radius.shape != z.shape:
        raise ValueError("polar grid arrays must be matching 3D arrays")
    radial_axis = radius[:, 0, 0]
    angular_axis = np.mod(theta[0, :, 0], 2 * np.pi)
    z_source_axis = z[0, 0, :]
    scale = 2.0
    if all(name in source for name in ("source_x", "source_y", "source_z", "source_amount")):
        # Scale the part itself by 2x and rasterize it on a tight grid.
        source_x = scale * np.asarray(source["source_x"])
        source_y = scale * np.asarray(source["source_y"])
        source_z = scale * np.asarray(source["source_z"])
        padding = 0.6 * scale
        x_axis = np.linspace(source_x.min() - padding, source_x.max() + padding, x_points)
        y_axis = np.linspace(source_y.min() - padding, source_y.max() + padding, y_points)
        z_axis = np.linspace(source_z.min() - padding, source_z.max() + padding, z_points)
        values = np.zeros((x_points, y_points, z_points), dtype=float)
        ix = np.clip(np.rint((source_x - x_axis[0]) / np.ptp(x_axis) * (x_points - 1)).astype(int), 0, x_points - 1)
        iy = np.clip(np.rint((source_y - y_axis[0]) / np.ptp(y_axis) * (y_points - 1)).astype(int), 0, y_points - 1)
        iz = np.clip(np.rint((source_z - z_axis[0]) / np.ptp(z_axis) * (z_points - 1)).astype(int), 0, z_points - 1)
        np.maximum.at(values, (ix, iy, iz), 1.0)
        values = gaussian_filter(values, sigma=(smoothing, smoothing, max(1.5 * smoothing, 1.0)))
    else:
        x_axis = np.linspace(-scale * float(radial_axis.max()), scale * float(radial_axis.max()), x_points)
        y_axis = np.linspace(-scale * float(radial_axis.max()), scale * float(radial_axis.max()), y_points)
        z_axis = np.linspace(float(z.min()), float(z.min()) + scale * float(np.ptp(z)), z_points)
        x, y, zz = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
        target_radius = np.hypot(x, y)
        target_theta = np.mod(np.arctan2(y, x), 2 * np.pi)
        radial_index_raw = np.searchsorted(radial_axis, target_radius, side="left")
        radial_index = np.clip(radial_index_raw, 0, len(radial_axis) - 1)
        theta_index = np.mod(np.rint(target_theta / (2 * np.pi) * len(angular_axis)).astype(int), len(angular_axis))
        z_index_raw = np.searchsorted(z_source_axis, zz, side="left")
        z_index = np.clip(z_index_raw, 0, len(z_source_axis) - 1)
        values = density[radial_index, theta_index, z_index]
        values[(radial_index_raw >= len(radial_axis)) | (z_index_raw >= len(z_source_axis))] = 0.0
    with h5py.File(output, "w") as h5:
        h5.create_dataset("x", data=x_axis)
        h5.create_dataset("y", data=y_axis)
        h5.create_dataset("z", data=z_axis)
        h5.create_dataset("density", data=values, compression="gzip")
        h5.attrs["grid_type"] = "cartesian"
        h5.attrs["scale_factor"] = scale


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("polar_grid_npz")
    parser.add_argument("-o", "--output", default="physics.h5")
    parser.add_argument("--x-points", type=int, default=64)
    parser.add_argument("--y-points", type=int, default=64)
    parser.add_argument("--z-points", type=int, default=32)
    parser.add_argument("--smoothing", type=float, default=2.0)
    args = parser.parse_args()
    write_cartesian_hdf5(args.polar_grid_npz, args.output, args.x_points, args.y_points,
                         args.z_points, args.smoothing)


if __name__ == "__main__":
    main()
