"""
Report generation module for metering station designer.
Provides Excel (.xlsx) and PDF report generators.
"""

from .excel_report import generate_excel_report
from .pdf_report import generate_pdf_report, generate_pdf_from_results, HAS_WEASYPRINT

__all__ = [
    "generate_excel_report",
    "generate_pdf_report",
    "generate_pdf_from_results",
    "HAS_WEASYPRINT",
]
