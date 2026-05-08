import React from 'react';
import { motion } from 'framer-motion';

import { Card, CardContent } from './ui/card.jsx';

export default function KpiCard({ icon: Icon, label, value, delta, iconTone = 'text-primary bg-blue-50' }) {
  return (
    <motion.div whileHover={{ y: -3 }} transition={{ type: 'spring', stiffness: 280, damping: 22 }}>
      <Card className="border-white/70">
        <CardContent className="flex items-start justify-between gap-3 p-5">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight text-text">{value}</p>
            {delta ? <p className="mt-1 text-xs text-muted">{delta}</p> : null}
          </div>
          <div className={`rounded-xl p-2.5 ${iconTone}`}>
            <Icon className="h-5 w-5" />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
