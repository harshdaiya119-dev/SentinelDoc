# E2E Test Infra: SentinelDoc Phase 3 & Phase 4

## Test Philosophy
- Multi-tier opaque-box and requirement-driven testing.
- Ensure strict zero-regression guarantee on all 238 existing tests.
- Verify Phase 3 Risk Scoring mathematics, JSON API, and ReportLab PDF binary generation.
- Verify Phase 4 Frontend component rendering, user workflow, and API client contracts.

## Test Tiers & Methodology
- **Existing Suite**: 238 tests covering PII detection, Verhoeff/Luhn checksums, multi-format redactors, boundary conditions, false positive controls.
- **Phase 3 Test Additions**:
  - Unit tests for risk scoring engine (`tests/test_risk_engine.py`):
    * Monotonicity: adding findings strictly increases or maintains score.
    * Diminishing returns: multiple occurrences scale sublinearly.
    * Severity weighting: Tier 1 (Aadhaar/Card) produces significantly higher risk than Tier 4 (Email/Person).
    * Zero-finding test: documents with 0 findings yield score = 0, level = "Low".
    * Threshold accuracy: Low (0-39), Medium (40-69), High (70-100).
  - Integration tests for `/report` endpoint (`tests/test_report_endpoint.py`):
    * JSON output validation: verifies `ReportResponse` schema, entity counts, confidence scores.
    * PDF output validation: verifies HTTP 200, `Content-Type: application/pdf`, valid PDF binary header `%PDF-1.4`, non-zero size, attachment header.
    * Error handling: invalid files, empty files return 400 with standardized error envelope.
- **Phase 4 Test Additions**:
  - Frontend Vitest tests (`frontend/tests/`):
    * Screen 1 (Upload): file drag/drop handling, format filtering.
    * Screen 2 (Scanning): telemetry stream, progress bar updates.
    * Screen 3 (Findings): grouping by entity type, checkbox toggle updates state.
    * Screen 4 (Preview): slider drag updates split position.
    * Screen 5 (Report): radial gauge animates to score, download buttons trigger correct actions.

## Single-Command Verification Runner
- Backend: `./run_tests.sh` executes all backend tests (target: 250+ passing tests).
- Frontend: `cd frontend && npm test` executes all frontend tests.
- Full System: `./run_all.sh` boots both backend and frontend.
