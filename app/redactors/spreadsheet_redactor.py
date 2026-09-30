"""Spreadsheet redactor for XLSX and CSV files with cell value replacement."""
import io
import csv
from typing import Dict, List, Optional, Set, Tuple
import openpyxl
from openpyxl.cell.cell import MergedCell
from app.models.schemas import Finding
from .base import BaseRedactor


def _redact_in_text(
    text: str,
    target_text: str,
    start_char: Optional[int] = None,
    end_char: Optional[int] = None,
) -> str:
    """Replace a specific occurrence of target_text with [REDACTED] in text."""
    if not target_text or target_text not in text:
        return text

    if (
        start_char is not None
        and end_char is not None
        and 0 <= start_char < end_char <= len(text)
        and text[start_char:end_char] == target_text
    ):
        return text[:start_char] + "[REDACTED]" + text[end_char:]

    # If start_char is provided, find occurrence closest to start_char
    if start_char is not None:
        positions = []
        idx = text.find(target_text)
        while idx != -1:
            positions.append(idx)
            idx = text.find(target_text, idx + 1)
        if positions:
            closest_pos = min(positions, key=lambda p: abs(p - start_char))
            return text[:closest_pos] + "[REDACTED]" + text[closest_pos + len(target_text):]

    # Fallback: replace only the first occurrence
    return text.replace(target_text, "[REDACTED]", 1)


class SpreadsheetRedactor(BaseRedactor):
    """Redacts XLSX and CSV files replacing sensitive cell values with [REDACTED]."""

    def redact(
        self,
        content: bytes,
        file_name: str,
        findings: List[Finding],
        target_finding_ids: Optional[Set[str]] = None,
    ) -> bytes:
        """Dispatch redaction based on file extension (.xlsx vs .csv)."""
        lower_name = file_name.lower()
        if lower_name.endswith(".csv"):
            return self._redact_csv(content, findings, target_finding_ids)
        elif lower_name.endswith(".xlsx"):
            return self._redact_xlsx(content, findings, target_finding_ids)
        else:
            raise ValueError(f"Unsupported spreadsheet format: {file_name}")

    def _redact_csv(
        self,
        content: bytes,
        findings: List[Finding],
        target_finding_ids: Optional[Set[str]] = None,
    ) -> bytes:
        """Redact sensitive cells in CSV format preserving rows and quotes."""
        if target_finding_ids is not None:
            to_redact = [f for f in findings if f.id in target_finding_ids]
        else:
            to_redact = list(findings)

        try:
            text_data = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text_data = content.decode("latin-1")
            except Exception as e:
                raise ValueError(f"Failed to decode CSV content: {e}") from e

        rows = list(csv.reader(io.StringIO(text_data)))

        # Group findings by cell coordinate (row, col)
        cell_findings: Dict[Tuple[int, int], List[Finding]] = {}
        unassigned: List[Finding] = []

        for f in to_redact:
            assigned = False
            if f.location and f.location.row is not None and f.location.col is not None:
                r_idx = f.location.row - 1
                c_idx = f.location.col - 1
                if 0 <= r_idx < len(rows) and 0 <= c_idx < len(rows[r_idx]):
                    cell_findings.setdefault((r_idx, c_idx), []).append(f)
                    assigned = True
            if not assigned:
                unassigned.append(f)

        # Process each cell with findings sorted by start_char descending
        for (r_idx, c_idx), f_list in cell_findings.items():
            cell_str = rows[r_idx][c_idx]

            def get_sort_key(item: Finding) -> int:
                if item.location and item.location.start_char is not None:
                    return item.location.start_char
                pos = cell_str.find(item.matched_text)
                return pos if pos != -1 else 0

            f_list.sort(key=get_sort_key, reverse=True)

            for f in f_list:
                s_char = f.location.start_char if f.location else None
                e_char = f.location.end_char if f.location else None
                cell_str = _redact_in_text(cell_str, f.matched_text, s_char, e_char)

            rows[r_idx][c_idx] = cell_str

        # Fallback for unassigned findings
        for f in unassigned:
            if not f.matched_text:
                continue
            s_char = f.location.start_char if f.location else None
            e_char = f.location.end_char if f.location else None
            redacted = False
            for r in rows:
                for c_idx in range(len(r)):
                    if f.matched_text in r[c_idx]:
                        r[c_idx] = _redact_in_text(r[c_idx], f.matched_text, s_char, e_char)
                        redacted = True
                        break
                if redacted:
                    break

        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerows(rows)
        return out.getvalue().encode("utf-8")

    def _redact_xlsx(
        self,
        content: bytes,
        findings: List[Finding],
        target_finding_ids: Optional[Set[str]] = None,
    ) -> bytes:
        """Redact sensitive cells in XLSX workbook preserving formulas and structure."""
        if target_finding_ids is not None:
            to_redact = [f for f in findings if f.id in target_finding_ids]
        else:
            to_redact = list(findings)

        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=False)
        except Exception as e:
            raise ValueError(f"Failed to open XLSX workbook: {e}") from e

        try:
            # Group findings by (sheet_name, row, col)
            cell_findings: Dict[Tuple[str, int, int], List[Finding]] = {}
            unassigned: List[Finding] = []

            for f in to_redact:
                assigned = False
                sheet_name = f.location.sheet_name if f.location else None
                row = f.location.row if f.location else None
                col = f.location.col if f.location else None

                if sheet_name and sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    if row and col:
                        cell_findings.setdefault((sheet_name, row, col), []).append(f)
                        assigned = True
                    elif f.location and f.location.cell and f.location.cell in ws:
                        c = ws[f.location.cell]
                        cell_findings.setdefault((sheet_name, c.row, c.column), []).append(f)
                        assigned = True

                if not assigned:
                    unassigned.append(f)

            # Process grouped cells
            for (sheet_name, row_idx, col_idx), f_list in cell_findings.items():
                ws = wb[sheet_name]
                cell = ws.cell(row=row_idx, column=col_idx)
                if isinstance(cell, MergedCell):
                    for rng in ws.merged_cells.ranges:
                        if cell.coordinate in rng:
                            cell = ws.cell(row=rng.min_row, column=rng.min_col)
                            break

                if cell.value is None:
                    continue

                cell_str = str(cell.value)
                if cell_str.startswith("="):
                    continue

                def get_x_sort_key(item: Finding) -> int:
                    if item.location and item.location.start_char is not None:
                        return item.location.start_char
                    pos = cell_str.find(item.matched_text)
                    return pos if pos != -1 else 0

                f_list.sort(key=get_x_sort_key, reverse=True)

                for f in f_list:
                    s_char = f.location.start_char if f.location else None
                    e_char = f.location.end_char if f.location else None
                    cell_str = _redact_in_text(cell_str, f.matched_text, s_char, e_char)

                cell.value = cell_str

            # Fallback for unassigned
            for f in unassigned:
                matched_text = f.matched_text
                if not matched_text:
                    continue
                s_char = f.location.start_char if f.location else None
                e_char = f.location.end_char if f.location else None
                redacted = False
                for sname in wb.sheetnames:
                    ws = wb[sname]
                    for row_cells in ws.iter_rows():
                        for c in row_cells:
                            if c.value is not None and matched_text in str(c.value):
                                if isinstance(c, MergedCell):
                                    for rng in ws.merged_cells.ranges:
                                        if c.coordinate in rng:
                                            c = ws.cell(row=rng.min_row, column=rng.min_col)
                                            break
                                c_str = str(c.value)
                                if c_str.startswith("="):
                                    continue
                                c.value = _redact_in_text(c_str, matched_text, s_char, e_char)
                                redacted = True
                                break
                        if redacted:
                            break
                    if redacted:
                        break

            buf = io.BytesIO()
            wb.save(buf)
            return buf.getvalue()
        finally:
            wb.close()
