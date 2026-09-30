"""Configuration settings and constants for SentinelDoc."""
from typing import Dict, Set

# Application Metadata
APP_TITLE = "SentinelDoc"
APP_DESCRIPTION = "Personal Data Leak Detector & Redaction Backend"
APP_VERSION = "1.0.0"

# Supported file extensions and corresponding MIME types
SUPPORTED_EXTENSIONS: Set[str] = {
    ".pdf",
    ".docx",
    ".csv",
    ".xlsx",
    ".txt",
    ".log",
}

MIME_TYPE_MAPPING: Dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
    "log": "text/plain",
}

# NLP Engine Configuration for Microsoft Presidio
NLP_CONFIGURATION = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}

# Non-PII common false positive words to suppress for NER PERSON/LOCATION
NER_DENY_LIST = {
    "aadhaar", "uidai", "pan", "card", "credit card", "debit card", "visa",
    "mastercard", "order id", "zip code", "pincode", "pin code", "account",
    "invoice", "receipt", "phone", "mobile", "email", "address", "date",
    "valid", "invalid", "sample", "test", "total", "amount", "status",
    "sentineldoc", "document", "id", "ref", "reference", "number", "tax",
    "income tax", "permanent account number", "customer", "vendor",
}
