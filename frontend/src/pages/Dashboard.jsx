import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, Printer, RefreshCw, ShieldCheck, TrendingUp, Users } from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import toast from 'react-hot-toast';

import { dashboardApi } from '../api/endpoints.js';
import KpiCard from '../components/KpiCard.jsx';
import PageMotion from '../components/PageMotion.jsx';
import StatusBadge from '../components/StatusBadge.jsx';
import { Button } from '../components/ui/button.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card.jsx';
import { Skeleton } from '../components/ui/skeleton.jsx';
import { formatNumber, formatRelative } from '../utils/format.js';

const REFRESH_MS = 15000;
const STATUS_COLORS = ['#10B981', '#2563EB', '#F59E0B', '#EF4444', '#6B7280'];

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-white p-3 text-xs shadow-soft">
      <p className="font-semibold text-text">{label}</p>
      {payload.map((item) => (
        <p key={item.name} className="mt-1 text-muted">
          <span className="font-medium text-text">{item.name}:</span> {formatNumber(item.value)}
        </p>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const lastIdRef = useRef(0);

  const load = useCallback(async (withLoader = false) => {
    if (withLoader) setLoading(true);
    setRefreshing(true);
    try {
      const response = await dashboardApi.get();
      const newest = response.recent_prints?.[0]?.id ?? 0;
      if (lastIdRef.current && newest > lastIdRef.current) {
        const delta = newest - lastIdRef.current;
        toast.success(`${delta} new print ${delta > 1 ? 'jobs' : 'job'} detected`);
      }
      lastIdRef.current = newest;
      setData(response);
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.message || 'Failed to load dashboard';
      toast.error(detail);
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(true);
    const interval = setInterval(() => load(false), REFRESH_MS);
    return () => clearInterval(interval);
  }, [load]);

  const statusData = useMemo(() => {
    if (!data?.status_breakdown) return [];
    return Object.entries(data.status_breakdown)
      .filter(([, value]) => value > 0)
      .map(([name, value]) => ({ name, value }));
  }, [data]);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[...Array(8)].map((_, idx) => (
          <Skeleton key={idx} className="h-40" />
        ))}
      </div>
    );
  }

  if (!data) return null;

  const { stats, recent_prints: recentPrints = [], hourly_today: hourly = [], daily_last_30_days: daily = [] } = data;

  return (
    <PageMotion>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="page-title">Infrastructure Overview</h2>
            <p className="page-subtitle">
              Real-time print operations across office systems. Last sync {formatRelative(data.generated_at)}
            </p>
          </div>
          <Button variant="secondary" onClick={() => load(false)} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <KpiCard
            icon={TrendingUp}
            label="Prints Today"
            value={formatNumber(stats.prints_today)}
            delta={`${formatNumber(stats.pages_today)} pages`}
          />
          <KpiCard
            icon={Printer}
            label="Monthly Prints"
            value={formatNumber(stats.prints_this_month)}
            delta={`${formatNumber(stats.pages_this_month)} pages this month`}
            iconTone="text-blue-700 bg-blue-100"
          />
          <KpiCard
            icon={Users}
            label="Active Users"
            value={formatNumber(stats.active_users_today)}
            delta="Unique users today"
            iconTone="text-emerald-700 bg-emerald-100"
          />
          <KpiCard
            icon={AlertTriangle}
            label="Failed Jobs"
            value={formatNumber(stats.failed_today)}
            delta={stats.failed_today ? 'Needs attention' : 'No incidents today'}
            iconTone={stats.failed_today ? 'text-red-700 bg-red-100' : 'text-emerald-700 bg-emerald-100'}
          />
          <KpiCard
            icon={ShieldCheck}
            label="Total Prints"
            value={formatNumber(stats.prints_total)}
            delta={`${formatNumber(stats.pages_total)} pages all-time`}
            iconTone="text-violet-700 bg-violet-100"
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <div>
                <CardTitle>Today’s Print Trend</CardTitle>
                <CardDescription>Live print jobs and pages volume by hour</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={hourly}>
                  <defs>
                    <linearGradient id="printsArea" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#E5E7EB" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: '#6B7280', fontSize: 11 }} tickMargin={8} />
                  <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Area dataKey="prints" stroke="#2563EB" fill="url(#printsArea)" strokeWidth={2} name="Prints" />
                  <Area dataKey="pages" stroke="#10B981" fillOpacity={0} strokeWidth={2} name="Pages" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Status Breakdown</CardTitle>
              <CardDescription>Current month job states</CardDescription>
            </CardHeader>
            <CardContent className="h-80">
              {statusData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={statusData} dataKey="value" innerRadius={52} outerRadius={82} paddingAngle={3}>
                      {statusData.map((entry, idx) => (
                        <Cell key={entry.name} fill={STATUS_COLORS[idx % STATUS_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="grid h-full place-items-center text-sm text-muted">No status data yet</div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>30-Day Usage Analytics</CardTitle>
              <CardDescription>Print volume trends for monthly planning</CardDescription>
            </CardHeader>
            <CardContent className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={daily}>
                  <CartesianGrid stroke="#E5E7EB" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: '#6B7280', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="prints" fill="#2563EB" radius={[6, 6, 0, 0]} name="Prints" />
                  <Bar dataKey="pages" fill="#10B981" radius={[6, 6, 0, 0]} name="Pages" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest print events in real-time</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentPrints.slice(0, 6).map((item) => (
                <motion.div key={item.id} layout className="rounded-xl border border-border bg-white p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-text">{item.document_name || 'Untitled document'}</p>
                      <p className="text-xs text-muted">{item.username || 'Unknown user'} · {item.printer_name || 'Unknown printer'}</p>
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                </motion.div>
              ))}
              {!recentPrints.length ? <p className="text-sm text-muted">No recent print activity yet.</p> : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </PageMotion>
  );
}
