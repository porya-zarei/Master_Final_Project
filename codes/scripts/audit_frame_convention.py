"""Frame-convention audit -- reproduced evidence for plan section 1.3 (G14).

Run:  cd codes && PYTHONPATH=. ./venv/Scripts/python.exe scripts/audit_frame_convention.py

Every claim is tested against an INDEPENDENT implementation (scipy Rotation) or a
conservation law -- none of it is taken on faith from the external audit, and one
of the audit's claims (the reference-rate sign) initially looked wrong because a
sign error in THIS script's helper. That is why the helper is self-tested first.
"""
from __future__ import annotations
import os
import sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scipy.spatial.transform import Rotation
from satellite_adcs.config import load_config
from satellite_adcs.dynamics import SpacecraftDynamics
from satellite_adcs.quaternion import quat_to_dcm, dcm_to_quat
from satellite_adcs.guidance import NadirGuidance
import simulate


def C_NB_scipy(q):
    """Independent body->inertial matrix (scipy takes x,y,z,w)."""
    return Rotation.from_quat([q[1], q[2], q[3], q[0]]).as_matrix()


def Rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def frame_rate(C_of_t, dt):
    """Angular velocity of a moving frame, in the frame's own coordinates.

    C_of_t(t) must return C_IF with ROWS = the frame's axes in inertial coords.
    For a vector fixed in inertial space, c_dot = -omega x c, hence
        [c0]_x omega = (c1 - c0)/dt      for each basis vector -> lstsq over 9 eqns.
    Self-tested below before use.
    """
    C0, C1 = C_of_t(0.0), C_of_t(dt)
    A, b = [], []
    for j in range(3):
        e = np.zeros(3); e[j] = 1.0
        c0, c1 = C0 @ e, C1 @ e
        A.append([[0, -c0[2], c0[1]], [c0[2], 0, -c0[0]], [-c0[1], c0[0], 0]])
        b.append((c1 - c0) / dt)
    return np.linalg.lstsq(np.vstack(A), np.concatenate(b), rcond=None)[0]


def lvlh_C_IL(r, v):
    rn = np.linalg.norm(r); rhat = r / rn
    h = np.cross(r, v); yhat = -h / np.linalg.norm(h)
    zhat = -rhat; xhat = np.cross(yhat, zhat); xhat /= np.linalg.norm(xhat)
    return np.column_stack([xhat, yhat, zhat]).T


def main():
    cfg = load_config()
    rng = np.random.default_rng(0)
    print("=" * 78); print("T1  convention of quat_to_dcm (q = +90 deg about z)"); print("=" * 78)
    q90 = np.array([np.cos(np.pi / 4), 0, 0, np.sin(np.pi / 4)])
    C = quat_to_dcm(q90)
    is_cnb = np.allclose(C, Rz(np.pi / 2)); is_cbn = np.allclose(C, Rz(-np.pi / 2))
    print(f"   equals R_z(+90)=C_NB : {is_cnb}")
    print(f"   equals R_z(-90)=C_BN : {is_cbn}")
    print(f"   scipy agrees (active) : {np.allclose(C, C_NB_scipy(q90))}")
    print(f"   => docstring says C_BN but the function returns "
          f"{'C_NB  *** DOCSTRING IS WRONG ***' if is_cnb else 'C_BN'}")

    print(); print("=" * 78); print("T2  dcm_to_quat inverse of quat_to_dcm?"); print("=" * 78)
    ok_signed = ok_unsigned = True
    for _ in range(5):
        q = rng.normal(size=4); q /= np.linalg.norm(q)
        r = dcm_to_quat(quat_to_dcm(q))
        ok_signed &= np.allclose(r, q, atol=1e-10)
        ok_unsigned &= min(np.linalg.norm(r - q), np.linalg.norm(r + q)) < 1e-10
    print(f"   exact (signed q) : {ok_signed}   exact up to q <-> -q : {ok_unsigned}")

    print(); print("=" * 78)
    print("T3  torque-free spin: which reading conserves inertial momentum?"); print("=" * 78)
    cfg2 = load_config(); cfg2["disturbances"]["gravity_gradient"] = False
    d = SpacecraftDynamics(cfg2, rng); d.gravity_gradient = False
    d.reset(q=np.array([1.0, 0, 0, 0]), omega=np.array([0.3, -0.2, 0.5]))
    L_cbn, L_cnb = [], []
    for _ in range(2000):
        d.step(0.01, np.zeros(3), np.zeros(3))
        C = quat_to_dcm(d.q); H = d.J @ d.omega
        L_cbn.append(C.T @ H); L_cnb.append(C @ H)
    for name, L in (("read as C_BN (docstring)", np.array(L_cbn)),
                    ("read as C_NB (active)  ", np.array(L_cnb))):
        dr = np.max(np.linalg.norm(L - L[0], axis=1)) / np.linalg.norm(L[0])
        print(f"   L_I {name}: max relative drift = {dr:.3e}")

    print(); print("=" * 78)
    print("T4a metric vs TRUTH at random attitudes"); print("=" * 78)
    d2 = SpacecraftDynamics(cfg, rng); worst = 0.0
    rng4 = np.random.default_rng(11)          # own stream: T4a must be reproducible
    for k in range(6):
        q = rng4.normal(size=4); q /= np.linalg.norm(q)
        d2.reset(q=q, omega=np.array([0.02, -0.01, 0.03]))
        rep = simulate.pointing_error_deg(d2)
        nd = -d2.r / np.linalg.norm(d2.r)
        tru = np.degrees(np.arccos(np.clip((d2.C @ np.array([0, 0, 1.0])) @ nd, -1, 1)))
        worst = max(worst, abs(rep - tru))
        print(f"   trial {k}: reported {rep:8.3f}   truth {tru:8.3f}   diff {abs(rep-tru):7.3f}")
    print(f"   -> max discrepancy {worst:.2f} deg")

    print(); print("=" * 78)
    print("T4b real LQR episode (600 s): reported vs true pointing"); print("=" * 78)
    res = simulate.run_episode(cfg, seed=0, T=600.0); dyn = res["dyn"]
    nd = -dyn.r / np.linalg.norm(dyn.r)
    rep = simulate.pointing_error_deg(dyn)
    tru = np.degrees(np.arccos(np.clip((dyn.C @ np.array([0, 0, 1.0])) @ nd, -1, 1)))
    print(f"   reported = {rep:.4f} deg   TRUTH = {tru:.4f} deg")
    print(f"   reported series min = {res['pe'].min():.4f} deg")

    print(); print("=" * 78); print("T5  reference-rate sign"); print("=" * 78)
    w0 = 0.7
    self_test = frame_rate(lambda t: np.array([[np.cos(w0*t), np.sin(w0*t), 0],
                                               [-np.sin(w0*t), np.cos(w0*t), 0],
                                               [0, 0, 1.0]]), 1e-6)
    print(f"   helper self-test: true [0,0,{w0}] measured {np.round(self_test, 6)} "
          f"-> {'OK' if abs(self_test[2]-w0) < 1e-4 else 'BROKEN'}")
    d3 = SpacecraftDynamics(cfg, rng); d3.gravity_gradient = False; d3.reset()
    base_r, base_v = d3.r.copy(), d3.v.copy()
    om = frame_rate(lambda t: lvlh_C_IL(base_r + base_v * t, base_v), 1e-3)
    n = np.sqrt(d3.mu / d3.a ** 3)
    print(f"   n = {n:.6e} rad/s")
    print(f"   measured omega_LVLH = {np.round(om, 8)}")
    print(f"   code uses  [0, +n, 0] = {np.round([0, n, 0], 8)}")
    print(f"   => code is {'RIGHT' if abs(om[1]-n) < 1e-6 else 'WRONG (sign flipped)'}")

    print(); print("=" * 78); print("T6  does q_ref point at nadir?"); print("=" * 78)
    q_ref, _ = NadirGuidance(d3.mu, d3.a).reference(base_r, base_v)
    C_ref = quat_to_dcm(q_ref)
    nd = -base_r / np.linalg.norm(base_r)
    a_true = np.degrees(np.arccos(np.clip((C_ref @ np.array([0, 0, 1.0])) @ nd, -1, 1)))
    a_code = np.degrees(np.arccos(np.clip((C_ref.T @ np.array([0, 0, 1.0])) @ nd, -1, 1)))
    print(f"   q_ref body+z to nadir, TRUE reading  = {a_true:.4f} deg")
    print(f"   q_ref body+z to nadir, code's reading = {a_code:.4f} deg")

    print(); print("=" * 78)
    print("T7  after 600 s: is the body aligned with the desired LVLH frame?"); print("=" * 78)
    C_BN_true = quat_to_dcm(dyn.q).T
    C_tgt = lvlh_C_IL(dyn.r, dyn.v)
    err = np.degrees(np.arccos(np.clip((np.trace(C_BN_true.T @ C_tgt) - 1) / 2, -1, 1)))
    print(f"   body frame vs desired LVLH frame = {err:.3f} deg   (0 deg == nadir pointing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
