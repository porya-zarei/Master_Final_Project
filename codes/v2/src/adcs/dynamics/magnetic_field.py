"""Earth geomagnetic field model: official IGRF-14 degree-13 spherical harmonics + tilted dipole.

Supports:
- Official NOAA/IAGA `igrf14coeffs.txt` (degrees n=1..13 with 2025-2030 secular variation).
- Simple whitespace `n m g_nm h_nm` tables.
- Built-in tilted geomagnetic dipole fallback if no coefficient file is present.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from adcs.interfaces.types import FloatArray
from adcs.utils.quaternion import quat_rotate_vec_inv

EARTH_ROTATION_RATE_RAD_S = 7.2921150e-5
IGRF_REFERENCE_RADIUS_M = 6371200.0
DEFAULT_IGRF14_FILENAME = "igrf14coeffs.txt"


@dataclass(frozen=True)
class GaussCoefficients:
    """Schmidt semi-normalized spherical harmonic Gauss coefficients in nT."""

    max_degree: int
    g: FloatArray  # shape (N+1, N+1), g[n, m] in nT
    h: FloatArray  # shape (N+1, N+1), h[n, m] in nT
    model_fidelity: str
    epoch_year: float = 2025.0


def default_tilted_dipole_coefficients() -> GaussCoefficients:
    """Built-in n=1 tilted geomagnetic dipole fallback when no IGRF-14 file is supplied."""
    g = np.zeros((2, 2), dtype=np.float64)
    h = np.zeros((2, 2), dtype=np.float64)
    g[1, 0] = -29350.0
    g[1, 1] = -1410.3
    h[1, 1] = 4545.5
    return GaussCoefficients(
        max_degree=1,
        g=g,
        h=h,
        model_fidelity="tilted_dipole_fallback_pending_igrf14_file",
        epoch_year=2025.0,
    )


def load_igrf14_coefficients(
    path: str | Path,
    *,
    decimal_year: float = 2025.0,
) -> GaussCoefficients:
    """Parse official NOAA/IAGA `igrf14coeffs.txt` (degrees 1..13 + 2025-2030 SV)."""
    file_path = Path(path)
    lines = file_path.read_text(encoding="utf-8").splitlines()
    header_years: list[float] | None = None
    has_sv = False
    year_col_idx: int | None = None

    raw_rows: list[tuple[str, int, int, float, float]] = []
    max_n = 0

    for line in lines:
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("c/s"):
            continue
        parts = s.split()
        if parts[0] == "g/h":
            # Header row: g/h n m 1900.0 ... 2025.0 2025-30
            epoch_tokens = parts[3:]
            has_sv = "-" in epoch_tokens[-1]
            year_tokens = epoch_tokens[:-1] if has_sv else epoch_tokens
            header_years = [float(tok) for tok in year_tokens]
            # Pick epoch 2025.0 (or nearest <= decimal_year)
            year_col_idx = len(header_years) - 1
            for idx, yr in enumerate(header_years):
                if yr <= decimal_year + 1e-6:
                    year_col_idx = idx
            continue

        if parts[0] in ("g", "h") and header_years is not None and year_col_idx is not None:
            kind = parts[0]
            n = int(parts[1])
            m = int(parts[2])
            vals = parts[3:]
            base_val = float(vals[year_col_idx])
            base_year = header_years[year_col_idx]
            if decimal_year >= header_years[-1] and has_sv:
                sv = float(vals[-1])
                val = base_val + sv * (decimal_year - base_year)
            elif year_col_idx + 1 < len(header_years):
                next_val = float(vals[year_col_idx + 1])
                dt_yr = header_years[year_col_idx + 1] - base_year
                frac = (decimal_year - base_year) / max(dt_yr, 1e-9)
                val = base_val + frac * (next_val - base_val)
            else:
                val = base_val
            max_n = max(max_n, n)
            raw_rows.append((kind, n, m, val, base_year))

    if max_n < 1:
        raise ValueError(f"Failed to parse IGRF-14 coefficients from {file_path}")

    g = np.zeros((max_n + 1, max_n + 1), dtype=np.float64)
    h = np.zeros((max_n + 1, max_n + 1), dtype=np.float64)
    for kind, n, m, val, _ in raw_rows:
        if kind == "g":
            g[n, m] = val
        else:
            h[n, m] = val

    return GaussCoefficients(
        max_degree=max_n,
        g=g,
        h=h,
        model_fidelity=f"IGRF-14_deg_{max_n}_epoch_{decimal_year:.2f}",
        epoch_year=float(decimal_year),
    )


def load_shc_coefficients(
    path: str | Path,
    *,
    decimal_year: float = 2025.0,
) -> GaussCoefficients:
    """Load official NOAA `igrf14coeffs.txt` OR simple `n m g_nm h_nm` coefficient file."""
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if "g/h" in text and "IGRF" in text:
        return load_igrf14_coefficients(file_path, decimal_year=decimal_year)

    rows: list[tuple[int, int, float, float]] = []
    max_n = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 4:
            continue
        n, m = int(parts[0]), int(parts[1])
        gnm, hnm = float(parts[2]), float(parts[3])
        max_n = max(max_n, n)
        rows.append((n, m, gnm, hnm))
    if max_n < 1:
        raise ValueError(f"No valid spherical harmonic coefficients found in {file_path}")
    g = np.zeros((max_n + 1, max_n + 1), dtype=np.float64)
    h = np.zeros((max_n + 1, max_n + 1), dtype=np.float64)
    for n, m, gnm, hnm in rows:
        g[n, m] = gnm
        h[n, m] = hnm
    return GaussCoefficients(
        max_degree=max_n,
        g=g,
        h=h,
        model_fidelity=f"spherical_harmonic_deg_{max_n}",
        epoch_year=float(decimal_year),
    )


def find_default_igrf14_file() -> Path | None:
    """Locate bundled `configs/igrf14coeffs.txt` relative to repo root if available."""
    repo_root = Path(__file__).resolve().parents[3]
    candidate = repo_root / "configs" / DEFAULT_IGRF14_FILENAME
    return candidate if candidate.exists() else None


def _schmidt_legendre(
    max_n: int, cos_theta: float, sin_theta: float
) -> tuple[FloatArray, FloatArray]:
    """Compute Schmidt semi-normalized associated Legendre functions P_n^m and dP_n^m/dtheta."""
    p = np.zeros((max_n + 1, max_n + 1), dtype=np.float64)
    dp = np.zeros((max_n + 1, max_n + 1), dtype=np.float64)
    p[0, 0] = 1.0
    dp[0, 0] = 0.0
    for n in range(1, max_n + 1):
        if n == 1:
            p[1, 1] = sin_theta
            dp[1, 1] = cos_theta
        else:
            k = np.sqrt((2.0 * n - 1.0) / (2.0 * n))
            p[n, n] = k * sin_theta * p[n - 1, n - 1]
            dp[n, n] = k * (cos_theta * p[n - 1, n - 1] + sin_theta * dp[n - 1, n - 1])
        for m in range(0, n):
            a_nm = np.sqrt(((2.0 * n - 1.0) ** 2) / ((n - m) * (n + m)))
            if n - 1 == m:
                p[n, m] = a_nm * cos_theta * p[n - 1, m]
                dp[n, m] = a_nm * (-sin_theta * p[n - 1, m] + cos_theta * dp[n - 1, m])
            else:
                b_nm = np.sqrt(((n - 1.0 - m) * (n - 1.0 + m)) / ((n - m) * (n + m)))
                p[n, m] = a_nm * cos_theta * p[n - 1, m] - b_nm * p[n - 2, m]
                dp[n, m] = (
                    a_nm * (-sin_theta * p[n - 1, m] + cos_theta * dp[n - 1, m])
                    - b_nm * dp[n - 2, m]
                )
    return p, dp


class GeomagneticFieldModel:
    """Earth magnetic field evaluator (IGRF-14 ECEF spherical harmonics -> ECI -> Body)."""

    def __init__(
        self,
        coefficients: GaussCoefficients | None = None,
        gmst_initial_rad: float = 0.0,
        decimal_year: float = 2025.0,
        auto_load_igrf14: bool = True,
    ) -> None:
        if coefficients is not None:
            self.coefficients = coefficients
        elif auto_load_igrf14 and (igrf_path := find_default_igrf14_file()) is not None:
            self.coefficients = load_igrf14_coefficients(igrf_path, decimal_year=decimal_year)
        else:
            self.coefficients = default_tilted_dipole_coefficients()
        self.gmst_initial_rad = float(gmst_initial_rad)

    @property
    def model_fidelity(self) -> str:
        return self.coefficients.model_fidelity

    def _eci_to_ecef_dcm(self, time_s: float) -> FloatArray:
        theta = self.gmst_initial_rad + EARTH_ROTATION_RATE_RAD_S * float(time_s)
        c, s = np.cos(theta), np.sin(theta)
        return np.array(
            [
                [c, s, 0.0],
                [-s, c, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def field_ecef_t(self, position_ecef_m: FloatArray) -> FloatArray:
        """Compute geomagnetic field vector in ECEF Cartesian coordinates (Tesla)."""
        x, y, z = float(position_ecef_m[0]), float(position_ecef_m[1]), float(position_ecef_m[2])
        r = float(np.sqrt(x * x + y * y + z * z))
        if r < 1.0e5:
            raise ValueError(f"Invalid geocentric radius {r} m for geomagnetic field")

        cos_theta = float(np.clip(z / r, -1.0, 1.0))
        sin_theta = float(np.sqrt(max(0.0, 1.0 - cos_theta * cos_theta)))
        phi = float(np.arctan2(y, x))
        sin_theta_safe = max(sin_theta, 1e-10)

        max_n = self.coefficients.max_degree
        p, dp = _schmidt_legendre(max_n, cos_theta, sin_theta)
        a_over_r = IGRF_REFERENCE_RADIUS_M / r

        # Precompute cos(m*phi), sin(m*phi)
        m_idx = np.arange(max_n + 1, dtype=np.float64)
        cos_m = np.cos(m_idx * phi)
        sin_m = np.sin(m_idx * phi)

        g_mat = self.coefficients.g
        h_mat = self.coefficients.h

        b_r = 0.0
        b_theta = 0.0
        b_phi = 0.0
        ratio_pow = a_over_r * a_over_r
        for n in range(1, max_n + 1):
            ratio_pow *= a_over_r  # (a/r)^(n+2)
            sl = slice(0, n + 1)
            gn = g_mat[n, sl]
            hn = h_mat[n, sl]
            cm = cos_m[sl]
            sm = sin_m[sl]
            gh_cos = gn * cm + hn * sm
            gh_sin = -gn * sm + hn * cm
            pn = p[n, sl]
            dpn = dp[n, sl]
            b_r += (n + 1) * ratio_pow * float(np.dot(gh_cos, pn))
            b_theta -= ratio_pow * float(np.dot(gh_cos, dpn))
            b_phi -= ratio_pow * float(np.dot(m_idx[sl] * gh_sin, pn)) / sin_theta_safe

        scale = 1.0e-9
        b_r *= scale
        b_theta *= scale
        b_phi *= scale

        cos_phi = float(np.cos(phi))
        sin_phi = float(np.sin(phi))
        b_x = b_r * sin_theta * cos_phi + b_theta * cos_theta * cos_phi - b_phi * sin_phi
        b_y = b_r * sin_theta * sin_phi + b_theta * cos_theta * sin_phi + b_phi * cos_phi
        b_z = b_r * cos_theta - b_theta * sin_theta
        return np.array([b_x, b_y, b_z], dtype=np.float64)

    def field_eci_t(self, position_eci_m: FloatArray, time_s: float) -> FloatArray:
        """Compute geomagnetic field in ECI frame (Tesla)."""
        r_ecef_eci = self._eci_to_ecef_dcm(time_s)
        pos_ecef = r_ecef_eci @ np.asarray(position_eci_m, dtype=np.float64)
        b_ecef = self.field_ecef_t(pos_ecef)
        return r_ecef_eci.T @ b_ecef

    def field_body_t(
        self, position_eci_m: FloatArray, q_ib: FloatArray, time_s: float
    ) -> FloatArray:
        """Compute geomagnetic field in spacecraft body frame (Tesla)."""
        b_eci = self.field_eci_t(position_eci_m, time_s)
        return quat_rotate_vec_inv(q_ib, b_eci)
