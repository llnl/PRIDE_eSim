#!/usr/bin/env python3
"""Put engineering arrays on a 3D polar grid with small random perturbations."""

from __future__ import annotations

import argparse

import numpy as np


def build_polar_grid(input_npz: str, radial: int, angular: int, vertical: int,
                     noise: float, seed: int, support_radius: float = 0.18):
    source = np.load(input_npz)
    amount_name = "material_amount" if "material_amount" in source else "density"
    for name in ("x", "y", "z", amount_name):
        if name not in source:
            raise ValueError(f"input archive must contain {name}")
    x, y, z, density = (np.asarray(source[name], dtype=float).ravel() for name in ("x", "y", "z", amount_name))
    if not (len(x) == len(y) == len(z) == len(density) and len(x) > 0):
        raise ValueError("x, y, z, and density must be non-empty arrays of equal length")
    if min(radial, angular, vertical) < 1:
        raise ValueError("grid dimensions must be positive")

    radii = np.linspace(0.0, max(np.hypot(x, y).max(), 1e-12), radial)
    angles = np.linspace(0.0, 2.0 * np.pi, angular, endpoint=False)
    heights = np.linspace(z.min(), z.max() if z.max() > z.min() else z.min() + 1e-12, vertical)
    radius, theta, height = np.meshgrid(radii, angles, heights, indexing="ij")
    if all(name in source for name in ("field", "grid_x", "grid_y", "grid_z")):
        # Transform the engineering Cartesian volume into cylindrical
        # coordinates. This preserves the actual printed shape.
        grid_x, grid_y, grid_z = (np.asarray(source[name]) for name in ("grid_x", "grid_y", "grid_z"))
        target_x = radius * np.cos(theta)
        target_y = radius * np.sin(theta)
        ix_raw = np.searchsorted(grid_x, target_x, side="left")
        iy_raw = np.searchsorted(grid_y, target_y, side="left")
        iz_raw = np.searchsorted(grid_z, height, side="left")
        ix = np.clip(ix_raw, 0, len(grid_x) - 1)
        iy = np.clip(iy_raw, 0, len(grid_y) - 1)
        iz = np.clip(iz_raw, 0, len(grid_z) - 1)
        values = np.asarray(source["field"])[ix, iy, iz]
        outside = ((ix_raw >= len(grid_x)) | (iy_raw >= len(grid_y)) |
                   (iz_raw >= len(grid_z)))
        values = np.where(outside, 0.0, values)
    else:
        # Fallback for older engineering archives without a Cartesian field.
        src = np.column_stack((np.hypot(x, y), np.mod(np.arctan2(y, x), 2 * np.pi), z))
        dst = np.column_stack((radius.ravel(), theta.ravel(), height.ravel()))
        angular_distance = np.abs(src[:, 1, None] - dst[:, 1])
        angular_distance = np.minimum(angular_distance, 2 * np.pi - angular_distance)
        distance = ((src[:, 0, None] - dst[:, 0]) / max(radii[-1], 1e-12)) ** 2
        distance += (angular_distance / np.pi) ** 2 + ((src[:, 2, None] - dst[:, 2]) / max(np.ptp(heights), 1e-12)) ** 2
        nearest = np.argmin(distance, axis=0)
        nearest_distance = distance[nearest, np.arange(distance.shape[1])]
        values = np.where(nearest_distance <= support_radius,
                          density[nearest], 0.0).reshape(radius.shape)
    rng = np.random.default_rng(seed)
    values = np.clip(values * (1.0 + rng.normal(0.0, noise, values.shape)), 0.0, None)
    return radius, theta, height, values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_npz")
    parser.add_argument("-o", "--output", default="polar_grid.npz")
    parser.add_argument("--radial", type=int, default=32)
    parser.add_argument("--angular", type=int, default=64)
    parser.add_argument("--vertical", type=int, default=32)
    parser.add_argument("--noise", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--support-radius", type=float, default=0.18,
                        help="normalized distance around printer samples that contains material")
    args = parser.parse_args()
    result = build_polar_grid(args.input_npz, args.radial, args.angular, args.vertical,
                              args.noise, args.seed, args.support_radius)
    source = np.load(args.input_npz)
    amount_name = "material_amount" if "material_amount" in source else "density"
    np.savez_compressed(args.output, radius=result[0], theta=result[1], z=result[2], density=result[3],
                        source_x=np.asarray(source["x"]), source_y=np.asarray(source["y"]),
                        source_z=np.asarray(source["z"]), source_amount=np.asarray(source[amount_name]))


if __name__ == "__main__":
    main()
