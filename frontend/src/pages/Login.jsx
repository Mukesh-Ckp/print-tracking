import React, { useState } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext.jsx';
import { Button } from '../components/ui/button.jsx';
import { Card, CardContent, CardHeader } from '../components/ui/card.jsx';
import { Input } from '../components/ui/input.jsx';

export default function Login() {
  const { login, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={location.state?.from?.pathname || '/dashboard'} replace />;
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (!username || !password) {
      toast.error('Please enter username and password');
      return;
    }

    setSubmitting(true);
    try {
      await login(username, password);
      toast.success('Welcome back');
      navigate('/dashboard', { replace: true });
    } catch (error) {
      toast.error(error?.response?.data?.detail || error?.message || 'Authentication failed');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-background px-4 py-12">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="w-full max-w-md">
          <div className="mb-3">
            <h2 className="text-lg font-semibold text-text">Sign in</h2>
            <p className="text-sm text-muted">Use administrator credentials</p>
          </div>
          <Card className="mx-auto w-full border-white/70">
            <CardHeader>
              <div className="mb-2 flex items-center gap-3">
                <img src="/ckp-logo.png" alt="CKP Workspace logo" className="h-10 w-10 rounded-lg object-contain" />
                <div>
                  <p className="text-sm font-semibold text-text">Print Tracking</p>
                  <p className="text-xs text-muted">CKP Workspace</p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <form onSubmit={onSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium uppercase tracking-wide text-muted">Username or email</label>
                  <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="admin" autoComplete="username" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium uppercase tracking-wide text-muted">Password</label>
                  <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="��������" autoComplete="current-password" />
                </div>
                <Button type="submit" className="w-full" disabled={submitting || loading}>
                  {submitting ? 'Signing in...' : 'Sign in'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    
  );
}
