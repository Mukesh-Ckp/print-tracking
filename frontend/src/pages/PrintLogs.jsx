import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Download, Filter, Pencil, RefreshCw, Search, UserCog } from 'lucide-react';
import toast from 'react-hot-toast';

import PageMotion from '../components/PageMotion.jsx';
import StatusBadge from '../components/StatusBadge.jsx';
import { reportsApi, printsApi, usersApi } from '../api/endpoints.js';
import { Button } from '../components/ui/button.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card.jsx';
import { Input } from '../components/ui/input.jsx';
import { Select } from '../components/ui/select.jsx';
import { Skeleton } from '../components/ui/skeleton.jsx';
import { Table, TBody, TD, TH, THead, TR } from '../components/ui/table.jsx';
import { formatDateTime, formatNumber } from '../utils/format.js';

const REFRESH_MS = 20000;
const PAGE_SIZES = [10, 25, 50, 100];

export default function PrintLogs() {
  const [filters, setFilters] = useState({
    search: '',
    username: '',
    printer_name: '',
    status: '',
    date_from: '',
    date_to: '',
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [data, setData] = useState({ items: [], total: 0, total_pages: 1, page: 1 });
  const [userSummary, setUserSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [exporting, setExporting] = useState(null);

  const [editOpen, setEditOpen] = useState(false);
  const [editingUsername, setEditingUsername] = useState('');
  const [editingDisplayName, setEditingDisplayName] = useState('');
  const [editingLimit, setEditingLimit] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  const params = useMemo(() => {
    const q = { page, page_size: pageSize };
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) q[key] = value;
    });
    if (q.date_from) q.date_from = `${q.date_from}T00:00:00`;
    if (q.date_to) q.date_to = `${q.date_to}T23:59:59`;
    return q;
  }, [filters, page, pageSize]);

  const loadUsers = useCallback(async () => {
    try {
      const users = await usersApi.summary();
      setUserSummary(users || []);
    } catch (_e) {
      // keep log table usable even if summary fails
    }
  }, []);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const response = await printsApi.list(params);
      setData(response);
    } catch (error) {
      toast.error(error?.response?.data?.detail || error?.message || 'Failed to fetch print logs');
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const interval = setInterval(() => {
      load();
      loadUsers();
    }, REFRESH_MS);
    return () => clearInterval(interval);
  }, [autoRefresh, load, loadUsers]);

  function updateFilter(key, value) {
    setPage(1);
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function openEdit(row) {
    const raw = row.username || '';
    const summary = userSummary.find((u) => u.username === raw);
    setEditingUsername(raw);
    setEditingDisplayName(summary?.display_name || row.display_username || raw);
    setEditingLimit(summary?.print_limit ? String(summary.print_limit) : '');
    setEditOpen(true);
  }

  async function saveUserProfile() {
    if (!editingUsername) return;
    setSavingProfile(true);
    try {
      await usersApi.update(editingUsername, {
        display_name: editingDisplayName?.trim() || null,
        print_limit: editingLimit ? Number(editingLimit) : null,
      });
      toast.success('User profile saved. New prints will show saved name and limit rules.');
      setEditOpen(false);
      await Promise.all([load(), loadUsers()]);
    } catch (error) {
      toast.error(error?.response?.data?.detail || error?.message || 'Failed to save user profile');
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleExport(kind) {
    setExporting(kind);
    try {
      const exportParams = { ...params };
      delete exportParams.page;
      delete exportParams.page_size;
      const { blob, filename } = await reportsApi.download(kind, exportParams);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      toast.success(`${kind.toUpperCase()} report downloaded`);
    } catch (error) {
      toast.error(error?.response?.data?.detail || error?.message || 'Export failed');
    } finally {
      setExporting(null);
    }
  }

  return (
    <PageMotion>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="page-title">Print Logs</h2>
            <p className="page-subtitle">Recent prints appear first. Edit user names and set per-user print limits.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" className="gap-2" onClick={() => handleExport('excel')} disabled={!!exporting}>
              <Download className="h-4 w-4" /> Excel
            </Button>
            <Button className="gap-2" onClick={() => handleExport('pdf')} disabled={!!exporting}>
              <Download className="h-4 w-4" /> PDF
            </Button>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Filter className="h-4 w-4" /> Filters</CardTitle>
            <CardDescription>Choose a user from dropdown to see only prints they took.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
              <div className="relative xl:col-span-2">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  className="pl-9"
                  placeholder="Search user, computer, printer, job id..."
                  value={filters.search}
                  onChange={(e) => updateFilter('search', e.target.value)}
                />
              </div>
              <Select value={filters.username} onChange={(e) => updateFilter('username', e.target.value)}>
                <option value="">All users</option>
                {userSummary.map((u) => (
                  <option key={u.username} value={u.username}>
                    {u.effective_name} ({u.prints_total})
                  </option>
                ))}
              </Select>
              <Input placeholder="Printer" value={filters.printer_name} onChange={(e) => updateFilter('printer_name', e.target.value)} />
              <Select value={filters.status} onChange={(e) => updateFilter('status', e.target.value)}>
                <option value="">All statuses</option>
                <option value="queued">Queued</option>
                <option value="printing">Printing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="cancelled">Cancelled</option>
              </Select>
              <Button variant="secondary" className="gap-2" onClick={() => { load(); loadUsers(); }}>
                <RefreshCw className="h-4 w-4" /> Apply
              </Button>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <Input type="date" value={filters.date_from} onChange={(e) => updateFilter('date_from', e.target.value)} />
              <Input type="date" value={filters.date_to} onChange={(e) => updateFilter('date_to', e.target.value)} />
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setFilters({ search: '', username: '', printer_name: '', status: '', date_from: '', date_to: '' });
                    setPage(1);
                  }}
                >
                  Clear filters
                </Button>
                <label className="text-xs text-muted">
                  <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} className="mr-2" />
                  Auto refresh
                </label>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Activity Table</CardTitle>
            <CardDescription>{formatNumber(data.total)} records</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-hidden rounded-2xl border border-border bg-white">
              <div className="max-h-[560px] overflow-auto">
                <Table>
                  <THead className="sticky top-0 z-10">
                    <TR>
                      <TH>Time</TH>
                      <TH>User</TH>
                      <TH>Computer</TH>
                      <TH>Printer</TH>
                      <TH className="text-right">Pages</TH>
                      <TH>Status</TH>
                      <TH>Actions</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {loading ? (
                      [...Array(6)].map((_, idx) => (
                        <TR key={idx}><TD colSpan={7}><Skeleton className="h-8" /></TD></TR>
                      ))
                    ) : data.items.length ? (
                      data.items.map((item) => (
                        <motion.tr
                          key={item.id}
                          layout
                          className={`border-b border-border/70 hover:bg-blue-50/40 ${item.user_limit_exceeded ? 'bg-red-50/70 hover:bg-red-50' : ''}`}
                        >
                          <TD>{formatDateTime(item.received_at)}</TD>
                          <TD>
                            <div>
                              <p className="text-sm font-medium text-text">{item.display_username || item.username || '—'}</p>
                              <p className="text-xs text-muted">@{item.username || 'unknown'}</p>
                            </div>
                          </TD>
                          <TD>{item.computer_name || '—'}</TD>
                          <TD>{item.printer_name || '—'}</TD>
                          <TD className="text-right">{item.total_pages || item.pages || 0}</TD>
                          <TD><StatusBadge status={item.status} /></TD>
                          <TD>
                            <Button variant="secondary" size="sm" className="gap-1" onClick={() => openEdit(item)}>
                              <Pencil className="h-3.5 w-3.5" /> Edit user
                            </Button>
                          </TD>
                        </motion.tr>
                      ))
                    ) : (
                      <TR><TD colSpan={7} className="py-10 text-center text-sm text-muted">No print logs match your filters</TD></TR>
                    )}
                  </TBody>
                </Table>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
              <div className="flex items-center gap-2">
                <span>Rows per page</span>
                <Select className="w-20" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
                  {PAGE_SIZES.map((size) => <option key={size} value={size}>{size}</option>)}
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" onClick={() => setPage(1)} disabled={page === 1}>First</Button>
                <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>Prev</Button>
                <span>Page {data.page} of {data.total_pages || 1}</span>
                <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.min(data.total_pages || 1, p + 1))} disabled={page >= (data.total_pages || 1)}>Next</Button>
                <Button variant="secondary" size="sm" onClick={() => setPage(data.total_pages || 1)} disabled={page >= (data.total_pages || 1)}>Last</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {editOpen ? (
          <div className="fixed inset-0 z-40 grid place-items-center bg-slate-900/30 p-4">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><UserCog className="h-4 w-4" /> Edit user profile</CardTitle>
                <CardDescription>
                  Save a display name and print-job limit. From the next print after the limit, rows are highlighted red.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">Raw username</label>
                  <Input value={editingUsername} disabled />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">Display name</label>
                  <Input value={editingDisplayName} onChange={(e) => setEditingDisplayName(e.target.value)} placeholder="e.g. John - Accounts" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">Print limit (jobs)</label>
                  <Input type="number" min="1" value={editingLimit} onChange={(e) => setEditingLimit(e.target.value)} placeholder="Leave blank for unlimited" />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="secondary" onClick={() => setEditOpen(false)} disabled={savingProfile}>Cancel</Button>
                  <Button onClick={saveUserProfile} disabled={savingProfile}>{savingProfile ? 'Saving...' : 'Save'}</Button>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : null}
      </div>
    </PageMotion>
  );
}
