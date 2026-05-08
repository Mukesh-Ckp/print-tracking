import React from 'react';

import { Badge } from './ui/badge.jsx';

const MAP = {
  completed: 'success',
  printing: 'info',
  queued: 'warning',
  paused: 'warning',
  failed: 'danger',
  cancelled: 'danger',
  unknown: 'neutral',
};

export default function StatusBadge({ status }) {
  const key = String(status || 'unknown').toLowerCase();
  return <Badge variant={MAP[key] || 'neutral'}>{key}</Badge>;
}
