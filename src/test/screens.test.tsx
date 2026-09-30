import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Screen1Upload } from '../components/screens/Screen1Upload';
import { Screen2Scanning } from '../components/screens/Screen2Scanning';
import { Screen3Findings } from '../components/screens/Screen3Findings';
import { Screen4Preview } from '../components/screens/Screen4Preview';
import { Screen5Report } from '../components/screens/Screen5Report';
import { App } from '../App';
import { ThemeProvider } from '../context/ThemeContext';
import { AuthProvider } from '../context/AuthContext';
import { ScanResponse, ReportResponse } from '../types';

describe('Screen 1: Upload Dropzone', () => {
  it('renders upload instructions and accepted formats', () => {
    const onFileSelect = vi.fn();
    render(<Screen1Upload onFileSelect={onFileSelect} />);

    expect(screen.getByText(/Scan Document for Personal Data Leaks/i)).toBeInTheDocument();
    expect(screen.getByText(/Drop target document here/i)).toBeInTheDocument();
    expect(screen.getByText(/\.PDF/i)).toBeInTheDocument();
    expect(screen.getByText(/\.DOCX/i)).toBeInTheDocument();
  });

  it('rejects unsupported file formats with user error alert', () => {
    const onFileSelect = vi.fn();
    render(<Screen1Upload onFileSelect={onFileSelect} />);

    const input = document.getElementById('file-upload-input') as HTMLInputElement;
    const invalidFile = new File(['content'], 'malicious.exe', { type: 'application/x-msdownload' });

    fireEvent.change(input, { target: { files: [invalidFile] } });

    expect(screen.getByText(/Unsupported format '\.exe'/i)).toBeInTheDocument();
    expect(onFileSelect).not.toHaveBeenCalled();
  });

  it('rejects empty (0 byte) file with clear warning', () => {
    const onFileSelect = vi.fn();
    render(<Screen1Upload onFileSelect={onFileSelect} />);

    const input = document.getElementById('file-upload-input') as HTMLInputElement;
    const emptyFile = new File([], 'empty.txt', { type: 'text/plain' });

    fireEvent.change(input, { target: { files: [emptyFile] } });

    expect(screen.getByText(/The selected file is empty/i)).toBeInTheDocument();
    expect(onFileSelect).not.toHaveBeenCalled();
  });

  it('accepts valid file and triggers inspect action', () => {
    const onFileSelect = vi.fn();
    render(<Screen1Upload onFileSelect={onFileSelect} />);

    const input = document.getElementById('file-upload-input') as HTMLInputElement;
    const validFile = new File(['Employee data: Rahul'], 'employee.txt', { type: 'text/plain' });

    fireEvent.change(input, { target: { files: [validFile] } });

    const filenames = screen.getAllByText('employee.txt');
    expect(filenames.length).toBeGreaterThan(0);
    expect(screen.getByText(/Inspect Document/i)).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Inspect Document/i));
    const allowBtn = screen.getByText(/Allow for now/i);
    fireEvent.click(allowBtn);
    expect(onFileSelect).toHaveBeenCalledWith(validFile);
  });

  it('displays sensitive data warning notification and handles permission cancel vs allow', () => {
    const onFileSelect = vi.fn();
    render(<Screen1Upload onFileSelect={onFileSelect} />);

    const sampleBtn = screen.getByText(/Employee Onboarding/i);
    fireEvent.click(sampleBtn);

    const inspectBtn = screen.getByText(/Inspect Document/i);
    fireEvent.click(inspectBtn);

    // Warning notification modal appears
    expect(screen.getByText(/SENSITIVE DATA WARNING/i)).toBeInTheDocument();
    expect(screen.getByText(/Your data is sensitive, be careful!/i)).toBeInTheDocument();
    expect(screen.getByText(/Allow for now/i)).toBeInTheDocument();

    // Cancel dismisses notification without calling onFileSelect
    const cancelBtn = screen.getByText(/Cancel/i);
    fireEvent.click(cancelBtn);
    expect(onFileSelect).not.toHaveBeenCalled();

    // Click inspect again and allow
    fireEvent.click(inspectBtn);
    const allowBtn = screen.getByText(/Allow for now/i);
    fireEvent.click(allowBtn);
    expect(onFileSelect).toHaveBeenCalled();
  });
});

describe('Screen 2: Scanning & Telemetry', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders radar scan beam and streaming terminal', async () => {
    const file = new File(['sample content'], 'doc.pdf', { type: 'application/pdf' });
    const onScanComplete = vi.fn();
    const onBack = vi.fn();

    const mockScanResponse: ScanResponse = {
      file_name: 'doc.pdf',
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
      json: async () => mockScanResponse,
    });

    render(<Screen2Scanning file={file} onScanComplete={onScanComplete} onBack={onBack} />);

    expect(screen.getByText(/Real-Time Analysis Telemetry/i)).toBeInTheDocument();
    expect(screen.getByText(/Structure Parsing/i)).toBeInTheDocument();
    expect(screen.getByText(/Presidio NER & Regex/i)).toBeInTheDocument();
    expect(screen.getByText(/Checksum Validation/i)).toBeInTheDocument();

    await waitFor(
      () => {
        expect(onScanComplete).toHaveBeenCalledWith(mockScanResponse);
      },
      { timeout: 3500 }
    );
  });
});

describe('Screen 3: Findings Review & Selective Toggles', () => {
  const mockScan: ScanResponse = {
    file_name: 'test_contract.txt',
    file_type: 'txt',
    total_findings: 3,
    findings: [
      {
        id: 'find_1',
        entity_type: 'AADHAAR',
        matched_text: '3675 9832 4511',
        confidence: 0.95,
        reasoning: 'Matches 12-digit Aadhaar pattern; passed Verhoeff checksum validation',
        location: { line: 4 },
      },
      {
        id: 'find_2',
        entity_type: 'PAN',
        matched_text: 'ABCDE1234F',
        confidence: 0.9,
        reasoning: 'Matches Indian Income Tax PAN pattern',
        location: { line: 5 },
      },
      {
        id: 'find_3',
        entity_type: 'PHONE',
        matched_text: '+91 9876543210',
        confidence: 0.85,
        reasoning: 'Matches Indian mobile phone number',
        location: { line: 6 },
      },
    ],
  };

  it('groups findings by entity type with severity badges', () => {
    const selected = new Set(['find_1', 'find_2', 'find_3']);
    const onToggle = vi.fn();
    const onSelectAll = vi.fn();
    const onDeselectAll = vi.fn();
    const onInvert = vi.fn();
    const onProceed = vi.fn();
    const onBack = vi.fn();

    render(
      <Screen3Findings
        scanResult={mockScan}
        selectedFindingIds={selected}
        onToggleFinding={onToggle}
        onSelectAll={onSelectAll}
        onDeselectAll={onDeselectAll}
        onInvertSelection={onInvert}
        onProceedToRedact={onProceed}
        onBack={onBack}
        isRedacting={false}
      />
    );

    expect(screen.getByText(/Personal Data Findings Review/i)).toBeInTheDocument();
    expect(screen.getByText('AADHAAR')).toBeInTheDocument();
    expect(screen.getByText('PAN')).toBeInTheDocument();
    expect(screen.getByText('PHONE')).toBeInTheDocument();
    expect(screen.getByText(/Selective Masking Enabled/i)).toBeInTheDocument();
  });

  it('triggers batch controls (Select All, Deselect All, Invert)', () => {
    const selected = new Set(['find_1']);
    const onToggle = vi.fn();
    const onSelectAll = vi.fn();
    const onDeselectAll = vi.fn();
    const onInvert = vi.fn();
    const onProceed = vi.fn();
    const onBack = vi.fn();

    render(
      <Screen3Findings
        scanResult={mockScan}
        selectedFindingIds={selected}
        onToggleFinding={onToggle}
        onSelectAll={onSelectAll}
        onDeselectAll={onDeselectAll}
        onInvertSelection={onInvert}
        onProceedToRedact={onProceed}
        onBack={onBack}
        isRedacting={false}
      />
    );

    fireEvent.click(screen.getByText('Select All'));
    expect(onSelectAll).toHaveBeenCalled();

    fireEvent.click(screen.getByText('Deselect All'));
    expect(onDeselectAll).toHaveBeenCalled();

    fireEvent.click(screen.getByText('Invert'));
    expect(onInvert).toHaveBeenCalled();
  });

  it('toggling group selection fires individual toggles or group action', () => {
    const selected = new Set(['find_1', 'find_2', 'find_3']);
    const onToggle = vi.fn();

    render(
      <Screen3Findings
        scanResult={mockScan}
        selectedFindingIds={selected}
        onToggleFinding={onToggle}
        onSelectAll={vi.fn()}
        onDeselectAll={vi.fn()}
        onInvertSelection={vi.fn()}
        onProceedToRedact={vi.fn()}
        onBack={vi.fn()}
        isRedacting={false}
      />
    );

    // Click group deselect button
    const groupBtns = screen.getAllByTitle(/Deselect entire group/i);
    expect(groupBtns.length).toBeGreaterThan(0);
    fireEvent.click(groupBtns[0]);
    expect(onToggle).toHaveBeenCalled();
  });
});

describe('Screen 4: Redaction Preview Split Slider', () => {
  const mockScan: ScanResponse = {
    file_name: 'doc.txt',
    file_type: 'txt',
    total_findings: 1,
    findings: [
      {
        id: 'find_1',
        entity_type: 'AADHAAR',
        matched_text: '3675 9832 4511',
        confidence: 0.95,
        reasoning: 'Matches 12-digit Aadhaar pattern; passed Verhoeff checksum validation',
        location: { line: 1 },
      },
    ],
  };

  it('renders interactive before/after split slider view', async () => {
    const file = new File(['Original text with Aadhaar: 3675 9832 4511'], 'doc.txt', {
      type: 'text/plain',
    });
    const redactedBlob = new Blob(['Original text with Aadhaar: [REDACTED]'], { type: 'text/plain' });

    render(
      <Screen4Preview
        originalFile={file}
        redactedBlob={redactedBlob}
        scanResult={mockScan}
        selectedCount={1}
        totalCount={1}
        onProceedToReport={vi.fn()}
        onBack={vi.fn()}
      />
    );

    expect(screen.getByText(/Interactive Redaction Split Comparison/i)).toBeInTheDocument();
    expect(screen.getByText(/BEFORE \(Original Document\)/i)).toBeInTheDocument();
    expect(screen.getByText(/AFTER \(Sanitized Redaction\)/i)).toBeInTheDocument();
    expect(screen.getByText(/<\|>/)).toBeInTheDocument(); // Slider handle
  });
});

describe('Screen 5: Report & Download', () => {
  const mockReport: ReportResponse = {
    file_name: 'candidate.pdf',
    file_type: 'pdf',
    risk_score: 84,
    risk_level: 'High',
    total_findings: 2,
    findings_by_type: { AADHAAR: 1, PAN: 1 },
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
    summary: {
      critical_count: 1,
      high_count: 1,
      medium_count: 0,
      low_count: 0,
      primary_threat: 'High identity theft danger',
      compliance_verdict: 'Mandatory automated redaction required before external transmission.',
    },
  };

  it('renders radial gauge, score, breakdown counts, and download actions', () => {
    const file = new File(['dummy'], 'candidate.pdf', { type: 'application/pdf' });
    const redactedBlob = new Blob(['redacted'], { type: 'application/pdf' });
    const onReset = vi.fn();

    render(
      <Screen5Report
        originalFile={file}
        reportData={mockReport}
        redactedBlob={redactedBlob}
        onReset={onReset}
      />
    );

    expect(screen.getByText(/Executive Compliance & Risk Audit/i)).toBeInTheDocument();
    expect(screen.getByText(/HIGH RISK LEVEL/i)).toBeInTheDocument();
    expect(screen.getByText(/out of 100/i)).toBeInTheDocument();
    expect(screen.getByText(/Mandatory automated redaction required/i)).toBeInTheDocument();
    expect(screen.getByText(/Download Redacted Document/i)).toBeInTheDocument();
    expect(screen.getByText(/Download Risk Report \(PDF\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Scan Another Document/i)).toBeInTheDocument();
  });
});

describe('App Integration', () => {
  it('renders login gate when unauthenticated', () => {
    sessionStorage.clear();
    render(
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
    );

    expect(screen.getByText(/SECURE AUTHENTICATION REQUIRED/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter username/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter password/i)).toBeInTheDocument();
    expect(screen.getByText(/Authenticate & Enter SOC/i)).toBeInTheDocument();
  });

  it('renders SentinelDoc SOC header and step tracker when authenticated', () => {
    sessionStorage.setItem('sentineldoc-user', JSON.stringify({ username: 'admin', displayName: 'Admin' }));
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'healthy', app: 'SentinelDoc', version: '1.0.0' }),
    });

    render(
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
    );

    const brandHeaders = screen.getAllByText(/Sentinel/i);
    expect(brandHeaders.length).toBeGreaterThan(0);
    expect(screen.getByText(/v1.0-SOC/i)).toBeInTheDocument();
    expect(screen.getByText(/Personal Data Leak Detector & Compliance Redactor/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Target Document/i).length).toBeGreaterThan(0);
  });

  it('rejects invalid credentials with error alert on login page', () => {
    sessionStorage.clear();
    render(
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
    );

    const userInput = screen.getByPlaceholderText(/Enter username/i);
    const passInput = screen.getByPlaceholderText(/Enter password/i);
    const submitBtn = screen.getByText(/Authenticate & Enter SOC/i);

    fireEvent.change(userInput, { target: { value: 'wronguser' } });
    fireEvent.change(passInput, { target: { value: 'wrongpass' } });
    fireEvent.click(submitBtn);

    expect(screen.getByText(/ACCESS DENIED/i)).toBeInTheDocument();
  });

  it('successfully logs in with valid demo credentials', () => {
    sessionStorage.clear();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'healthy', app: 'SentinelDoc', version: '1.0.0' }),
    });

    render(
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
    );

    const userInput = screen.getByPlaceholderText(/Enter username/i);
    const passInput = screen.getByPlaceholderText(/Enter password/i);
    const submitBtn = screen.getByText(/Authenticate & Enter SOC/i);

    fireEvent.change(userInput, { target: { value: 'admin' } });
    fireEvent.change(passInput, { target: { value: 'sentinel2026' } });
    fireEvent.click(submitBtn);

    expect(screen.getByText(/v1.0-SOC/i)).toBeInTheDocument();
    expect(screen.getByText(/Admin/i)).toBeInTheDocument();
  });

  it('saves credentials to localStorage and enables 1-Click Login', () => {
    sessionStorage.clear();
    localStorage.clear();

    render(
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
    );

    const userInput = screen.getByPlaceholderText(/Enter username/i);
    const passInput = screen.getByPlaceholderText(/Enter password/i);
    const saveBtn = screen.getByText(/Save My Credentials/i);

    fireEvent.change(userInput, { target: { value: 'admin' } });
    fireEvent.change(passInput, { target: { value: 'sentinel2026' } });
    fireEvent.click(saveBtn);

    expect(screen.getByText(/Saved!/i)).toBeInTheDocument();
    expect(localStorage.getItem('sentineldoc-saved-credentials')).toContain('admin');

    // 1-Click Login button is now visible
    const quickLoginBtn = screen.getByText(/1-Click Login/i);
    expect(quickLoginBtn).toBeInTheDocument();

    fireEvent.click(quickLoginBtn);
    expect(screen.getByText(/v1.0-SOC/i)).toBeInTheDocument();
  });
});
