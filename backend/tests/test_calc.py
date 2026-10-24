"""Calculators: worked examples checked by hand, plus every recorded case (the TypeScript engine is checked against the same file)."""
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calc import engine as E  # noqa: E402

CASES = json.loads((Path(__file__).parent / "calc_cases.json").read_text())


def item(res, label):
    return next(i["value"] for i in res["items"] if i["label"] == label)


def test_pf_correction_worked_example():
    # 100 kW from 0.70 to 0.95: Q = P (tan φ1 − tan φ2) = 100 × (1.0202 − 0.3287) = 69.15 kVAR
    res = E.run("pf-correction", {"kw": 100, "pf_now": 0.7, "pf_target": 0.95})
    q = 100 * (math.tan(math.acos(0.7)) - math.tan(math.acos(0.95)))
    assert abs(q - 69.15) < 0.01
    assert item(res, "kVAR needed") == pytest.approx(69.2, abs=0.05)


def test_pipe_electrode_resistance():
    # IS 3043 pipe: R = 100ρ / (2πL) × ln(4L/d), ρ = 100 Ω·m, L = 300 cm, d = 4 cm → 30.26 Ω
    res = E.run("earthing", {"rho": 100, "electrode": "pipe", "length": 3, "diameter": 40})
    r = 100 * 100 / (2 * math.pi * 300) * math.log(4 * 300 / 4)
    assert round(r, 2) == 30.26
    assert item(res, "One electrode") == 30.26


def test_motor_full_load_current():
    # 15 kW, 415 V, η 0.92, PF 0.86 → I = 15000 / (√3 × 415 × 0.92 × 0.86) = 26.4 A
    res = E.run("motor", {"rating": 15, "unit": "kw", "voltage": 415})
    assert res["headline"]["value"] == pytest.approx(15000 / (math.sqrt(3) * 415 * 0.92 * 0.86), abs=0.05)


def test_lt_limit_in_tamil_nadu():
    small = E.run("connected-load", {})
    assert "LT" in small["headline"]["sub"]
    big = E.run("connected-load", {"method": "area", "building": "hospital", "area": 12000})
    assert "HT" in big["headline"]["sub"]


def test_tariff_constants_are_current_order():
    c = E.merged_constants(None)
    assert c["tariffs"]["HT_I"]["energy"] == 7.5
    assert c["tariffs"]["HT_I"]["demand"] == 608


def test_validation_messages():
    with pytest.raises(E.CalcError, match="at least"):
        E.run("pf-correction", {"kw": -5})
    with pytest.raises(E.CalcError, match="choose one"):
        E.run("cable-size", {"conductor": "gold"})


def test_overrides_change_results():
    base = E.run("bill-estimator", {})
    dear = E.run("bill-estimator", {}, {"tariffs": {**E.merged_constants(None)["tariffs"], "HT_I": {**E.merged_constants(None)["tariffs"]["HT_I"], "energy": 9.0}}})
    assert dear["headline"]["value"] > base["headline"]["value"]


@pytest.mark.parametrize("case", CASES, ids=[f"{c['slug']}-{n}" for n, c in enumerate(CASES)])
def test_recorded_cases(case):
    res = E.run(case["slug"], case["inputs"])
    want = case["result"]
    assert res["headline"] == want["headline"]
    assert res["verdict"] == want["verdict"]
    assert res["items"] == want["items"]
