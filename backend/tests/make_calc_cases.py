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


def main():
    out = []
    for slug, cases in V.items():
        for inp in cases:
            res = E.run(slug, inp)
            out.append({"slug": slug, "inputs": inp, "result": res})
    p = Path(__file__).with_name("calc_cases.json")
    p.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    print(f"{len(out)} cases for {len(V)} tools -> {p}")


if __name__ == "__main__":
    main()
