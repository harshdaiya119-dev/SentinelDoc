"""Pydantic schemas for request, response, and findings models."""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates for PDF rendering and redaction."""
    x0: float = Field(..., description="Left horizontal coordinate")
    top: float = Field(..., description="Top vertical coordinate")
    x1: float = Field(..., description="Right horizontal coordinate")
    bottom: float = Field(..., description="Bottom vertical coordinate")


class Location(BaseModel):
    """Multi-format location descriptor."""
    page: Optional[int] = Field(None, description="1-indexed page number for PDFs")
    bbox: Optional[BoundingBox] = Field(None, description="Bounding box on page for PDFs")
    paragraph_index: Optional[int] = Field(None, description="0-indexed paragraph number for DOCX")
    sheet_name: Optional[str] = Field(None, description="Sheet name for spreadsheets")
    cell: Optional[str] = Field(None, description="Cell reference (e.g. A1, C4) for spreadsheets")
    row: Optional[int] = Field(None, description="1-indexed row number for spreadsheets")
    col: Optional[int] = Field(None, description="1-indexed column number for spreadsheets")
    line: Optional[int] = Field(None, description="1-indexed line number for TXT")
    start_char: Optional[int] = Field(None, description="Character start offset in context")
    end_char: Optional[int] = Field(None, description="Character end offset in context")


class Finding(BaseModel):
    """Individual PII entity finding."""
    id: str = Field(..., description="Unique finding ID, e.g. find_1")
    entity_type: str = Field(..., description="Entity classification (e.g. AADHAAR, PAN, CREDIT_CARD)")
    matched_text: str = Field(..., description="Exact or snippet text matched")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score calibrated between 0.0 and 1.0")
    reasoning: str = Field(..., description="Human-readable explanation of detection and validation")
    location: Location = Field(..., description="Location of the finding within the document")


class ScanResponse(BaseModel):
    """Response envelope for POST /scan endpoint."""
    file_name: str
    file_type: str
    total_findings: int
    findings: List[Finding]


RiskLevel = Literal["Low", "Medium", "High"]


class RiskSummary(BaseModel):
    """Executive risk breakdown and compliance verdict."""
    critical_count: int = Field(..., description="Count of Tier 1 findings (Aadhaar, Credit Card)")
    high_count: int = Field(..., description="Count of Tier 2 findings (PAN, Date of Birth)")
    medium_count: int = Field(..., description="Count of Tier 3 findings (Phone, Address)")
    low_count: int = Field(..., description="Count of Tier 4 findings (Email, Person)")
    primary_threat: str = Field(..., description="Dominant exposure threat description")
    compliance_verdict: str = Field(..., description="Actionable regulatory recommendation")


class VerifyIdResponse(BaseModel):
    """Response envelope for POST /verify-id endpoint."""
    is_real: bool = Field(..., description="True if QR code or hologram indicates authentic Govt ID")
    status_category: str = Field(default="NOT_FOUND", description="Category: REAL_GOVT_ID, GOVT_ID_NOT_FOUND, FAKE_CARD, NOT_FOUND")
    face_found: bool = Field(..., description="True if a human face is detected in the ID photo")
    qr_found: bool = Field(..., description="True if a QR code is detected")
    hologram_found: bool = Field(default=False, description="True if a hologram or metallic security foil is detected")
    message: str = Field(..., description="Human-readable assessment result")
    id_type: Optional[str] = Field(None, description="Type of Government ID (Aadhaar, PAN, etc.)")
    id_number: Optional[str] = Field(None, description="Extracted Government ID Number")
    name: Optional[str] = Field(None, description="Cardholder Name extracted from ID")
    dob: Optional[str] = Field(None, description="Date of Birth extracted from ID")
    gender: Optional[str] = Field(None, description="Gender extracted from ID")
    photo_base64: Optional[str] = Field(None, description="Base64 Data URL of the cardholder photo cropped from the ID")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Key-value pairs of extracted details")
    verification_checks: List[Dict[str, Any]] = Field(default_factory=list, description="List of verification factor results")
    authenticity_score: int = Field(default=0, ge=0, le=100, description="Computed authenticity confidence 0-100")
    pan_holder_type: Optional[str] = Field(None, description="PAN card holder type (Individual, Company, etc.)")
    aadhaar_verified: bool = Field(default=False, description="True if Aadhaar number passed Verhoeff checksum")
    pan_verified: bool = Field(default=False, description="True if PAN number structure is validated")


class ReportResponse(BaseModel):
    """Response envelope for POST /report endpoint."""
    file_name: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="Detected file extension")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score from 0 to 100")
    risk_level: str = Field(..., description="Categorical risk level (Low, Medium, High)")
    total_findings: int = Field(..., ge=0, description="Total count of PII findings")
    findings_by_type: Dict[str, int] = Field(default_factory=dict, description="Mapping of entity type to occurrence count")
    findings: List[Finding] = Field(default_factory=list, description="Complete list of findings with coordinates and reasoning")
    summary: RiskSummary = Field(..., description="Executive risk assessment summary")


class ErrorDetail(BaseModel):
    """Inner error payload."""
    code: str
    message: str
    status_code: int
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standardized error envelope."""
    error: ErrorDetail
