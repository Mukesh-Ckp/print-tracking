import React, { useEffect, useState } from 'react';
import { Building2, KeyRound, Printer, Server, UserCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';

import { API_BASE_URL } from '../api/axios.js';
import { printersApi } from '../api/endpoints.js';
import PageMotion from '../components/PageMotion.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card.jsx';
import { Skeleton } from '../components/ui/skeleton.jsx';
import { Table, TBody, TD, TH, THead, TR } from '../components/ui/table.jsx';
import { formatDateTime } from '../utils/format.js';

export default function Settings() {
  const { admin } = useAuth();
  const [printers, setPrinters] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    printersApi.list()
      .then(setPrinters)
      .catch((error) => toast.error(error?.response?.data?.detail || error?.message || 'Failed to load printers'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <PageMotion>
      <div className="space-y-6">
        <div>
          <h2 className="page-title">System Settings</h2>
          <p className="page-subtitle">Tenant profile, environment details, and printer infrastructure</p>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><UserCircle2 className="h-4 w-4" /> Administrator Profile</CardTitle>
              <CardDescription>Authenticated account information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Item label="Username" value={admin?.username} />
              <Item label="Email" value={admin?.email} />
              <Item label="Full name" value={admin?.full_name || '—'} />
              <Item label="Super admin" value={admin?.is_superuser ? 'Yes' : 'No'} />
              <Item label="Last login" value={formatDateTime(admin?.last_login_at)} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Server className="h-4 w-4" /> Platform Configuration</CardTitle>
              <CardDescription>Environment and integration metadata</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Item label="API Base URL" value={API_BASE_URL} />
              <Item label="Frontend Stack" value="React + Tailwind + Framer Motion" />
              <Item label="Backend Stack" value="FastAPI + SQLAlchemy" />
              <Item label="Database" value="PostgreSQL / SQLite" />
              <Item label="Agent Mode" value="Windows Print Spooler Monitor" />
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Printer className="h-4 w-4" /> Registered Printers</CardTitle>
            <CardDescription>Live printer inventory from the tracking backend</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-9" />)}</div>
            ) : (
              <div className="overflow-hidden rounded-2xl border border-border">
                <Table>
                  <THead>
                    <TR>
                      <TH>Name</TH>
                      <TH>IP</TH>
                      <TH>Network</TH>
                      <TH>Active</TH>
                      <TH>Last Seen</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {printers.length ? printers.map((printer) => (
                      <TR key={printer.id}>
                        <TD>{printer.name}</TD>
                        <TD>{printer.ip_address || '—'}</TD>
                        <TD>{printer.network || '—'}</TD>
                        <TD>{printer.is_active ? 'Online' : 'Offline'}</TD>
                        <TD>{formatDateTime(printer.last_seen_at)}</TD>
                      </TR>
                    )) : <TR><TD colSpan={5} className="py-6 text-center text-sm text-muted">No registered printers found</TD></TR>}
                  </TBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Building2 className="h-4 w-4" /> Enterprise Recommendations</CardTitle>
            <CardDescription>Operational best practices for production rollout</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted">
            <p>• Keep the print-agent as a Windows service on the main office print server.</p>
            <p>• Rotate <KeyRound className="inline h-3.5 w-3.5" /> <span className="font-medium text-text">AGENT_API_KEY</span> quarterly.</p>
            <p>• Use Neon PostgreSQL for production persistence and long-term reporting.</p>
            <p>• Restrict CORS and admin access to authorized office domains only.</p>
          </CardContent>
        </Card>
      </div>
    </PageMotion>
  );
}

function Item({ label, value }) {
  return (
    <div className="rounded-xl border border-border bg-white px-3 py-2">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-sm font-medium text-text break-all">{value}</p>
    </div>
  );
}
