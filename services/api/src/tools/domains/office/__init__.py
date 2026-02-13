"""
Office Domain Tools - Herramientas para generación de documentos Office

Tools:
- generate_spreadsheet: Genera archivos Excel (.xlsx) desde datos JSON
"""

from .generate_spreadsheet import generate_spreadsheet, GENERATE_SPREADSHEET_TOOL

OFFICE_TOOLS = {
    "generate_spreadsheet": GENERATE_SPREADSHEET_TOOL
}

__all__ = [
    "OFFICE_TOOLS",
    "generate_spreadsheet",
    "GENERATE_SPREADSHEET_TOOL"
]
