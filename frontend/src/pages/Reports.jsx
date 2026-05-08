import React, { useState } from 'react';
import { CalendarRange, Download, FileSpreadsheet, FileText } from 'lucide-react';
import toast from 'react-hot-toast';

import { reportsApi } from '../api/endpoints.js';
import PageMotion from '../components/PageMotion.jsx';
import { Button } from '../components/ui/button.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card.jsx';
import { Input } from '../components/ui/input.jsx';

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

export default function Reports() {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [downloading, setDownloading] = useState(null);

  function quickRange(days) {
    const to = new Date();
    const from = new Date();
    from.setDate(to.getDate() - days);
    setDateFrom(from.toISOString().slice(0, 10));
    setDateTo(to.toISOString().slice(0, 10));
  }

  async function download(kind) {
    setDownloading(kind);
    try {
      const params = {};
      if (dateFrom) params.date_from = `${dateFrom}T00:00:00`;
      if (dateTo) params.date_to = `${dateTo}T23:59:59`;

      const { blob, filename } = await reportsApi.download(kind, params);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      toast.success(`${kind.toUpperCase()} exported successfully`);
    } catch (error) {
      toast.error(error?.response?.data?.detail || error?.message || 'Failed to download report');
    } finally {
      setDownloading(null);
    }
  }

  return (
    <PageMotion>
      <div className="space-y-6">
        <div>
          <h2 className="page-title">Reports Center</h2>
          <p className="page-subtitle">Generate executive-ready print usage reports in one click</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><CalendarRange className="h-4 w-4" /> Date range</CardTitle>
            <CardDescription>Select a period to export filtered print activity reports</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <Input type="date" value={dateFrom} max={todayISO()} onChange={(e) => setDateFrom(e.target.value)} />
              <Input type="date" value={dateTo} max={todayISO()} onChange={(e) => setDateTo(e.target.value)} />
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" onClick={() => quickRange(7)}>Last 7d</Button>
                <Button variant="secondary" size="sm" onClick={() => quickRange(30)}>Last 30d</Button>
                <Button variant="secondary" size="sm" onClick={() => quickRange(90)}>Last 90d</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><FileSpreadsheet className="h-4 w-4" /> Excel Export</CardTitle>
              <CardDescription>Detailed tabular logs for finance, audit, and operations teams</CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="gap-2" onClick={() => download('excel')} disabled={!!downloading}>
                <Download className="h-4 w-4" />
                {downloading === 'excel' ? 'Exporting...' : 'Download .xlsx'}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><FileText className="h-4 w-4" /> PDF Export</CardTitle>
              <CardDescription>Executive-friendly printable reports for leadership review</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="secondary" className="gap-2" onClick={() => download('pdf')} disabled={!!downloading}>
                <Download className="h-4 w-4" />
                {downloading === 'pdf' ? 'Exporting...' : 'Download PDF'}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageMotion>
  );
}
