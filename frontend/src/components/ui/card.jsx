import React from 'react';

import { cn } from '../../utils/cn.js';

const Card = React.forwardRef(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('glass-card', className)} {...props} />
));
Card.displayName = 'Card';

const CardHeader = ({ className, ...props }) => (
  <div className={cn('flex items-start justify-between p-5 pb-2', className)} {...props} />
);

const CardTitle = ({ className, ...props }) => (
  <h3 className={cn('text-sm font-semibold text-text', className)} {...props} />
);

const CardDescription = ({ className, ...props }) => (
  <p className={cn('text-sm text-muted', className)} {...props} />
);

const CardContent = ({ className, ...props }) => (
  <div className={cn('p-5 pt-2', className)} {...props} />
);

export { Card, CardHeader, CardTitle, CardDescription, CardContent };
