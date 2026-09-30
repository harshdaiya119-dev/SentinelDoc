import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  checkHealth,
  scanDocument,
  redactDocument,
  getRiskReport,
  downloadRiskReportPdf,
} from '../services/api';

describe('Frontend API Client (src/services/api.ts)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('checkHealth returns true when status is healthy', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'healthy', app: 'SentinelDoc', version: '1.0.0' }),
    });

    const result = await checkHealth();
    expect(result).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith('/health');
  });

  it('checkHealth returns false when network fails', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Connection refused'));

    const result = await checkHealth();
    expect(result).toBe(false);
  });

  it('scanDocument sends file in FormData and returns ScanResponse', async () => {
    const mockResponse = {
      file_name: 'test.pdf',
      file_type: 'pdf',
      total_findings: 1,
      findings: [
        {
          id: 'find_1',
          entity_type: 'AADHAAR',
          matched_text: '3675 9832 4511',
          confidence: 0.95,
          reasoning: 'Verhoeff valid',
          location: { page: 1 },
        },
      ],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const file = new File(['dummy content'], 'test.pdf', { type: 'application/pdf' });
    const res = await scanDocument(file);

    expect(res.total_findings).toBe(1);
    expect(res.findings[0].entity_type).toBe('AADHAAR');
    expect(global.fetch).toHaveBeenCalledWith('/scan', expect.objectContaining({
      method: 'POST',
    }));
  });

  it('scanDocument throws readable error message on API error', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        error: { message: 'Uploaded file is empty (0 bytes).' },
      }),
    });

    const file = new File([], 'empty.txt', { type: 'text/plain' });
    await expect(scanDocument(file)).rejects.toThrow('Uploaded file is empty (0 bytes).');
  });

  it('redactDocument sends selected finding IDs JSON array', async () => {
    const mockBlob = new Blob(['redacted content'], { type: 'application/pdf' });
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => mockBlob,
    });

    const file = new File(['content'], 'doc.pdf', { type: 'application/pdf' });
    const result = await redactDocument(file, ['find_1', 'find_2']);

    expect(result).toBeInstanceOf(Blob);
    expect(global.fetch).toHaveBeenCalledWith('/redact', expect.objectContaining({
      method: 'POST',
    }));
  });

  it('getRiskReport calls /report?format=json and returns ReportResponse', async () => {
    const mockReport = {
      file_name: 'audit.pdf',
      file_type: 'pdf',
      risk_score: 84,
      risk_level: 'High',
      total_findings: 2,
      findings_by_type: { AADHAAR: 1, PAN: 1 },
      findings: [],
      summary: {
        critical_count: 1,
        high_count: 1,
        medium_count: 0,
        low_count: 0,
        primary_threat: 'High identity risk',
        compliance_verdict: 'Mandatory redaction required',
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockReport,
    });

    const file = new File(['data'], 'audit.pdf', { type: 'application/pdf' });
    const res = await getRiskReport(file);

    expect(res.risk_score).toBe(84);
    expect(res.risk_level).toBe('High');
    expect(global.fetch).toHaveBeenCalledWith('/report?format=json', expect.objectContaining({
      method: 'POST',
      headers: { Accept: 'application/json' },
    }));
  });

  it('downloadRiskReportPdf calls /report?format=pdf and returns Blob', async () => {
    const mockPdfBlob = new Blob(['%PDF-1.4 mock'], { type: 'application/pdf' });
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => mockPdfBlob,
    });

    const file = new File(['data'], 'report.pdf', { type: 'application/pdf' });
    const blob = await downloadRiskReportPdf(file);

    expect(blob).toBeInstanceOf(Blob);
    expect(global.fetch).toHaveBeenCalledWith('/report?format=pdf', expect.objectContaining({
      method: 'POST',
      headers: { Accept: 'application/pdf' },
    }));
  });
});
