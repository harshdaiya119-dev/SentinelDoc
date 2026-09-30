# Original User Request

## 2026-09-05T02:58:56+05:30

Build the backend engine for **SentinelDoc**, a personal data leak detector for documents. This is a hackathon project (IEEE SRM AP Hackathon, Cybersecurity Track). This phase builds only the detection engine and redaction layer — no frontend, no report generation, no 3D/UI. A frontend will be built later against these endpoints.

Working directory: ~/teamwork_projects/sentinel_doc
Integrity mode: development

### Reference Material

The full product spec and roadmap are provided below for context. **Only Phases 1 and 2 are in scope for this build.**

<details>
<summary>SPEC.md (full text)</summary>

# SentinelDoc — Personal Data Leak Detector for Documents
**Problem Statement 3 (Cybersecurity Track) — IEEE SRM AP Hackathon**

---

## 1. Problem Analysis (brief)

Organisations are supposed to scrub PII (Aadhaar, phone, email, card numbers, addresses, names) before sharing files externally. In practice this is manual and error-prone.

**What judges will actually reward, based on the constraints listed:**
- Accuracy across *varied formats*, not just clean regex-matchable text
- Not over-redacting harmless text (false-positive control)
- Quality of the redaction itself (does it look intentional, not butchered)
- Clarity of the risk report (a human should be able to act on it in seconds)
- Range of sensitive data types handled

**What most teams will ship (the floor):** a Python script with 5 regex patterns and a table. That's the thing to beat.

**Where you win:** multi-format ingestion, an NER model (not just regex) for names/addresses, confidence scoring with visible reasoning, a genuinely polished before/after redaction view, and a report a compliance officer would actually forward to their boss.

---

## 2. Core Product Definition

**One-line pitch:** *Upload any document. In seconds, SentinelDoc finds every piece of personal data hiding in it, shows you exactly why it flagged each one, and hands you back a clean, redacted copy plus a report you can forward straight to legal.*

**Inputs supported (prioritised — build in this order):**
1. `.pdf` (text-based)
2. `.docx`
3. `.csv` / `.xlsx`
4. `.txt`
5. *(Stretch)* scanned PDF / image via OCR — this is a strong differentiator if time allows

**Sensitive data classes to detect (prioritised):**
| Priority | Type | Detection method |
|---|---|---|
| Must-have | Email | Regex |
| Must-have | Phone number (Indian formats) | Regex |
| Must-have | Aadhaar number | Regex + Verhoeff checksum validation |
| Must-have | PAN number | Regex + format validation |
| Must-have | Credit/debit card number | Regex + Luhn checksum |
| Should-have | Person name | NER (spaCy / Presidio) |
| Should-have | Physical address | NER + rule-based |
| Should-have | Date of birth | Regex + context window |
| Stretch | IP address, IFSC code, passport number | Regex |
| Stretch | Bank account number | Contextual regex (near "account no.") |

**Checksum validation matters** — it's a cheap, visible way to show judges you're not "just regex." Aadhaar has a public Verhoeff algorithm; cards have Luhn. Implement both — it's ~20 lines each and directly reduces false positives (the #1 judging criterion).

---

## 6. Suggested Architecture

```
Backend
  ├─ FastAPI (Python)    → detection + redaction engine
  │    ├─ Microsoft Presidio (NER + PII recognizers) — don't reinvent NER
  │    ├─ Custom recognizers: Aadhaar (Verhoeff), PAN, card (Luhn)
  │    ├─ pdfplumber / python-docx / openpyxl → parsing
  │    └─ reportlab / fpdf2 → risk report PDF generation
```

**Why Presidio:** it's an open-source, well-known PII detection framework (regex + NER + checksum recognizers built in) — using it correctly and *extending* it with India-specific recognizers (Aadhaar/PAN) is faster than building an NER pipeline from scratch.

</details>

<details>
<summary>ROADMAP.md — Phase 1 & Phase 2 (in scope)</summary>

## Phase 1 — Detection Engine Core

**Subtasks**
- Stand up FastAPI service with a single `/scan` endpoint (accepts file, returns findings JSON)
- Integrate Microsoft Presidio (base install, default recognizers running)
- Add custom recognizer: Aadhaar (regex + Verhoeff checksum)
- Add custom recognizer: PAN (regex format validation)
- Add custom recognizer: Card number (regex + Luhn checksum)
- Wire up phone/email (Presidio defaults, tune for Indian phone formats)
- Return a structured JSON: `{type, value_snippet, location, confidence, reasoning}` per finding

## Phase 2 — Document Parsing & Redaction

**Subtasks**
- PDF parsing (pdfplumber) → extract text + coordinates per finding
- DOCX parsing (python-docx) → extract text + paragraph/run mapping
- CSV/XLSX parsing (openpyxl/pandas) → cell-level detection
- Redaction: PDF → black-box overlay at exact coordinates (not just text deletion)
- Redaction: DOCX → replace run text with `[REDACTED]` or black block styling
- Redaction: CSV → cell value replacement
- `/redact` endpoint returns the modified file (downloadable)

</details>

---

## Requirements

### R1. PII Detection Engine

A FastAPI service with a `/scan` endpoint that accepts a file upload (PDF, DOCX, CSV, XLSX, TXT) and returns structured JSON findings. Each finding must include: entity type, a snippet of the matched value, its location in the document, a confidence score (not hardcoded — must vary meaningfully by finding type and match quality), and a human-readable reasoning string explaining *why* it was flagged (e.g., "matches Aadhaar format, Verhoeff checksum valid").

Detection must use Microsoft Presidio as the NER/PII framework, extended with custom recognizers for Indian data types:
- **Aadhaar**: regex + Verhoeff checksum validation
- **PAN**: regex + format validation
- **Credit/debit card**: regex + Luhn checksum
- **Phone (Indian formats)** and **email**: tuned Presidio defaults
- **Person names** and **physical addresses**: Presidio's NER capabilities

### R2. Multi-Format Document Redaction

A `/redact` endpoint that accepts a file upload and a list of finding IDs to redact, and returns the redacted file for download. Redaction must be format-appropriate:
- **PDF**: black-box overlay at the exact coordinates of each finding (not text deletion — the layout must remain intact)
- **DOCX**: replace the matched text runs with `[REDACTED]` or apply black-block styling
- **CSV/XLSX**: replace cell values containing findings

The redacted output must look intentional — surrounding text and layout must not be broken or shifted by the redaction.

### R3. Architecture Constraints

Follow the architecture from SPEC.md §6: FastAPI backend, Presidio for detection, pdfplumber for PDF parsing, python-docx for DOCX, openpyxl for spreadsheets. The API contract between `/scan` and `/redact` should be clean enough that a React frontend can be built against it later without backend changes.

---

## Acceptance Criteria

### Detection Accuracy
- [ ] The `/scan` endpoint correctly identifies all must-have PII types (email, phone, Aadhaar, PAN, credit/debit card) in a test document containing known planted instances of each type
- [ ] Aadhaar detection validates using the Verhoeff checksum algorithm — a valid Aadhaar passes, an invalid one (single digit changed) does not
- [ ] Card number detection validates using the Luhn algorithm — a valid card number passes, a random 16-digit number does not
- [ ] PAN detection validates format (5 letters, 4 digits, 1 letter pattern) — rejects strings that are 10 alphanumeric characters but don't match the PAN pattern
- [ ] Confidence scores vary meaningfully across findings (not all the same value)
- [ ] Each finding includes a non-empty reasoning string that explains the detection method used

### False-Positive Control
- [ ] A test document containing numbers that resemble but are NOT PII (order IDs, zip codes, 10-digit non-phone numbers, random 12-digit numbers failing Verhoeff) does not produce false positives for Aadhaar, PAN, or card number types

### Multi-Format Support
- [ ] `/scan` successfully parses and returns findings from at least: one PDF, one DOCX, one CSV or XLSX file
- [ ] `/redact` produces a downloadable output file for each supported format
- [ ] A redacted PDF, when opened, has intact layout with black-box overlays covering only the flagged regions
- [ ] A redacted DOCX, when opened, shows `[REDACTED]` or black blocks only at flagged positions without breaking surrounding formatting

### API Contract
- [ ] Both endpoints return well-structured JSON responses with consistent schema
- [ ] Error cases (unsupported file type, empty file, malformed upload) return appropriate HTTP status codes and human-readable error messages, not stack traces
- [ ] The `/scan` response includes enough location information (page/paragraph/cell coordinates) that a frontend could highlight findings in a document preview

### Automated Verification
- [ ] A test script exists that can be run with a single command to exercise both endpoints against sample documents and verify the above criteria programmatically
- [ ] The test script includes at least one false-positive test case (document with PII-like-but-not-PII numbers) and verifies they are NOT flagged

## 2026-09-04T22:30:06Z

Build Phase 3 (risk report generation) and Phase 4 (React + Vite frontend) of **SentinelDoc**, a personal data leak detector for documents. This is a hackathon submission (IEEE SRM AP Hackathon, Cybersecurity Track) targeting demo quality — needs to impress judges in a live demo.

Phases 1 and 2 (FastAPI detection engine + redaction layer) are already complete and running. The new team must build on top of the existing backend without modifying its `/scan` or `/redact` endpoints.

Working directory: /Users/harsh/Downloads/New Folder With Items
Integrity mode: development

---

## Existing Backend — API Contract (do not change)

The backend runs via `uvicorn app.main:app`. All endpoints are defined in `app/main.py`. The Pydantic schemas are in `app/models/schemas.py`.

### `POST /scan`
Accepts: `multipart/form-data` with `file` (PDF, DOCX, CSV, XLSX, TXT)
Returns: `ScanResponse`
```json
{
  "file_name": "string",
  "file_type": "string",
  "total_findings": 0,
  "findings": [
    {
      "id": "find_1",
      "entity_type": "AADHAAR | PAN | CREDIT_CARD | PHONE | EMAIL | PERSON | ADDRESS | DATE_OF_BIRTH",
      "matched_text": "string",
      "confidence": 0.95,
      "reasoning": "matches Aadhaar format, Verhoeff checksum valid",
      "location": {
        "page": 1,
        "bbox": { "x0": 0, "top": 0, "x1": 100, "bottom": 20 },
        "paragraph_index": null,
        "sheet_name": null,
        "cell": null,
        "row": null,
        "col": null,
        "line": null,
        "start_char": 0,
        "end_char": 12
      }
    }
  ]
}
```

### `POST /redact`
Accepts: `multipart/form-data` with `file` + optional `finding_ids` (JSON array string or `"all"`)
Returns: Binary file download (`redacted_<filename>`)

### `GET /health`
Returns: `{ "status": "healthy", "app": "SentinelDoc", "version": "..." }`

---

## Requirements

### R1. Risk Report Generation (Phase 3)

Add a `/report` endpoint to the existing FastAPI backend (extend `app/main.py` or add a new router). The endpoint accepts a file upload, runs `/scan` internally, computes a risk score, and returns both a JSON summary and a downloadable PDF report.

The risk score must be weighted by data type severity and count (e.g. Aadhaar/card numbers are higher severity than email). The PDF report must be readable by a non-technical compliance officer in under 10 seconds: overall risk score, counts by entity type, and a per-finding detail table. It must look clean and professional — not a raw data dump. Use `reportlab` or `fpdf2`.

The `/report` JSON response must include enough data for the frontend to render a risk gauge (overall score 0–100 and a risk level: Low / Medium / High) and a collapsible findings table.

### R2. React + Vite Frontend (Phase 4)

Build a React + Vite frontend that implements the full 5-screen user flow from the spec below, wired to the real backend endpoints. The frontend must match the design direction exactly:

- **Palette**: near-black/deep slate background (`#0B0F14`–`#12161C`), off-white text (`#EDEFF2`), single accent in electric teal (`#2DD4BF`) or amber (`#F5A524`) for risk states (green/amber/red = low/medium/high)
- **Typography**: `Inter` or `Geist` for UI; `JetBrains Mono` or `IBM Plex Mono` for data/numbers
- **Layout**: thin 1px borders, no glassmorphism, no rounded-pill buttons, 4–6px radii, generous whitespace
- **Motion**: Framer Motion, 150–250ms transitions, no bounce — communicates state change only
- **Icons**: Lucide or Phosphor, never mixed with emoji

The five screens:
1. **Upload** — single centered drop zone, accepts PDF/DOCX/CSV/XLSX/TXT, shows file type icon/preview on drop
2. **Scanning** — live scan visualization + streaming log of what's being checked; must feel like real work being done
3. **Findings Review** — findings grouped by entity type, each with confidence and location; user can toggle individual findings on/off before redaction
4. **Redaction Preview** — before/after slider over the rendered document (use `react-pdf` for PDF, `mammoth` for DOCX preview)
5. **Report & Download** — risk gauge (radial, animated fill), summary counts, "Download redacted file" + "Download risk report (PDF)" buttons

All screens connect to real backend endpoints — no mock data by the end of Phase 4.

### R3. 3D Hero Element (Stretch — implement only after R1 and R2 are solid)

A React Three Fiber element on the idle/upload screen: a slowly rotating low-poly shield or document stack, subtly reactive to mouse movement. Used only on the landing screen, never blocks the workflow. If time is short, skip this entirely.

### R4. Design Constraints

The spec explicitly prohibits:
- Purple-to-blue gradient backgrounds
- Glassmorphism cards
- Generic rocket/sparkle icons
- Poppins or Space Grotesk fonts
- Gratuitous 3D beyond the single hero element

Reference aesthetic: Vercel dashboard / Linear / SOC monitoring tool.

---

## Acceptance Criteria

### Risk Report (Phase 3)
- [ ] `POST /report` returns a JSON body with: `risk_score` (0–100 integer), `risk_level` ("Low" / "Medium" / "High"), `findings_by_type` (count per entity type), and the full findings list
- [ ] `POST /report` returns a downloadable PDF report (via `Content-Disposition: attachment`) that includes: overall risk score, entity type summary table, and per-finding detail rows
- [ ] Risk score changes meaningfully when findings are added/removed (not a fixed formula that always returns 75)
- [ ] PDF report is readable and structured — not a raw JSON dump or wall of text

### Frontend Functionality (Phase 4)
- [ ] A user unfamiliar with the project can complete Upload → Scan → Review → Redact → Download without being told what to click
- [ ] The app never shows raw JSON or an unstyled error to the user
- [ ] Finding toggles on the Findings Review screen actually affect which regions are redacted in the downloaded file
- [ ] The before/after slider renders the actual document (not a placeholder image)
- [ ] Risk gauge animates on load and reflects the actual backend risk score
- [ ] Both "Download redacted file" and "Download risk report (PDF)" buttons produce valid, openable files

### Design Quality
- [ ] No default Tailwind purple, gradient backgrounds, glassmorphism, or pill buttons appear anywhere in the app
- [ ] Monospace font is used for all numeric data values (confidence scores, finding counts, risk score number)
- [ ] The scan screen shows a meaningful log of steps being checked (not just a spinner)
- [ ] Color-coded risk states: teal/green = Low, amber = Medium, red = High

### Automated Verification
- [ ] A single command starts the full application (backend + frontend) locally
- [ ] Existing `./run_tests.sh` still passes after Phase 3 additions (backend must not be broken)
