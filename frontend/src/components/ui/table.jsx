import React from 'react';

import { cn } from '../../utils/cn.js';

export function Table({ className, ...props }) {
  return <table className={cn('w-full text-sm', className)} {...props} />;
}

export function THead({ className, ...props }) {
  return <thead className={cn('bg-slate-50/90', className)} {...props} />;
}

export function TBody(props) {
  return <tbody {...props} />;
}

export function TR({ className, ...props }) {
  return <tr className={cn('border-b border-border/70 transition hover:bg-blue-50/30', className)} {...props} />;
}

export function TH({ className, ...props }) {
  return <th className={cn('px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted', className)} {...props} />;
}

export function TD({ className, ...props }) {
  return <td className={cn('px-4 py-3 text-text', className)} {...props} />;
}
