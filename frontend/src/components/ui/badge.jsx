import React from 'react';
import { cva } from 'class-variance-authority';

import { cn } from '../../utils/cn.js';

const badgeVariants = cva('inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium', {
  variants: {
    variant: {
      neutral: 'bg-slate-100 text-slate-700',
      success: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
      warning: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
      danger: 'bg-red-50 text-red-700 ring-1 ring-red-200',
      info: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
    },
  },
  defaultVariants: {
    variant: 'neutral',
  },
});

export function Badge({ className, variant, ...props }) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
