import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Screen1Upload } from '../components/screens/Screen1Upload';
import { Screen2Scanning } from '../components/screens/Screen2Scanning';
import { Screen4Preview } from '../components/screens/Screen4Preview';
import { Screen5Report } from '../components/screens/Screen5Report';
import { ScanResponse, ReportResponse } from '../types';

describe('Workflow & Interactive Edge Cases', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('Screen 1 loads quick test synthetic samples', () => {
    const onFileSelect = vi.fn();
    render(<Screen1Upload onFileSelect={onFileSelect} />);

    const sampleBtn = screen.getByText(/Employee Onboarding/i);
    expect(sampleBtn).toBeInTheDocument();
    fireEvent.click(sampleBtn);

    const filenames = screen.getAllByText(/employee_onboarding_audit\.txt/i);
    expect(filenames.length).toBeGreaterThan(0);

    const inspectBtn = screen.getByText(/Inspect Document/i);
    fireEvent.click(inspectBtn);

    // Permission modal appears: click Allow for now
    const allowBtn = screen.getByText(/Allow for now/i);
    fireEvent.click(allowBtn);
    expect(onFileSelect).toHaveBeenCalled();
  });

  it('Screen 2 shows error and retry button when scan fails', async () => {
    const file = new File(['bad content'], 'bad.txt', { type: 'text/plain' });
    const onScanComplete = vi.fn();
    const onBack = vi.fn();

    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: { message: 'Corrupted file header' } }),
    });

    render(<Screen2Scanning file={file} onScanComplete={onScanComplete} onBack={onBack} />);

    await waitFor(
      () => {
        expect(screen.getAllByText(/Corrupted file header/i).length).toBeGreaterThan(0);
      },
      { timeout: 4000 }
    );

    const returnBtn = screen.getByText(/Return to Upload/i);
    expect(returnBtn).toBeInTheDocument();
    fireEvent.click(returnBtn);
    expect(onBack).toHaveBeenCalled();
  });

  it('Screen 4 toggles between Split Slider and Side-by-Side views', async () => {
    const file = new File(['Col1,Col2\nVal1,Val2'], 'data.csv', { type: 'text/csv' });
    const blob = new Blob(['Col1,Col2\n[REDACTED],Val2'], { type: 'text/csv' });
    const mockScan: ScanResponse = {
      file_name: 'data.csv',
      file_type: 'csv',
      total_findings: 1,
      findings: [
        {
          id: 'find_1',
          entity_type: 'EMAIL',
          matched_text: 'user@example.com',
          confidence: 0.95,
          reasoning: 'Matches email pattern',
          location: { row: 1, col: 0 },
        },
      ],
    };

    render(
      <Screen4Preview
        originalFile={file}
        redactedBlob={blob}
        scanResult={mockScan}
        selectedCount={1}
        totalCount={1}
        onProceedToReport={vi.fn()}
        onBack={vi.fn()}
      />
    );

    const sideBySideBtn = screen.getByRole('button', { name: /Side-by-Side/i });
    fireEvent.click(sideBySideBtn);

    const originalLabel = await screen.findByText(/ORIGINAL DOCUMENT/i, {}, { timeout: 3000 });
    expect(originalLabel).toBeInTheDocument();
    expect(screen.getByText(/REDACTED OUTPUT/i)).toBeInTheDocument();
  });

  it('Screen 5 triggers redacted file download and PDF report download', async () => {
    const file = new File(['content'], 'sample.pdf', { type: 'application/pdf' });
    const blob = new Blob(['redacted bytes'], { type: 'application/pdf' });
    const onReset = vi.fn();

    const mockReport: ReportResponse = {
      file_name: 'sample.pdf',
      file_type: 'pdf',
      risk_score: 45,
      risk_level: 'Medium',
      total_findings: 1,
      findings_by_type: { PAN: 1 },
      findings: [],
      summary: {
        critical_count: 0,
        high_count: 1,
        medium_count: 0,
        low_count: 0,
        primary_threat: 'Taxpayer identity leak',
        compliance_verdict: 'Review before external sharing',
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['pdf bytes'], { type: 'application/pdf' }),
    });

    render(
      <Screen5Report
        originalFile={file}
        reportData={mockReport}
        redactedBlob={blob}
        onReset={onReset}
      />
    );

    // Test Download Redacted
    const downloadRedactedBtn = screen.getByText(/Download Redacted Document/i);
    fireEvent.click(downloadRedactedBtn);

    // Test Download PDF Report
    const downloadPdfBtn = screen.getByText(/Download Risk Report \(PDF\)/i);
    fireEvent.click(downloadPdfBtn);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/report?format=pdf', expect.anything());
    });

    // Test Scan Another
    const resetBtn = screen.getByText(/Scan Another Document/i);
    fireEvent.click(resetBtn);
    expect(onReset).toHaveBeenCalled();
  });
});
