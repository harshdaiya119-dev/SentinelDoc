import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Columns,
  Split,
  ArrowRight,
  ArrowLeft,
  FileCheck2,
  ZoomIn,
  ZoomOut,
  RefreshCw,
} from 'lucide-react';
import mammoth from 'mammoth';
import * as pdfjsLib from 'pdfjs-dist';

// Configure pdfjs worker if in browser (local bundle for offline demo)
if (typeof window !== 'undefined' && pdfjsLib.GlobalWorkerOptions) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
}

import { ScanResponse } from '../../types';

interface Screen4PreviewProps {
  originalFile: File;
  redactedBlob: Blob | null;
  scanResult: ScanResponse | null;
  selectedCount: number;
  totalCount: number;
  onProceedToReport: () => void;
  onBack: () => void;
}

export const Screen4Preview: React.FC<Screen4PreviewProps> = ({
  originalFile,
  redactedBlob,
  scanResult: _scanResult,
  selectedCount,
  totalCount,
  onProceedToReport,
  onBack,
}) => {
  const [sliderPosition, setSliderPosition] = useState<number>(50); // percentage 0 to 100
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'split' | 'side-by-side'>('split');
  const [zoom, setZoom] = useState<number>(100);

  // Content representations
  const [originalText, setOriginalText] = useState<string>('');
  const [redactedText, setRedactedText] = useState<string>('');
  const [originalHtml, setOriginalHtml] = useState<string>('');
  const [redactedHtml, setRedactedHtml] = useState<string>('');
  const [loadingPreview, setLoadingPreview] = useState<boolean>(true);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // PDF Page management
  const [pdfPage, setPdfPage] = useState<number>(1);
  const [pdfTotalPages, setPdfTotalPages] = useState<number>(1);
  const originalCanvasRef = useRef<HTMLCanvasElement>(null);
  const redactedCanvasRef = useRef<HTMLCanvasElement>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  const ext = originalFile.name.split('.').pop()?.toLowerCase() || '';

  // Load preview data
  useEffect(() => {
    let active = true;

    const loadData = async () => {
      setLoadingPreview(true);
      setPreviewError(null);

      const readText = (b: Blob): Promise<string> => {
        if (typeof b.text === 'function') return b.text();
        return new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result as string);
          reader.onerror = reject;
          reader.readAsText(b);
        });
      };

      const readBuffer = (b: Blob): Promise<ArrayBuffer> => {
        if (typeof b.arrayBuffer === 'function') return b.arrayBuffer();
        return new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result as ArrayBuffer);
          reader.onerror = reject;
          reader.readAsArrayBuffer(b);
        });
      };

      try {
        if (ext === 'txt' || ext === 'csv' || ext === 'xlsx') {
          // Read as text
          const origStr = await readText(originalFile);
          let redStr = origStr;
          if (redactedBlob) {
            redStr = await readText(redactedBlob);
          }
          if (active) {
            setOriginalText(origStr);
            setRedactedText(redStr);
          }
        } else if (ext === 'docx') {
          // Mammoth docx to html
          const origBuf = await readBuffer(originalFile);
          const origRes = await mammoth.convertToHtml({ arrayBuffer: origBuf });
          let redHtml = origRes.value;

          if (redactedBlob) {
            try {
              const redBuf = await readBuffer(redactedBlob);
              const redRes = await mammoth.convertToHtml({ arrayBuffer: redBuf });
              redHtml = redRes.value;
            } catch {
              redHtml = origRes.value.replace(/\[REDACTED\]/g, '<span class="bg-black text-white px-1 font-mono">[REDACTED]</span>');
            }
          }

          if (active) {
            setOriginalHtml(origRes.value);
            setRedactedHtml(redHtml);
          }
        } else if (ext === 'pdf') {
          // PDF preview via pdfjs-dist
          try {
            const origBuf = await readBuffer(originalFile);
            const origPdf = await pdfjsLib.getDocument({ data: origBuf }).promise;
            if (active) {
              setPdfTotalPages(origPdf.numPages);
            }

            const page = await origPdf.getPage(pdfPage);
            const viewport = page.getViewport({ scale: zoom / 100 * 1.3 });

            if (originalCanvasRef.current) {
              const canvas = originalCanvasRef.current;
              const ctx = canvas.getContext('2d');
              if (ctx) {
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                await page.render({ canvasContext: ctx, viewport }).promise;
              }
            }

            if (redactedBlob && redactedCanvasRef.current) {
              const redBuf = await redactedBlob.arrayBuffer();
              const redPdf = await pdfjsLib.getDocument({ data: redBuf }).promise;
              const redPage = await redPdf.getPage(pdfPage);
              const redCanvas = redactedCanvasRef.current;
              const redCtx = redCanvas.getContext('2d');
              if (redCtx) {
                redCanvas.width = viewport.width;
                redCanvas.height = viewport.height;
                await redPage.render({ canvasContext: redCtx, viewport }).promise;
              }
            }
          } catch {
            // PDF canvas render failed; preview falls back safely
          }
        }
      } catch (err: unknown) {
        if (active) {
          const msg = err instanceof Error ? err.message : 'Error rendering preview';
          setPreviewError(msg);
        }
      } finally {
        if (active) {
          setLoadingPreview(false);
        }
      }
    };

    loadData();

    return () => {
      active = false;
    };
  }, [originalFile, redactedBlob, ext, pdfPage, zoom]);

  // Split slider drag handling
  const handlePointerDown = () => {
    setIsDragging(true);
  };

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement> | PointerEvent) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = (e as MouseEvent).clientX - rect.left;
      const pos = Math.max(5, Math.min(95, (x / rect.width) * 100));
      setSliderPosition(pos);
    },
    [isDragging]
  );

  const handlePointerUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('pointermove', handlePointerMove);
      window.addEventListener('pointerup', handlePointerUp);
    }
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [isDragging, handlePointerMove, handlePointerUp]);

  // Render Table content for CSV / XLSX
  const renderTable = (content: string) => {
    const lines = content.trim().split('\n').filter(Boolean);
    if (lines.length === 0) return <div className="p-4 text-text-muted">Empty file</div>;

    const headers = lines[0].split(',').map((h) => h.trim().replace(/^["']|["']$/g, ''));
    const rows = lines.slice(1).map((line) =>
      line.split(',').map((c) => c.trim().replace(/^["']|["']$/g, ''))
    );

    return (
      <div className="overflow-x-auto p-4 select-text">
        <table className="w-full text-left border-collapse text-xs font-mono">
          <thead>
            <tr className="border-b border-border bg-surface/80">
              {headers.map((h, i) => (
                <th key={i} className="p-2 text-text-muted font-semibold uppercase text-[10px]">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {rows.map((row, ri) => (
              <tr key={ri} className="hover:bg-surface/50">
                {row.map((cell, ci) => {
                  const isCellRedacted =
                    cell === '[REDACTED]' || cell.includes('REDACTED') || cell.includes('****');
                  return (
                    <td key={ci} className="p-2 text-text-primary">
                      {isCellRedacted ? (
                        <span className="group relative inline-block px-1.5 py-0.5 rounded bg-black border border-crimson-brand/40 text-crimson-brand font-mono font-bold text-[11px] cursor-help">
                          [REDACTED]
                          <span className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 w-max px-2 py-1 bg-surface border border-border text-text-primary text-[10px] rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-lg">
                            Sensitive PII masked
                          </span>
                        </span>
                      ) : (
                        cell
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // Render Plain Text
  const renderPlainText = (content: string, isRedacted: boolean) => {
    const lines = content.split('\n');
    return (
      <pre className="p-4 font-mono text-xs text-text-primary leading-relaxed whitespace-pre-wrap select-text">
        {lines.map((line, idx) => {
          const hasRedacted = line.includes('[REDACTED]');
          return (
            <div
              key={idx}
              className={`flex items-start ${
                hasRedacted && isRedacted ? 'bg-crimson-brand/10 border-l-2 border-crimson-brand pl-1' : ''
              }`}
            >
              <span className="text-text-muted w-8 select-none text-[10px] pr-2 text-right">
                {idx + 1}
              </span>
              <span className="flex-1">
                {hasRedacted && isRedacted ? (
                  line.split(/(\[REDACTED\])/).map((part, pIdx) =>
                    part === '[REDACTED]' ? (
                      <span
                        key={pIdx}
                        className="group relative inline-block bg-black text-crimson-brand font-bold px-1 rounded border border-crimson-brand/40 cursor-help"
                      >
                        [REDACTED]
                        <span className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 w-max px-2 py-1 bg-surface border border-border text-text-primary text-[10px] rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-lg font-sans font-normal">
                          Sensitive Data Sanitized
                        </span>
                      </span>
                    ) : (
                      part
                    )
                  )
                ) : (
                  line
                )}
              </span>
            </div>
          );
        })}
      </pre>
    );
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4 sm:px-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-semibold tracking-tight text-text-primary">
              Interactive Redaction Split Comparison
            </h2>
            <span className="px-2 py-0.5 rounded bg-teal-brand/10 border border-teal-brand/30 text-teal-brand text-xs font-mono font-semibold">
              LIVE PREVIEW
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Drag the vertical slider or toggle side-by-side to inspect sanitized data against the
            original layout.
          </p>
        </div>

        {/* View Mode & Zoom Controls */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center rounded-md bg-surface border border-border p-0.5 text-xs font-mono">
            <button
              type="button"
              onClick={() => setViewMode('split')}
              className={`px-2.5 py-1 rounded flex items-center space-x-1.5 transition-colors ${
                viewMode === 'split'
                  ? 'bg-canvas text-teal-brand font-medium shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <Split className="w-3.5 h-3.5" />
              <span>Split Slider</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('side-by-side')}
              className={`px-2.5 py-1 rounded flex items-center space-x-1.5 transition-colors ${
                viewMode === 'side-by-side'
                  ? 'bg-canvas text-teal-brand font-medium shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Side-by-Side</span>
            </button>
          </div>

          <div className="hidden sm:flex items-center space-x-1 bg-surface border border-border rounded-md px-2 py-1 text-xs font-mono">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(75, z - 15))}
              className="text-text-muted hover:text-text-primary"
              title="Zoom out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="px-1 text-text-primary font-mono-data">{zoom}%</span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(150, z + 15))}
              className="text-text-muted hover:text-text-primary"
              title="Zoom in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Redaction Meta Status Pill */}
      <div className="my-3 px-3.5 py-2 rounded-md bg-surface border border-border flex items-center justify-between text-xs font-mono">
        <div className="flex items-center space-x-2">
          <FileCheck2 className="w-4 h-4 text-teal-brand" />
          <span className="text-text-secondary">
            Selective Filter:{' '}
            <strong className="text-text-primary font-bold">
              {selectedCount} of {totalCount} findings
            </strong>{' '}
            redacted in output binary.
          </span>
        </div>
        <div className="text-text-muted hidden sm:block">
          Format: <span className="uppercase text-teal-brand">.{ext}</span> • Engine: In-Memory Vector Overlay
        </div>
      </div>

      {/* Main Preview Viewport */}
      {viewMode === 'split' ? (
        /* Split Comparison Slider Container */
        <div
          ref={containerRef}
          onPointerDown={handlePointerDown}
          className="relative w-full h-[520px] rounded-md bg-canvas border border-border overflow-hidden select-none cursor-ew-resize"
        >
          {/* Label Badges */}
          <div className="absolute top-3 left-3 z-30 pointer-events-none">
            <span className="px-2 py-1 rounded bg-surface/90 border border-border text-[11px] font-mono text-text-secondary font-medium backdrop-blur-none">
              BEFORE (Original Document)
            </span>
          </div>
          <div className="absolute top-3 right-3 z-30 pointer-events-none">
            <span className="px-2 py-1 rounded bg-teal-brand/10 border border-teal-brand/40 text-[11px] font-mono text-teal-brand font-medium backdrop-blur-none">
              AFTER (Sanitized Redaction)
            </span>
          </div>

          {/* Layer 1: Bottom Original Unredacted View */}
          <div className="absolute inset-0 w-full h-full overflow-auto bg-[#0B0F14]">
            {loadingPreview ? (
              <div className="flex items-center justify-center h-full space-x-2 text-text-muted font-mono text-xs">
                <RefreshCw className="w-4 h-4 text-teal-brand animate-spin" />
                <span>Rendering preview...</span>
              </div>
            ) : previewError ? (
              <div className="p-6 text-crimson-brand font-mono text-xs">{previewError}</div>
            ) : ext === 'pdf' ? (
              <div className="flex justify-center p-4">
                <canvas ref={originalCanvasRef} className="shadow-md max-w-full" />
              </div>
            ) : ext === 'docx' ? (
              <div
                className="p-6 text-xs text-text-primary leading-relaxed select-text"
                dangerouslySetInnerHTML={{ __html: originalHtml || '<p>Loading DOCX...</p>' }}
              />
            ) : ext === 'csv' || ext === 'xlsx' ? (
              renderTable(originalText)
            ) : (
              renderPlainText(originalText, false)
            )}
          </div>

          {/* Layer 2: Top Redacted View clipped to sliderPosition */}
          <div
            className="absolute inset-0 w-full h-full overflow-auto bg-[#0B0F14]"
            style={{
              clipPath: `polygon(${sliderPosition}% 0, 100% 0, 100% 100%, ${sliderPosition}% 100%)`,
            }}
          >
            {loadingPreview ? null : previewError ? null : ext === 'pdf' ? (
              <div className="flex justify-center p-4">
                <canvas ref={redactedCanvasRef} className="shadow-md max-w-full" />
              </div>
            ) : ext === 'docx' ? (
              <div
                className="p-6 text-xs text-text-primary leading-relaxed select-text"
                dangerouslySetInnerHTML={{ __html: redactedHtml || '<p>Loading Redacted DOCX...</p>' }}
              />
            ) : ext === 'csv' || ext === 'xlsx' ? (
              renderTable(redactedText)
            ) : (
              renderPlainText(redactedText, true)
            )}
          </div>

          {/* Draggable Vertical Slider Line */}
          <div
            className="absolute top-0 bottom-0 w-[2px] bg-teal-brand shadow-[0_0_8px_#2DD4BF] z-40"
            style={{ left: `${sliderPosition}%` }}
          >
            {/* Grip Handle */}
            <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-7 h-10 rounded bg-surface border border-teal-brand flex items-center justify-center text-teal-brand shadow-lg cursor-grab active:cursor-grabbing">
              <span className="font-mono text-[10px] font-bold select-none tracking-tighter">
                &lt;|&gt;
              </span>
            </div>
          </div>
        </div>
      ) : (
        /* Side-by-Side Dual View */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-[520px]">
          {/* Left: Original */}
          <div className="rounded-md bg-canvas border border-border flex flex-col overflow-hidden">
            <div className="p-2.5 bg-surface border-b border-border flex items-center justify-between text-xs font-mono">
              <span className="text-text-secondary font-medium">ORIGINAL DOCUMENT</span>
              <span className="text-[10px] text-text-muted">Unredacted Source</span>
            </div>
            <div className="flex-1 overflow-auto bg-[#0B0F14]">
              {ext === 'pdf' ? (
                <div className="flex justify-center p-4">
                  <canvas ref={originalCanvasRef} className="shadow-md max-w-full" />
                </div>
              ) : ext === 'docx' ? (
                <div
                  className="p-4 text-xs text-text-primary leading-relaxed select-text"
                  dangerouslySetInnerHTML={{ __html: originalHtml || '<p>Loading DOCX...</p>' }}
                />
              ) : ext === 'csv' || ext === 'xlsx' ? (
                renderTable(originalText)
              ) : (
                renderPlainText(originalText, false)
              )}
            </div>
          </div>

          {/* Right: Redacted */}
          <div className="rounded-md bg-canvas border border-teal-brand/40 flex flex-col overflow-hidden">
            <div className="p-2.5 bg-surface border-b border-teal-brand/40 flex items-center justify-between text-xs font-mono">
              <span className="text-teal-brand font-medium">REDACTED OUTPUT</span>
              <span className="text-[10px] text-teal-brand font-mono-data">
                {selectedCount} masked
              </span>
            </div>
            <div className="flex-1 overflow-auto bg-[#0B0F14]">
              {ext === 'pdf' ? (
                <div className="flex justify-center p-4">
                  <canvas ref={redactedCanvasRef} className="shadow-md max-w-full" />
                </div>
              ) : ext === 'docx' ? (
                <div
                  className="p-4 text-xs text-text-primary leading-relaxed select-text"
                  dangerouslySetInnerHTML={{
                    __html: redactedHtml || '<p>Loading Redacted DOCX...</p>',
                  }}
                />
              ) : ext === 'csv' || ext === 'xlsx' ? (
                renderTable(redactedText)
              ) : (
                renderPlainText(redactedText, true)
              )}
            </div>
          </div>
        </div>
      )}

      {/* Multipage PDF Pagination Controls */}
      {ext === 'pdf' && pdfTotalPages > 1 && (
        <div className="mt-3 flex items-center justify-center space-x-2 text-xs font-mono">
          <button
            type="button"
            disabled={pdfPage <= 1}
            onClick={() => setPdfPage((p) => Math.max(1, p - 1))}
            className="px-2.5 py-1 rounded bg-surface border border-border disabled:opacity-40"
          >
            Prev Page
          </button>
          <span className="text-text-secondary font-mono-data">
            Page {pdfPage} of {pdfTotalPages}
          </span>
          <button
            type="button"
            disabled={pdfPage >= pdfTotalPages}
            onClick={() => setPdfPage((p) => Math.min(pdfTotalPages, p + 1))}
            className="px-2.5 py-1 rounded bg-surface border border-border disabled:opacity-40"
          >
            Next Page
          </button>
        </div>
      )}

      {/* Navigation Footer */}
      <div className="mt-6 pt-4 border-t border-border flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-2 rounded-md bg-surface border border-border hover:border-border-focus text-xs font-mono text-text-secondary hover:text-text-primary transition-colors flex items-center space-x-1.5"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Findings</span>
        </button>

        <button
          type="button"
          onClick={onProceedToReport}
          className="px-5 py-2.5 rounded-md bg-teal-brand text-canvas hover:bg-teal-brand/90 font-medium text-xs tracking-wide transition-all flex items-center space-x-2 shadow-sm cursor-pointer"
        >
          <span>Generate Risk Report & Downloads</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
