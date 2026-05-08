import React, { useEffect, useMemo, useState } from 'react';
import { Bell, Search } from 'lucide-react';
import { useLocation } from 'react-router-dom';

import { useAuth } from '../context/AuthContext.jsx';
import { dashboardApi } from '../api/endpoints.js';
import { Input } from './ui/input.jsx';
import { Button } from './ui/button.jsx';
import LiveBadge from './LiveBadge.jsx';
import StatusBadge from './StatusBadge.jsx';

const titles = {
  '/dashboard': 'Dashboard',
  '/print-logs': 'Print Logs',
  '/analytics': 'Analytics',
  '/reports': 'Reports',
  '/settings': 'Settings',
};

function initials(name = '') {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((x) => x[0])
    .join('')
    .toUpperCase() || 'AD';
}

export default function Header() {
  const { admin, logout } = useAuth();
  const location = useLocation();
  const [now, setNow] = useState(new Date());
  const [alerts, setAlerts] = useState([]);
  const [alertCount, setAlertCount] = useState(0);
  const [showAlerts, setShowAlerts] = useState(false);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const data = await dashboardApi.get();
        if (!mounted) return;
        setAlertCount(data.over_limit_alert_count || 0);
        setAlerts(data.over_limit_alerts || []);
      } catch (_e) {
        // keep header usable even if this request fails
      }
    };
    load();
    const timer = setInterval(load, 15000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const title = useMemo(() => titles[location.pathname] || 'Print Tracking', [location.pathname]);

  return (
    <header className="sticky top-0 z-20 border-b border-border/80 bg-white/90 px-6 py-3 backdrop-blur">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <img src="/ckp-logo.png" alt="CKP Workspace logo" className="h-6 w-6 rounded object-contain" />
            <h1 className="text-lg font-semibold text-text">{title}</h1>
          </div>
          <p className="text-xs text-muted">{now.toLocaleString()}</p>
        </div>

        <div className="flex flex-1 items-center gap-3 lg:justify-end">
          <div className="relative w-full max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Search jobs, users, printers..." className="pl-9" />
          </div>

          <LiveBadge label="System Healthy" />

          <div className="relative">
            <Button
              variant="secondary"
              size="icon"
              className="h-10 w-10 rounded-full"
              onClick={() => setShowAlerts((v) => !v)}
            >
              <Bell className="h-4 w-4" />
            </Button>
            {alertCount > 0 ? (
              <span className="absolute -right-1 -top-1 rounded-full bg-danger px-1.5 py-0.5 text-[10px] font-semibold text-white">
                {alertCount}
              </span>
            ) : null}
            {showAlerts ? (
              <div className="absolute right-0 top-12 z-30 w-[360px] rounded-xl border border-border bg-white p-3 shadow-soft">
                <p className="mb-2 text-sm font-semibold text-text">User limit alerts</p>
                {alerts.length === 0 ? (
                  <p className="text-xs text-muted">No limit violations detected.</p>
                ) : (
                  <div className="max-h-64 space-y-2 overflow-auto">
                    {alerts.slice(0, 12).map((a) => (
                      <div key={a.id} className="rounded-lg border border-red-100 bg-red-50/60 p-2.5">
                        <div className="flex items-center justify-between gap-2">
                          <p className="truncate text-xs font-medium text-text">
                            {a.display_username || a.username || 'Unknown user'}
                          </p>
                          <StatusBadge status={a.status} />
                        </div>
                        <p className="mt-1 truncate text-[11px] text-muted">
                          {a.document_name || 'Untitled'} · {a.printer_name || 'Unknown printer'}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : null}
          </div>

          <div className="flex items-center gap-2 rounded-full border border-border bg-white px-2 py-1 shadow-sm">
            <div className="grid h-8 w-8 place-items-center rounded-full bg-primary text-xs font-semibold text-white">
              {initials(admin?.full_name || admin?.username)}
            </div>
            <div className="hidden pr-1 sm:block">
              <p className="text-xs font-semibold text-text">{admin?.full_name || admin?.username || 'Admin'}</p>
              <button onClick={logout} className="text-[11px] text-muted transition hover:text-text">
                Sign out
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
