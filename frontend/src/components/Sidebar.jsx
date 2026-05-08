import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  BarChart3,
  FileSpreadsheet,
  Home,
  Printer,
  ScrollText,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';

import { cn } from '../utils/cn.js';
import { Button } from './ui/button.jsx';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: Home },
  { to: '/print-logs', label: 'Print Logs', icon: ScrollText },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/reports', label: 'Reports', icon: FileSpreadsheet },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ collapsed, onToggle }) {
  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-30 border-r border-border bg-white/90 backdrop-blur transition-all duration-300',
        collapsed ? 'w-[88px]' : 'w-[250px]',
      )}
    >
      <div className="flex h-16 items-center justify-between border-b border-border px-4">
        <div className="flex items-center gap-3 overflow-hidden">
          <img src="/ckp-logo.png" alt="CKP Workspace logo" className="h-9 w-9 rounded-lg object-contain" />
          {!collapsed ? (
            <div>
              <p className="text-sm font-semibold text-text">Print Tracking</p>
              <p className="text-xs text-muted">CKP Workspace</p>
            </div>
          ) : null}
        </div>
        <Button size="icon" variant="ghost" onClick={onToggle} className="h-8 w-8 shrink-0">
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </Button>
      </div>

      <nav className="space-y-1 p-3">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'flex h-10 items-center rounded-xl px-3 text-sm font-medium text-muted transition hover:bg-slate-100 hover:text-text',
                  isActive && 'bg-blue-50 text-primary ring-1 ring-blue-100',
                  collapsed ? 'justify-center' : 'gap-3',
                )
              }
            >
              <Icon className="h-4.5 w-4.5" />
              {!collapsed ? <span>{item.label}</span> : null}
            </NavLink>
          );
        })}
      </nav>

      <div className="absolute inset-x-3 bottom-3 rounded-xl border border-blue-100 bg-blue-50/80 p-3">
        <div className="flex items-center gap-2 text-primary">
          <Printer className="h-4 w-4" />
          {!collapsed ? <p className="text-xs font-medium">Printer online</p> : null}
        </div>
        {!collapsed ? <p className="mt-1 text-xs text-muted">HP Smart Tank 660-670</p> : null}
      </div>
    </aside>
  );
}
