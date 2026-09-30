export type EntityType =
  | 'AADHAAR'
  | 'PAN'
  | 'CREDIT_CARD'
  | 'PHONE'
  | 'EMAIL'
  | 'PERSON'
  | 'ADDRESS'
  | 'DATE_OF_BIRTH'
  | string;

export interface BoundingBox {
  x0: number;
  top: number;
  x1: number;
  bottom: number;
}

export interface FindingLocation {
  page?: number | null;
  bbox?: BoundingBox | null;
  paragraph_index?: number | null;
  sheet_name?: string | null;
  cell?: string | null;
  row?: number | null;
  col?: number | null;
  line?: number | null;
  start_char?: number | null;
  end_char?: number | null;
}

export interface Finding {
  id: string;
  entity_type: EntityType;
  matched_text: string;
  confidence: number;
  reasoning: string;
  location: FindingLocation;
}

export interface ScanResponse {
  file_name: string;
  file_type: string;
  total_findings: number;
  findings: Finding[];
}

export interface RiskSummary {
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  primary_threat: string;
  compliance_verdict: string;
}

export interface ReportResponse {
  file_name: string;
  file_type: string;
  risk_score: number;
  risk_level: 'Low' | 'Medium' | 'High';
  total_findings: number;
  findings_by_type: Record<string, number>;
  findings: Finding[];
  summary: RiskSummary;
}

export type WorkflowStep =
  | 'UPLOAD'
  | 'SCANNING'
  | 'FINDINGS'
  | 'PREVIEW'
  | 'REPORT';

export type SeverityTier = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export function getEntitySeverity(type: string): SeverityTier {
  const t = type.toUpperCase();
  if (t === 'AADHAAR' || t === 'CREDIT_CARD') return 'CRITICAL';
  if (t === 'PAN' || t === 'DATE_OF_BIRTH') return 'HIGH';
  if (t === 'PHONE' || t === 'ADDRESS') return 'MEDIUM';
  return 'LOW'; // EMAIL, PERSON, others
}
