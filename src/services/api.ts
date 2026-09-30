import { ScanResponse, ReportResponse } from '../types';

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch('/health');
    if (!res.ok) return false;
    const data = await res.json();
    return data.status === 'healthy';
  } catch {
    return false;
  }
}

export async function scanDocument(file: File): Promise<ScanResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/scan', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errorMessage = `Scan failed (${res.status})`;
    try {
      const errorJson = await res.json();
      if (errorJson.error?.message) {
        errorMessage = errorJson.error.message;
      } else if (errorJson.detail) {
        errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorMessage);
  }

  return res.json();
}

export async function redactDocument(file: File, findingIds?: string[] | 'all'): Promise<Blob> {
  const formData = new FormData();
  formData.append('file', file);

  if (findingIds && findingIds !== 'all') {
    formData.append('finding_ids', JSON.stringify(findingIds));
  } else {
    formData.append('finding_ids', 'all');
  }

  const res = await fetch('/redact', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errorMessage = `Redaction failed (${res.status})`;
    try {
      const errorJson = await res.json();
      if (errorJson.error?.message) {
        errorMessage = errorJson.error.message;
      } else if (errorJson.detail) {
        errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorMessage);
  }

  return res.blob();
}

export async function getRiskReport(file: File): Promise<ReportResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/report?format=json', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
    },
    body: formData,
  });

  if (!res.ok) {
    let errorMessage = `Report generation failed (${res.status})`;
    try {
      const errorJson = await res.json();
      if (errorJson.error?.message) {
        errorMessage = errorJson.error.message;
      } else if (errorJson.detail) {
        errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorMessage);
  }

  return res.json();
}

export async function downloadRiskReportPdf(file: File): Promise<Blob> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/report?format=pdf', {
    method: 'POST',
    headers: {
      Accept: 'application/pdf',
    },
    body: formData,
  });

  if (!res.ok) {
    let errorMessage = `PDF report download failed (${res.status})`;
    try {
      const errorJson = await res.json();
      if (errorJson.error?.message) {
        errorMessage = errorJson.error.message;
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorMessage);
  }

  return res.blob();
}
