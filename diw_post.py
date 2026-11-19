#!/usr/bin/env python3
"""Convert printer path samples into cylindrical material-amount samples."""

from __future__ import annotations

import argparse
import csv
import importlib.util
from pathlib import Path

import numpy as np


def load_diw_module(script: str):
    spec = importlib.util.spec_from_file_location("diw_input", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load DIW script: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "generate_diw_data"):
        raise AttributeError(f"{script} must define generate_diw_data")
    return module


def generate_polar_density(diw_data: np.ndarray, points: int) -> np.ndarray:
    """Resample path data and return r, theta, z, and material amount."""
    if points < 1:
        raise ValueError("points must be positive")
    if diw_data.ndim != 2 or diw_data.shape[1] < 4 or len(diw_data) < 1:
        raise ValueError("DIW data must have x, y, z, ink_flow columns")

    source = np.linspace(0.0, 1.0, len(diw_data))
    target = np.linspace(0.0, 1.0, points)
    # Resample in Cartesian space first. Interpolating wrapped theta directly
    # creates large artificial arcs when a path crosses the 0/2pi boundary.
    x, y, z, flow = (np.interp(target, source, diw_data[:, i]) for i in range(4))
    r = np.hypot(x, y)
    theta = np.mod(np.arctan2(y, x), 2.0 * np.pi)
    spacing = np.sqrt(np.diff(x, prepend=x[0]) ** 2 + np.diff(y, prepend=y[0]) ** 2 + np.diff(z, prepend=z[0]) ** 2)
    baseline = np.median(spacing[1:]) if points > 1 else 1.0
    amount = np.clip(flow * np.maximum(spacing, baseline), 0.0, None)
    return np.column_stack((r, theta, z, amount))


def write_csv(path: str | Path, data: np.ndarray) -> None:
    with Path(path).open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("r", "theta", "z", "material_amount"))
        writer.writerows(data.tolist())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diw_script", help="path to diw.py or a compatible script")
    parser.add_argument("part_number")
    parser.add_argument("points", type=int)
    parser.add_argument("--logo", choices=("LLNL", "llnl", "Siemens"), default=None)
    parser.add_argument("-o", "--output", default="polar_density.csv")
    parser.add_argument("--source-samples", type=int, default=1000)
    args = parser.parse_args()
    module = load_diw_module(args.diw_script)
    data = module.generate_diw_data(args.part_number, args.source_samples, args.logo)
    write_csv(args.output, generate_polar_density(data, args.points))


if __name__ == "__main__":
    main()
