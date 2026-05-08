import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';

import Header from './Header.jsx';
import Sidebar from './Sidebar.jsx';

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((prev) => !prev)} />
      <div className={`transition-all duration-300 ${collapsed ? 'ml-[88px]' : 'ml-[250px]'}`}>
        <Header />
        <main className="px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
