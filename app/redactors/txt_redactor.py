"""Plain text redactor with line break and character span preservation."""
from typing import List, Optional, Set, Dict
from app.models.schemas import Finding
from .base import BaseRedactor


class TxtRedactor(BaseRedactor):
    """Redacts plain text files replacing character spans or matched lines with [REDACTED]."""

    def redact(
        self,
        content: bytes,
        file_name: str,
        findings: List[Finding],
        target_finding_ids: Optional[Set[str]] = None,
    ) -> bytes:
        """Replace sensitive findings in plain text with [REDACTED] preserving line breaks."""
        if target_finding_ids is not None:
            to_redact = [f for f in findings if f.id in target_finding_ids]
        else:
            to_redact = list(findings)

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    text = content.decode("latin-1")
                except Exception as e:
                    raise ValueError(f"Failed to decode text file: {e}") from e

        # Keep original line breaks intact
        lines = text.splitlines(keepends=True)

        # Group findings by 0-indexed line
        line_findings: Dict[int, List[Finding]] = {}
        unassigned: List[Finding] = []

        for f in to_redact:
            if f.location and f.location.line is not None:
                l_idx = f.location.line - 1
                if 0 <= l_idx < len(lines):
                    line_findings.setdefault(l_idx, []).append(f)
                else:
                    unassigned.append(f)
            else:
                unassigned.append(f)

        # Process each line with findings
        for l_idx, f_list in line_findings.items():
            line_str = lines[l_idx]

            # Sort findings by start_char descending so rightmost spans are replaced first
            def get_sort_key(item: Finding) -> int:
                if item.location and item.location.start_char is not None:
                    return item.location.start_char
                pos = line_str.find(item.matched_text)
                return pos if pos != -1 else 0

            f_list.sort(key=get_sort_key, reverse=True)

            for f in f_list:
                s_char = f.location.start_char if f.location else None
                e_char = f.location.end_char if f.location else None
                m_text = f.matched_text

                # Check if exact span matches
                if s_char is not None and e_char is not None and 0 <= s_char < e_char <= len(line_str):
                    if line_str[s_char:e_char] == m_text:
                        line_str = line_str[:s_char] + "[REDACTED]" + line_str[e_char:]
                        continue

                # Otherwise replace by string match
                if m_text and m_text in line_str:
                    last_pos = line_str.rfind(m_text)
                    if last_pos != -1:
                        line_str = line_str[:last_pos] + "[REDACTED]" + line_str[last_pos + len(m_text):]

            lines[l_idx] = line_str

        # Process any unassigned findings
        full_text = "".join(lines)
        for f in unassigned:
            if f.matched_text and f.matched_text in full_text:
                full_text = full_text.replace(f.matched_text, "[REDACTED]")

        return full_text.encode("utf-8")
