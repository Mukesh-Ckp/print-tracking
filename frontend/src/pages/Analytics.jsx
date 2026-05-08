import React, { useEffect, useMemo, useState } from 'react';
import { Activity, BarChart3, PieChart as PieChartIcon, Printer, Users } from 'lucide-react';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from 'recharts';
import toast from 'react-hot-toast';

import { dashboardApi } from '../api/endpoints.js';
import PageMotion from '../components/PageMotion.jsx';
import KpiCard from '../components/KpiCard.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card.jsx';
import { Skeleton } from '../components/ui/skeleton.jsx';
import { formatNumber } from '../utils/format.js';

const COLORS = ['#2563EB', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

function TooltipContent({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-white p-2.5 text-xs shadow-soft">
      <div className="font-medium text-text">{label}</div>
      {payload.map((item) => <div key={item.name} className="text-muted">{item.name}: {formatNumber(item.value)}</div>)}
    </div>
  );
}

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    dashboardApi.get()
      .then((response) => mounted && setData(response))
      .catch((error) => toast.error(error?.response?.data?.detail || error?.message || 'Failed to load analytics'))
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, []);

  const statusMix = useMemo(() => {
    if (!data?.status_breakdown) return [];
    return Object.entries(data.status_breakdown)
      .filter(([, value]) => value > 0)
      .map(([name, value]) => ({ name, value }));
  }, [data]);

  if (loading) return <div className="grid gap-4 md:grid-cols-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-56" />)}</div>;
  if (!data) return null;

  const stats = data.stats;

  return (
    <PageMotion>
      <div className="space-y-6">
        <div>
          <h2 className="page-title">Enterprise Analytics</h2>
          <p className="page-subtitle">Deep usage patterns and operational performance insights</p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <KpiCard icon={Activity} label="Weekly Prints" value={formatNumber(stats.prints_this_week)} delta={`${formatNumber(stats.pages_this_week)} pages`} />
          <KpiCard icon={Users} label="Active Users" value={formatNumber(stats.active_users_today)} delta="Live user activity" iconTone="text-emerald-700 bg-emerald-100" />
          <KpiCard icon={Printer} label="Active Printers" value={formatNumber(stats.active_printers)} delta="Connected devices" iconTone="text-violet-700 bg-violet-100" />
          <KpiCard icon={BarChart3} label="All-time Prints" value={formatNumber(stats.prints_total)} delta={`${formatNumber(stats.pages_total)} pages`} iconTone="text-amber-700 bg-amber-100" />
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <CardHeader>
              <CardTitle>30-Day Usage Trend</CardTitle>
              <CardDescription>Daily print & page activity</CardDescription>
            </CardHeader>
            <CardContent className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.daily_last_30_days}>
                  <CartesianGrid stroke="#E5E7EB" vertical={false} />
                  <XAxis dataKey="label" tickFormatter={(v) => v.slice(5)} tick={{ fill: '#6B7280', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} />
                  <Tooltip content={<TooltipContent />} />
                  <Area dataKey="prints" stroke="#2563EB" fill="#DBEAFE" strokeWidth={2} />
                  <Area dataKey="pages" stroke="#10B981" fillOpacity={0} strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><PieChartIcon className="h-4 w-4" /> Status Mix</CardTitle>
              <CardDescription>Job health distribution</CardDescription>
            </CardHeader>
            <CardContent className="h-80">
              {statusMix.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={statusMix} dataKey="value" innerRadius={50} outerRadius={84}>
                      {statusMix.map((entry, idx) => <Cell key={entry.name} fill={COLORS[idx % COLORS.length]} />)}
                    </Pie>
                    <Tooltip content={<TooltipContent />} />
                  </PieChart>
                </ResponsiveContainer>
              ) : <p className="text-sm text-muted">No status data yet.</p>}
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Top Users</CardTitle>
              <CardDescription>Highest print consumers this month</CardDescription>
            </CardHeader>
            <CardContent className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.top_users} layout="vertical" margin={{ left: 16 }}>
                  <CartesianGrid stroke="#E5E7EB" horizontal={false} />
                  <XAxis type="number" tick={{ fill: '#6B7280', fontSize: 11 }} />
                  <YAxis dataKey="username" type="category" tick={{ fill: '#6B7280', fontSize: 11 }} width={90} />
                  <Tooltip content={<TooltipContent />} />
                  <Bar dataKey="prints" fill="#2563EB" radius={[0, 8, 8, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top Printers</CardTitle>
              <CardDescription>Printer utilization and load balancing</CardDescription>
            </CardHeader>
            <CardContent className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.top_printers}>
                  <CartesianGrid stroke="#E5E7EB" vertical={false} />
                  <XAxis dataKey="printer_name" tick={{ fill: '#6B7280', fontSize: 10 }} tickFormatter={(v) => v.slice(0, 12)} />
                  <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} />
                  <Tooltip content={<TooltipContent />} />
                  <Bar dataKey="prints" fill="#10B981" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageMotion>
  );
}
