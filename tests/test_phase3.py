"""Phase 3 comprehensive integration tests"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metering_designer.meters.pd_meter import size_pd_meter
from metering_designer.meters.vortex import size_vortex
from metering_designer.report.pdf_report import generate_pdf_report, HAS_REPORTLAB
from metering_designer.metrology.uncertainty import calc_uncertainty_budget
from metering_designer.piping.materials import select_material
from metering_designer.core.i18n import get_text
from metering_designer.core.backends import calc_z_factor, get_backend_status
from metering_designer.fluids.gas import calc_gas_properties
from metering_designer.conditioners.scoring import score_all_conditioners
from metering_designer.core.validation import validate_process_inputs, validate_requirements, check_composition_sanity
from collections import namedtuple


def test_pd_meter_sizing():
    pd = size_pd_meter(8, 200, 50, 850, 12, 30, 35)
    assert pd["meter_size_inches"] > 0
    assert pd["capacity_percent"] > 0
    assert pd["slip_pct_at_qmax"] < 10
    assert pd["delta_p_mbar"] > 0
    assert pd["turndown_actual"] > 0


def test_vortex_sizing():
    vx = size_vortex(6, 15000, 3000, 40, 35, 30, 1.5e-6, 0.75, True)
    assert vx["v_max_ms"] > 0
    assert vx["f_max_hz"] > 0
    assert vx["K_factor_pulses_per_m3"] > 0
    assert isinstance(vx["velocity_ok"], bool)
    assert isinstance(vx["turndown_ok"], bool)


def test_pdf_report():
    if not HAS_REPORTLAB:
        return
    SMock = namedtuple('SMock', ['meter_key','name_tr','name_en','total_score','tier_label','tier_color','categories','strengths','weaknesses','details'])
    CatMock = namedtuple('CatMock', ['score','weight','criteria'])
    CritMock = namedtuple('CritMock', ['name','score','weight','justification'])
    cat = dict.fromkeys(['technical_fitness','accuracy_metrology','operational_ease','cost','implementability','project_specific'],
                         CatMock(8.0, 0.15, []))
    sm = SMock('ultrasonic', 'USM', 'USM', 78.5, '★★☆', 'blue', cat, ['Strong'], ['Weak'], {})
    buf = generate_pdf_report({'name':'T','location':'L'}, {}, {}, sm, {}, [])
    assert len(buf.getvalue()) > 1000


def test_gc_uncertainty():
    unc = calc_uncertainty_budget('ultrasonic')
    assert 'gc_composition' in [c['name'] for c in unc['components']]
    assert unc['expanded_uncertainty_k2_95pct'] > 0


def test_material_chloride_offshore():
    mat = select_material(h2s=True, h2s_ppm=50000, has_chlorides=True, chloride_ppm=5000, offshore=True)
    assert 'Duplex' in mat['name'] or '2507' in mat['name']


def test_material_sour_only():
    mat = select_material(h2s=True, h2s_ppm=1000, has_chlorides=False, offshore=False)
    assert mat['name'] != ''


def test_i18n():
    assert 'Proje' in get_text('project', 'tr')
    assert 'Project' in get_text('project', 'en')
    assert get_text('nonexistent', 'tr') == 'nonexistent'


def test_backend_fallback():
    comp = {'C1': 0.9137, 'C2': 0.0406, 'C3': 0.0152, 'N2': 0.0102, 'CO2': 0.0203}
    r = calc_z_factor(45, 40, comp)
    assert r['Z'] > 0.1
    assert r['Z'] < 3.0
    assert r['density_kg_m3'] > 0
    assert r['backend_layer'] >= 1


def test_gas_properties_backend():
    comp = {'C1': 90, 'C2': 4, 'C3': 1.5, 'N2': 1.0, 'CO2': 2.0}
    gp = calc_gas_properties(comp, 45, 40)
    assert gp['Z_oper'] > 0.1
    assert gp['rho_oper_kg_m3'] > 0
    assert 'backend_used' in gp


def test_conditioner_scoring():
    cr = score_all_conditioners('orifice', 10, 'double_bend_out_of_plane', 3.0, 4.5)
    assert len(cr) > 0
    assert cr[0]['total_score'] >= cr[-1]['total_score']


def test_validation():
    proc_ok = {'fluid_type': 'doğal_gaz', 'nps': 8, 'design_p_bar': 50, 'oper_p_bar': 40,
               'design_t_c': 60, 'oper_t_c': 40, 'qmin': 1000, 'qmax': 10000}
    assert len(validate_process_inputs(proc_ok)) == 0

    proc_bad = {'fluid_type': 'gas', 'nps': 50, 'design_p_bar': 10, 'oper_p_bar': 40, 'qmin': 100, 'qmax': 0}
    errs = validate_process_inputs(proc_bad)
    assert len(errs) >= 3

    req_ok = {'ex_zone': 'zone_2', 'target_uncertainty': 1.0, 'ambient_min_C': 0, 'ambient_max_C': 40}
    assert len(validate_requirements(req_ok)) == 0


if __name__ == "__main__":
    for name, func in list(locals().items()):
        if name.startswith("test_"):
            try:
                func()
                print(f"✅ {name}")
            except Exception as e:
                print(f"❌ {name}: {e}")
    print("\nPhase 3 integration tests complete")
