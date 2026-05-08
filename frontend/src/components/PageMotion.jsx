import React from 'react';
import { motion } from 'framer-motion';

export default function PageMotion({ children }) {
  return (
    <motion.div
      className="page-shell"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  );
}
