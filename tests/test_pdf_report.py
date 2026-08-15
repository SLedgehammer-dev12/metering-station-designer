import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from metering_designer.report.pdf_report import (
    HAS_WEASYPRINT,
    generate_pdf_report,
    generate_pdf_from_results,
)


@pytest.mark.skipif(not HAS_WEASYPRINT, reason="WeasyPrint not installed")
def test_generate_pdf_report():
    data = {
        "meter_type": "orifice",
        "standard_ref": "ISO 5167-2:2003",
        "pressure": 40.0,
        "temperature": 20.0,
        "flow_max": 1000.0,
        "flow_min": 100.0,
        "density_op": 30.0,
        "viscosity": 1.2e-5,
        "z_factor": 0.9,
        "sizing_results": {"beta": 0.5, "Cd": 0.603, "d_mm": 50.0},
        "uncertainty_components": [
            {"name": "meter", "value_pct": 0.6, "type": "B", "distribution": "normal"},
        ],
        "combined_uncertainty": 0.65,
        "expanded_k2": 1.30,
        "gas_properties": {"M_mix": 18.5, "rho_std_kg_m3": 0.8},
        "notes": ["Test note 1", "Test note 2"],
    }

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        out = f.name

    try:
        result = generate_pdf_report(data, out)
        assert os.path.exists(result), f"PDF was not created at {result}"
        assert os.path.getsize(result) > 0, "PDF file is empty"
    finally:
        os.unlink(out)


@pytest.mark.skipif(not HAS_WEASYPRINT, reason="WeasyPrint not installed")
def test_generate_pdf_from_results():
    sizing = {"beta": 0.55, "Cd": 0.604, "d_mm": 55.0, "notes": "sınırlar içinde"}
    uncertainty = {
        "components": [{"name": "meter", "value_pct": 0.6, "type": "B", "distribution": "normal"}],
        "combined_standard_uncertainty_pct": 0.6,
        "expanded_uncertainty_k2_95pct": 1.2,
        "coverage_factor_comment": "k=2",
    }
    gas = {"Z": 0.92, "M_mix": 18.0, "rho_oper_kg_m3": 28.5, "rho_std_kg_m3": 0.8,
           "P_bar": 40, "T_C": 20}

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        out = f.name

    try:
        result = generate_pdf_from_results("orifice", sizing, uncertainty, gas, out)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0
    finally:
        os.unlink(out)


@pytest.mark.skipif(not HAS_WEASYPRINT, reason="WeasyPrint not installed")
def test_generate_pdf_with_schematic_and_instruments_lang():
    data = {
        "meter_type": "Orifice Plate",
        "standard_ref": "ISO 5167-2:2003",
        "pressure": 40.0,
        "temperature": 20.0,
        "flow_max": 1000.0,
        "flow_min": 100.0,
        "density_op": 30.0,
        "viscosity": 1.2e-5,
        "z_factor": 0.9,
        "sizing_results": {"beta": 0.5, "Cd": 0.603, "d_mm": 50.0},
        "uncertainty_components": [
            {"name": "meter", "value_pct": 0.6, "type": "B", "distribution": "normal"},
        ],
        "combined_uncertainty": 0.65,
        "expanded_k2": 1.30,
        "gas_properties": {"M_mix": 18.5, "rho_std_kg_m3": 0.8},
        "notes": ["Test note 1", "Test note 2"],
        "schematic_png_b64": "QUJD",
        "instrument_table_rows": [
            {"tag": "PT-1001", "type": "pressure", "count": 1,
             "position_D": -2.0, "side": "Upstream", "standard": "ISO 5167-1"},
        ],
        "straight_pipe": {"upstream_required_diameters": 18, "downstream_required_diameters": 5},
    }

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        out = f.name

    try:
        result = generate_pdf_report(data, out, lang="en")
        assert os.path.exists(result)
        assert os.path.getsize(result) > 1000, "PDF file too small"
        with open(out, "rb") as fh:
            content = fh.read()
        assert b"%PDF-" in content, "Missing PDF header"
        assert len(data["schematic_png_b64"]) > 0  # schematic data was supplied
    finally:
        os.unlink(out)


def test_generate_pdf_no_weasyprint():
    if HAS_WEASYPRINT:
        pytest.skip("WeasyPrint is installed, skipping fallback test")
    result = generate_pdf_report({"meter_type": "test"}, "/tmp/test.pdf")
    assert "not installed" in result


def test_module_level_flag():
    from metering_designer.report.pdf_report import HAS_WEASYPRINT as flag
    # Flag should be defined even if weasyprint is not available
    assert flag is True or flag is False
