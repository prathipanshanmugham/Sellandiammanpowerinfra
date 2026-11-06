"""Writes backend/tests/calc_cases.json: inputs and the Python results for every calculator (defaults plus variants).
The TypeScript engine must give the same results (frontend/scripts/calc-parity.mjs); pytest re-checks the Python side.
    python tests/make_calc_cases.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calc import engine as E  # noqa: E402

V = {
    "connected-load": [{}, {"method": "area", "building": "hospital", "area": 12000}, {"method": "area", "building": "apartment", "area": 1500, "growth": 0},
                       {"loads": [{"name": "Chiller", "qty": 2, "kw": 110, "df": 0.9}, {"name": "Pumps", "qty": 6, "kw": 15, "df": 0.6}], "diversity": 0.8, "pf": 0.92},
                       {"loads": [{"name": "Shop", "qty": 1, "kw": 9, "df": 1}], "pf": 1, "growth": 50}],
    "lt-vs-ht": [{}, {"md_kva": 180}, {"md_kva": 120, "units": 60000, "peak_share": 10, "night_share": 40}, {"category": "commercial", "md_kva": 140, "units": 30000},
                 {"md_kva": 145, "units": 90000, "substation_cost": 1500000}],
    "bill-estimator": [{}, {"tariff": "HT_III", "units": 25000, "md_kva": 260, "cd_kva": 250, "pf": 0.84}, {"tariff": "LT_IIIB", "units": 9000, "load_kw": 75},
                       {"tariff": "LT_V", "units": 40, "load_kw": 4}, {"tariff": "HT_I", "pf": 0.72, "peak_share": 0, "night_share": 0}],
    "contract-demand": [{}, {"cd_kva": 300}, {"md": [100, 100, 100], "cd_kva": 200, "tariff": "HT_III"}, {"md": [510, 530, 525, 560], "cd_kva": 500}, {"cd_kva": 470}],
    "ht-connection-roadmap": [{}, {"kva": 2000, "voltage": "22kV"}, {"kva": 160, "kind": "lt_to_ht"}, {"kva": 750, "kind": "load_increase", "voltage": "33kV"}, {"kva": 3500}],
    "transformer-sizing": [{}, {"load_kw": 4000, "demand_factor": 0.9}, {"load_kw": 90, "location": "indoor"}, {"load_kw": 1200, "growth": 0, "max_loading": 100}, {"load_kw": 50, "pf": 0.8}],
    "transformer-losses": [{}, {"avg_load": 90, "years": 25, "tariff": 9.4}, {"kva": "250", "options": [{"name": "Only", "price": 400000, "nll": 350, "ll": 2800}]},
                           {"hours": 4000, "avg_load": 40}, {"options": [{"name": "A", "price": 1, "nll": 0, "ll": 0}, {"name": "B", "price": 2, "nll": 0, "ll": 0}]}],
    "dg-sizing": [{}, {"motor_kw": 75, "starter": "dol"}, {"motor_kw": 0}, {"running_kw": 600, "motor_kw": 110, "starter": "soft_starter", "transient": 2.5}, {"running_kw": 20, "motor_kw": 5.5, "starter": "dol", "pf": 0.9}],
    "ups-battery": [{}, {"load_kw": 40, "backup_min": 15, "bank_v": "384"}, {"load_kw": 2, "backup_min": 240, "bank_v": "48"}, {"load_kw": 100, "backup_min": 120, "bank_v": "360"}, {"load_kw": 0.5, "pf": 0.8, "growth": 0}],
    "solar-rooftop": [{}, {"metering": "gross"}, {"roof_area": 120, "town": "Chennai"}, {"monthly_units": 400, "sanctioned_kw": 5, "tariff": 6.5, "cost_per_kwp": 60000}, {"sanctioned_kw": 40}],
    "ev-charger-load": [{}, {"chargers": [{"type": "ac_22", "qty": 4}], "sanctioned_kva": 500, "existing_md": 200}, {"chargers": [{"type": "dc_120", "qty": 2}, {"type": "ac_3_3", "qty": 10}], "diversity": 1},
                        {"chargers": [{"type": "ac_11", "qty": 1}], "sanctioned_kva": 25, "existing_md": 20}, {"chargers": []}],
    "cable-size": [{}, {"laying": "air", "ambient": 45, "group": 3}, {"voltage": "11000", "load_kw": 1500, "length": 600, "fault_ka": 20, "clear_s": 0.5}, {"voltage": "230", "load_kw": 5, "conductor": "cu", "length": 40},
                   {"load_kw": 600, "length": 250, "group": 4, "spacing": "spaced", "soil": "200", "depth": "105"}, {"conductor": "cu", "load_kw": 30, "length": 60, "fault_ka": 10}],
    "voltage-drop": [{}, {"phase": "1", "current": 32, "length": 45, "conductor": "cu", "size": "6", "purpose": "lighting"}, {"current": 400, "size": "300", "runs": 2, "length": 180},
                     {"current": 50, "size": "16", "length": 300}, {"conductor": "cu", "size": "2.5", "current": 10, "length": 30, "pf": 1}],
    "fault-level": [{}, {"kva": 2500, "z_pct": 6.25, "xr": 8, "cable_m": 10, "cable_size": "400", "runs": 8}, {"kva": 250, "z_pct": 4.5, "xr": 4, "cable_m": 60, "cable_size": "95", "runs": 1},
                    {"source_mva": 500, "kva": 1600, "z_pct": 6.25, "cable_m": 0}, {"conductor": "cu", "cable_size": "240", "runs": 3}],
    "breaker-selector": [{}, {"input": "amps", "value": 20, "load_type": "lighting", "fault_ka": 6}, {"input": "kva", "value": 1000, "load_type": "transformer", "fault_ka": 40},
                         {"voltage": "11000", "input": "kva", "value": 2000, "fault_ka": 20}, {"input": "kw", "value": 300, "load_type": "capacitor"}, {"voltage": "230", "input": "kw", "value": 3, "load_type": "mixed", "fault_ka": 3}],
    "motor": [{}, {"rating": 100, "unit": "hp"}, {"rating": 3.7, "duty": "conveyor"}, {"rating": 160, "duty": "variable", "length": 120}, {"rating": 22, "eff": 0.94, "pf": 0.9, "duty": "compressor"}],
    "pf-correction": [{}, {"kw": 100, "pf_now": 0.7, "pf_target": 0.95, "energy_bill": 0, "nonlinear": 5}, {"ht": False}, {"kw": 1200, "pf_now": 0.88, "pf_target": 0.99, "nonlinear": 45}, {"pf_now": 0.9}],
    "harmonics": [{}, {"nonlinear": 10, "capacitors": False}, {"nonlinear": 25}, {"kva": 2500, "z_pct": 6.25, "load_kva": 400, "nonlinear": 60}, {"kva": 100, "load_kva": 95, "nonlinear": 0}],
    "energy-savings": [{}, {"measure": "vfd"}, {"measure": "vfd", "flow": 50, "motor_kw": 90, "hours": 8000}, {"measure": "motor"}, {"measure": "motor", "cost": 0}],
    "earthing": [{}, {"rho": 100, "target": 1}, {"electrode": "plate", "rho": 50}, {"electrode": "strip", "length": 30, "rho": 200, "target": 5}, {"material": "copper", "fault_ka": 40}, {"material": "aluminium", "rho": 10}],
    "lightning-risk": [{}, {"use": "house", "construction": "rcc_nonmetal", "contents": "ordinary", "isolation": "surrounded", "l": 12, "w": 10, "h": 8}, {"use": "school_hospital", "contents": "assembly", "isolation": "isolated", "terrain": "hill"},
                       {"h": 60, "l": 30, "w": 30, "ng": 8}, {"construction": "thatched", "l": 6, "w": 5, "h": 4, "ng": 0.5}],
    "lighting-lux": [{}, {"space": "warehouse", "length": 60, "width": 30, "height": 9, "lumens": 20000, "watts": 150}, {"space": "corridor", "length": 30, "width": 2, "height": 2.5, "lumens": 1500, "watts": 12},
                     {"lux": 750, "length": 20, "width": 20, "height": 3}, {"space": "operation_theatre", "length": 7, "width": 6, "height": 2, "lumens": 6000, "watts": 50}],
    "units-formulas": [{}, {"from": "kva", "value": 500}, {"from": "hp", "value": 50, "eff": 0.9}, {"from": "amps", "value": 32, "phase": "1", "voltage": 230, "pf": 1}, {"from": "amps", "value": 1600}],
    "document-checklists": [{"kind": k} for k in ("new_lt", "load_change", "new_ht", "ceig", "name_transfer", "solar")],
}

# Typing in the form: a blank box, half-typed numbers, out-of-range values. Both engines must give the same message
# (or, for optional and hidden fields, the same result).
# 6 Nov 2026 review: each fix keeps a case so both engines must agree on it
REVIEW = [
    ("dg-sizing", {"pf": 1, "motor_kw": 0}), ("dg-sizing", {"pf": 0.9, "motor_kw": 0}),
    ("ups-battery", {"load_kw": 8, "backup_min": 15, "bank_v": "96"}), ("ups-battery", {"load_kw": 500}), ("ups-battery", {"backup_min": 600}),
    ("motor", {"rating": 500, "voltage": 11000}), ("motor", {"rating": 37}), ("motor", {"rating": 22, "duty": "conveyor"}),
    ("pf-correction", {"kw": 300, "pf_now": 0.7, "pf_target": 0.95}), ("pf-correction", {"kw": 20, "pf_now": 0.85, "pf_target": 0.95}),
    ("pf-correction", {"kw": 100000, "pf_now": 0.7}), ("pf-correction", {"pf_now": 0.84}), ("pf-correction", {"pf_now": 0.74}),
    ("harmonics", {"kva": 500, "z_pct": 12, "load_kva": 300, "nonlinear": 14, "capacitors": False}),
    ("breaker-selector", {"voltage": "11000", "input": "kva", "value": 1000, "fault_ka": 40}), ("breaker-selector", {"voltage": "33000", "input": "kva", "value": 80000}),
    ("breaker-selector", {"value": 200, "input": "amps", "fault_ka": 150}), ("breaker-selector", {"value": 6000, "input": "amps"}),
    ("breaker-selector", {"value": 10, "input": "amps", "fault_ka": 25}), ("breaker-selector", {"voltage": "230", "input": "kva", "value": 5}),
    ("breaker-selector", {"value": 30, "input": "amps", "load_type": "motor", "fault_ka": 6}),
    ("cable-size", {"group": 7}), ("cable-size", {"group": 9, "laying": "air"}), ("cable-size", {"laying": "air"}), ("cable-size", {"laying": "air", "ambient": 30}),
    ("cable-size", {"voltage": "33000", "conductor": "cu", "load_kw": 5000}), ("cable-size", {"clear_s": 0.02}),
    ("fault-level", {"source_mva": 1000, "kva": 4000, "z_pct": 5, "cable_m": 1}), ("voltage-drop", {"conductor": "cu", "size": "10"}),
    ("earthing", {"electrode": "plate"}), ("earthing", {"electrode": "strip", "length": 0.5, "strip_w": 200, "strip_depth": 3}),
    ("earthing", {"electrode": "strip", "length": 30}), ("earthing", {"rho": 500, "target": 1}),
    ("lightning-risk", {}), ("lightning-risk", {"use": "office", "l": 40, "w": 20, "h": 10, "contents": "ordinary"}),
    ("lightning-risk", {"isolation": "isolated", "terrain": "hill"}), ("lightning-risk", {"l": 10, "w": 8, "h": 4, "use": "house", "ng": 1}),
    ("lighting-lux", {"length": 500, "width": 1}), ("lighting-lux", {"length": 40, "width": 2}),
    ("units-formulas", {"phase": "1", "from": "amps", "value": 10}), ("units-formulas", {"phase": "1", "voltage": 240}),
    ("bill-estimator", {"tariff": "LT_IIIB"}), ("bill-estimator", {"tariff": "LT_V", "pf": 0.8, "units": 40}), ("bill-estimator", {"tariff": "LT_IIIB", "load_kw": 142.5, "pf": 0.7}),
    ("bill-estimator", {"pf": 0.85}), ("bill-estimator", {"pf": 0.84}), ("bill-estimator", {"pf": 0.75}), ("bill-estimator", {"pf": 0.74}),
    ("lt-vs-ht", {}), ("lt-vs-ht", {"category": "commercial"}), ("lt-vs-ht", {"md_kva": 5000}),
    ("connected-load", {}), ("connected-load", {"loads": [{"name": "M", "qty": 30, "kw": 10, "df": 0.5}], "diversity": 0.8, "growth": 0}),
    ("contract-demand", {"md": [0] * 12}), ("contract-demand", {"md": [400] * 12}),
    ("ht-connection-roadmap", {"kva": 5000}), ("ht-connection-roadmap", {"kva": 100}),
    ("transformer-sizing", {"load_kw": 10}), ("transformer-sizing", {"location": "indoor"}),
    ("transformer-losses", {"options": [{"name": "A", "price": 1000000, "nll": 1100, "ll": 8000}, {"name": "B", "price": 1100000, "nll": 900, "ll": 7000},
                                        {"name": "C", "price": 900000, "nll": 1500, "ll": 11000}]}),
    ("energy-savings", {"measure": "vfd", "flow": 100}), ("energy-savings", {"new_w": 72}),
    ("ev-charger-load", {"sanctioned_kva": 112, "existing_md": 90, "chargers": [{"type": "dc_120", "qty": 1}]}),
    ("document-checklists", {"kind": "solar"}),
    # re-check round
    ("lighting-lux", {"length": 12, "width": 6, "lumens": 7100}), ("lighting-lux", {"length": 10, "width": 10}),
    ("bill-estimator", {"tariff": "LT_IIIB", "tod_meter": False}), ("bill-estimator", {"tariff": "LT_V", "tod_meter": False, "pf": 0.7}),
    ("pf-correction", {"ht": False, "pf_now": 0.75}), ("pf-correction", {"kw": 30000, "pf_now": 0.7}),
    ("motor", {"rating": 900}), ("motor", {"rating": 5000}), ("motor", {"rating": 37}),
    ("ups-battery", {"backup_min": 1}), ("ups-battery", {"backup_min": 4.5}),
    ("harmonics", {"kva": 500, "z_pct": 12, "load_kva": 300, "nonlinear": 12.6, "capacitors": False}),
    ("breaker-selector", {"value": 64, "input": "amps", "fault_ka": 25}),
    ("earthing", {"electrode": "strip", "length": 0.8, "strip_w": 200, "strip_depth": 3}), ("earthing", {"electrode": "strip", "length": 2.4}),
    ("cable-size", {"load_kw": 5, "fault_ka": 6, "clear_s": 0.01}),
]

EDGE = [
    ("pf-correction", {"pf_now": ""}), ("pf-correction", {"kw": "999999999"}), ("pf-correction", {"kw": "1e3"}), ("pf-correction", {"kw": "100000"}),
    ("motor", {"eff": "", "pf": ""}), ("motor", {"voltage": "0"}), ("motor", {"voltage": " "}),
    ("lt-vs-ht", {"substation_cost": ""}), ("lt-vs-ht", {"pf": ""}), ("lt-vs-ht", {"units": "0"}),
    ("lighting-lux", {"lux": ""}), ("lighting-lux", {"length": ""}),
    ("fault-level", {"lv": "0"}), ("fault-level", {"lv": "1100"}), ("transformer-sizing", {"max_loading": ""}),
    ("connected-load", {"method": "area", "area": "abc"}), ("connected-load", {"method": "loads", "area": ""}),
    ("connected-load", {"loads": [{"name": "X", "qty": "abc", "kw": 1, "df": 1}]}), ("connected-load", {"loads": [{"name": "X", "qty": "", "kw": "", "df": 1}]}),
    ("connected-load", {"loads": [{"name": "X", "qty": 20000, "kw": 1, "df": 1}]}),
    ("earthing", {"electrode": "plate", "length": "", "diameter": ""}), ("earthing", {"electrode": "plate", "plate_w": "0"}), ("earthing", {"electrode": "strip", "strip_depth": ""}),
    ("energy-savings", {"measure": "vfd", "fixtures": "", "old_w": "", "new_w": ""}), ("energy-savings", {"measure": "led", "fixtures": ""}),
    ("solar-rooftop", {"metering": "net", "export_rate": ""}), ("solar-rooftop", {"metering": "gross", "export_rate": ""}),
    ("contract-demand", {"md": [400, 200000]}), ("contract-demand", {"md": [400, "", 410]}), ("cable-size", {"length": "5001"}), ("harmonics", {"load_kva": ""}),
    ("units-formulas", {"voltage": ""}), ("ups-battery", {"dod": ""}), ("voltage-drop", {"runs": ""}), ("dg-sizing", {"pf": "-"}),
]


def main():
    out = []
    for slug, cases in V.items():
        for inp in cases:
            res = E.run(slug, inp)
            out.append({"slug": slug, "inputs": inp, "result": res})
    for slug, inp in EDGE + REVIEW:
        try:
            out.append({"slug": slug, "inputs": inp, "result": E.run(slug, inp)})
        except E.CalcError as ex:
            out.append({"slug": slug, "inputs": inp, "error": str(ex)})
    p = Path(__file__).with_name("calc_cases.json")
    p.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    print(f"{len(out)} cases for {len(V)} tools -> {p}")


if __name__ == "__main__":
    main()
