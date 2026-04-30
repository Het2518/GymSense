// === FILE: src/components/DownloadButton.jsx ===
// GymSense AI — PDF report download button

import React, { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { getReport } from '../api';

export default function DownloadButton({ sessionId }) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    if (!sessionId) return;
    setDownloading(true);

    try {
      const blob = await getReport(sessionId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `GymSense_Report_${sessionId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Report downloaded!');
    } catch (err) {
      toast.error('Failed to download report: ' + err.message);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <button
      id="download-report-btn"
      onClick={handleDownload}
      disabled={downloading || !sessionId}
      className="btn-secondary flex items-center gap-2"
    >
      {downloading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-slate-500" />
          Downloading...
        </>
      ) : (
        <>
          <Download className="w-4 h-4 text-orange-600" />
          Download PDF Report
        </>
      )}
    </button>
  );
}
