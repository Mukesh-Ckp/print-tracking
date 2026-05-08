import React from 'react';
import { CircleDot } from 'lucide-react';

import { Badge } from './ui/badge.jsx';

export default function LiveBadge({ label = 'Live Monitoring' }) {
  return (
    <Badge variant="success" className="gap-1.5">
      <CircleDot className="h-3.5 w-3.5 animate-pulseSoft" />
      {label}
    </Badge>
  );
}
