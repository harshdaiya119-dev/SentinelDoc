# Project: SentinelDoc (Phase 3 & Phase 4)

## Architecture
SentinelDoc is a high-assurance personal data leak detector and compliance reporting platform.
- **Backend (FastAPI, Python 3.9)**:
  - Detection Core: Microsoft Presidio, custom Verhoeff (Aadhaar) and Luhn (Card) checksum algorithms, PAN regex (5L+4D+1L), Indian phone/email heuristics, spaCy NER.
  - Multi-Format Redaction: Native PDF vector overlays, DOCX run replacements, CSV/XLSX cell masking, TXT replacement.
  - Risk Scoring Engine (`app/core/risk.py`): Severity-weighted sublinear scoring normalized to [0, 100] mapping to Low / Medium / High.
  - PDF Report Generator (`app/core/pdf_report.py`): Professional ReportLab Platypus compliance audit report with executive metrics, risk gauge badge, entity breakdown, and finding audit trails.
  - API Endpoints: `POST /scan`, `POST /redact`, `POST /report` (dual JSON/PDF mode), `GET /health`.
- **Frontend (React 18 + Vite 5 + TypeScript + Tailwind CSS)**:
  - 5-Screen Workflow: Upload Dropzone -> Scanning Telemetry Log -> Grouped Findings Review -> Before/After Redaction Preview Slider -> Executive Report & Download.
  - Design Aesthetic: Dark Slate SOC Console (`#0B0F14` - `#12161C`), 1px borders (`#21262D`), Electric Teal (`#2DD4BF`), Amber (`#F5A524`), Crimson (`#EF4444`), Inter UI font, JetBrains Mono numeric data. Zero pill buttons, zero purple gradients, zero glassmorphism.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | PII Detection Engine Core | Existing Presidio + Custom Recognizers for Aadhaar, PAN, Cards, Phone, Email, Person, Address | M1 (Done) | Phase 1 |
| 2 | Multi-Format Redaction | Existing PDF, DOCX, CSV, XLSX, TXT redactors | M2 (Done) | Phase 2 |
| 3 | Mathematical Risk Scoring Engine | Weighted scoring ($W_e$), sublinear count decay, normalized to 0-100, Low/Medium/High categorization | M3 (Done) | survey_spec_miner_p34 |
| 4 | Executive Risk Metadata Summary | Breakdown counts by severity tiers (Critical, High, Medium, Low), dominant exposure threat description | M3 (Done) | survey_spec_miner_p34 |
| 5 | Dual-Mode POST /report Endpoint | Content negotiation via `format` param & `Accept` header (JSON `ReportResponse` vs binary PDF) | M3 (Done) | survey_backend_p34 |
| 6 | In-Process Scanning Reuse | Call `scan_document` directly within `/report` without HTTP overhead or modifying `/scan`/`/redact` | M3 (Done) | survey_backend_p34 |
| 7 | ReportLab Compliance PDF Synthesis | Platypus document template, dark modern header, executive metrics box, risk gauge visual, entity summary table | M3 (Done) | survey_backend_p34 |
| 8 | Dynamic NumberedCanvas Pagination | Multi-page audit table with "Page X of Y" running footers and timestamped compliance disclaimer | M3 (Done) | survey_backend_p34 |
| 9 | Privacy-Masked PDF Audit Table | Document location, confidence, rule explanation, with masked PII strings for legal safe-harbor | M3 (Done) | survey_spec_miner_p34 |
| 10 | Frontend Scaffolding & Design System | Vite + React + TS + Tailwind with strict SOC dark slate palette, typography, and 1px borders | M4 | survey_frontend_p34 |
| 11 | Screen 1: Agnostic Upload Dropzone | Drag-and-drop file target with format validation (PDF, DOCX, CSV, XLSX, TXT), size limits, file icons | M4 | survey_spec_miner_p34 |
| 12 | Screen 2: Real-Feel Scanning Telemetry | Multi-stage progress tracking (Parsing -> NER -> Checksums -> Correlation -> Scoring) with streaming log | M4 | survey_spec_miner_p34 |
| 13 | Screen 3: Grouped Findings Review | Findings grouped by entity type, confidence badges, reasoning tooltips, selective redaction checkboxes | M4 | survey_spec_miner_p34 |
| 14 | Screen 4: Before/After Redaction Slider | Interactive split comparison slider rendering original document vs redacted document | M4 | survey_frontend_p34 |
| 15 | Screen 5: Executive Report & Risk Gauge | Radial animated risk score gauge (0-100), risk badge, entity count cards, compliance recommendation | M4 | survey_spec_miner_p34 |
| 16 | Dual Artifact Download Actions | "Download Redacted Document" (respecting selective checkboxes) and "Download Risk Report (PDF)" | M4 | survey_spec_miner_p34 |
| 17 | Zero Mock Data Production Wiring | Complete end-to-end connection between React UI and live FastAPI `/scan`, `/redact`, `/report` endpoints | M4 | survey_frontend_p34 |
| 18 | Frontend Test Suite | Vitest / React Testing Library component tests covering all 5 screens and user flows | M4 | survey_spec_miner_p34 |
| 19 | Unified Single-Command Runner | `run_all.sh` launching backend and frontend concurrently with graceful signal trapping | M4 | survey_frontend_p34 |
| 20 | Non-Regression Verification | Ensure all existing 238 tests in `./run_tests.sh` pass alongside all Phase 3 & 4 additions | Final | survey_backend_p34 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Test harness & cases for Phase 3 (/report JSON & PDF) & Phase 4 | Survey Complete | DONE (55 tests, 293 total passing) |
| M3 | Risk Report Generation (Phase 3 Backend) | `reportlab` install, `app/core/risk.py`, `app/core/pdf_report.py`, `POST /report` endpoint, unit/endpoint tests | Survey Complete | DONE (Passed Gate) |
| M4 | React + Vite Frontend (Phase 4) | Full 5-screen flow, strict SOC dark palette, document preview slider, live backend wiring, run_all.sh | M3 | IN_PROGRESS |
| Final | 100% E2E Verification & Victory Audit | Full verification (backend 293+ tests, frontend tests, run_all.sh), Victory Audit | M4 | PLANNED |

## Interface Contracts

### Backend: POST /report
- Request: `multipart/form-data` with `file: UploadFile` and optional `format: str` (`"json"` or `"pdf"`).
- Query/Header: Supports `?format=pdf` or `Accept: application/pdf` for binary stream; `?format=json` or `Accept: application/json` for JSON.
- Response (JSON, 200 OK):
```json
{
  "file_name": "string",
  "file_type": "string",
  "risk_score": 85,
  "risk_level": "High",
  "total_findings": 4,
  "findings_by_type": { "AADHAAR": 1, "PAN": 1, "PHONE": 1, "EMAIL": 1 },
  "findings": [ { "id": "find_1", "entity_type": "AADHAAR", "matched_text": "...", "confidence": 0.95, "reasoning": "...", "location": { ... } } ],
  "summary": {
    "critical_count": 1,
    "high_count": 1,
    "medium_count": 1,
    "low_count": 1,
    "primary_threat": "string",
    "compliance_verdict": "string"
  }
}
```
- Response (PDF, 200 OK):
  - Content-Type: `application/pdf`
  - Content-Disposition: `attachment; filename="SentinelDoc_Risk_Report_<filename>.pdf"`

### Frontend ↔ Backend Integration
- Scan call: `POST /scan` -> returns `ScanResponse` -> feeds Scanning & Findings Review screens.
- Redact call: `POST /redact` with `finding_ids` -> returns redacted file blob -> feeds Redaction Preview & Download.
- Report call: `POST /report?format=json` -> returns `ReportResponse` -> feeds Executive Report gauge & cards; `POST /report?format=pdf` -> downloads PDF.

## Code Layout
- `app/core/risk.py`: Risk scoring mathematics, severity tiers, count scaling, category mapping.
- `app/core/pdf_report.py`: ReportLab Platypus compliance PDF generation.
- `app/models/schemas.py`: `RiskSummary`, `ReportResponse` Pydantic models.
- `app/main.py`: Include `/report` endpoint (or import router).
- `frontend/`: React + Vite + TypeScript application.
  - `src/components/`: Modular UI widgets (Dropzone, ScanLog, FindingsGroup, RedactionSlider, RiskGauge, DownloadBar).
  - `src/screens/`: Screen components for the 5 linear steps.
  - `src/services/api.ts`: Typed API client for `/scan`, `/redact`, `/report`.
  - `src/types/`: TypeScript interfaces mirroring backend schemas.
- `run_all.sh`: Unified startup script.
- `run_tests.sh`: Unified test runner.
