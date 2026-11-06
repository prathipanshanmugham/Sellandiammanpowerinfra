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
    # 15 kW, 415 V, IE3 η 0.921 (IEC 60034-30-1), typical PF 0.84 → I = 15000 / (√3 × 415 × 0.921 × 0.84) = 27.0 A
    res = E.run("motor", {"rating": 15, "unit": "kw", "voltage": 415})
    assert res["headline"]["value"] == pytest.approx(15000 / (math.sqrt(3) * 415 * 0.921 * 0.84), abs=0.05)


def test_review_fixes_6_nov_2026():
    """Independent hand calculations behind the 6 Nov 2026 review."""
    # HT PF penalty: the band's rate × every 0.01 below 0.90 (T.O. 6/2025 cl. 3.1.1.6)
    for pf, pct in ((0.90, 0), (0.85, 5), (0.84, 9), (0.80, 15), (0.75, 22.5), (0.74, 32), (0.70, 40)):
        assert E.pf_penalty_pct(pf, E.merged_constants()) == pytest.approx(pct), pf
    # LT PF penalty from 0.85 (cl. 3.2.1(b))
    for pf, pct in ((0.85, 0), (0.80, 5), (0.75, 10), (0.70, 22.5)):
        assert E.lt_pf_penalty_pct(pf, E.merged_constants()) == pytest.approx(pct), pf
    # LT IIIB, 60,000 kWh, 30% peak, 10% night: ToD = 60000 × 8.25 × (0.30 × 0.25 − 0.10 × 0.05) = 34,650
    lt = E.run("bill-estimator", {"tariff": "LT_IIIB"})
    assert dict((r[0], r[2]) for r in lt["table"]["rows"])["Time-of-day"] == pytest.approx(34650)
    # LT fixed charges per kW or part: 142.5 kW bills as 143 kW × ₹608
    lt2 = E.run("bill-estimator", {"tariff": "LT_IIIB", "load_kw": 142.5})
    assert dict((r[0], r[2]) for r in lt2["table"]["rows"])["Fixed charges"] == pytest.approx(143 * 608)
    # DG: 120 kW at PF 1 needs 120 ÷ 0.8 ÷ 0.8 = 187.5 kVA → 200 kVA
    assert E.run("dg-sizing", {"pf": 1, "motor_kw": 0})["headline"]["value"] == 200
    # Cable: 7 cables in ground take the 8-cable factor (0.50), so 120 mm² Al (232 A × 0.5 = 116 A) fails 122.8 A
    assert E.run("cable-size", {"group": 7})["headline"]["value"] == "150 mm²"
    # Plate: A is both faces, so 0.6 × 0.6 m in 40 Ω·m gives (40 ÷ 4) × √(π ÷ 0.72) = 20.89 Ω
    assert E.run("earthing", {"electrode": "plate"})["items"][0]["value"] == pytest.approx(20.89, abs=0.01)
    # Lightning: risk 169× the acceptable needs E = 0.994 > 0.98 → Class I with extra measures
    assert E.run("lightning-risk", {})["headline"]["sub"] == "Class I with extra measures"
    # PF steps add up to the panel
    pf = E.run("pf-correction", {"kw": 300, "pf_now": 0.7, "pf_target": 0.95})
    steps = next(x["value"] for x in pf["items"] if x["label"].startswith("Steps"))
    assert sum(float(x) for x in steps.split("=")[0].split("+")) == pytest.approx(225)


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
    if "error" in case:
        with pytest.raises(E.CalcError) as ex:
            E.run(case["slug"], case["inputs"])
        assert str(ex.value) == case["error"]
        return
    res = E.run(case["slug"], case["inputs"])
    want = case["result"]
    assert res["headline"] == want["headline"]
    assert res["verdict"] == want["verdict"]
    assert res["items"] == want["items"]
