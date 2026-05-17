// Main Layout - Clean, Simple & Modern

import React from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  Phone,
  Users,
  FileText,
  BarChart3,
  MessageSquare,
  Settings,
  Mic,
  ChevronsLeft,
  ChevronsRight,
  Bell,
  Megaphone,
  PhoneCall,
  Building2
} from 'lucide-react';

const MainLayout: React.FC = () => {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = React.useState(true);

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard', color: 'primary' },
    { path: '/calling', icon: Phone, label: 'Calling', color: 'success' },
    { path: '/popup', icon: Bell, label: 'Popup Queue', color: 'primary' },
    { path: '/leads', icon: Users, label: 'Leads', color: 'info' },
    { path: '/campaigns', icon: Megaphone, label: 'Campaigns', color: 'success' },
    { path: '/phone-numbers', icon: PhoneCall, label: 'Phone Numbers', color: 'info' },
    { path: '/stores', icon: Building2, label: 'Stores', color: 'success' },
    { path: '/history', icon: FileText, label: 'History', color: 'warning' },
    { path: '/analytics', icon: BarChart3, label: 'Analytics', color: 'primary' },
    { path: '/sms', icon: MessageSquare, label: 'SMS', color: 'warning' },
    { path: '/settings', icon: Settings, label: 'Settings', color: 'info' },
  ];

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <div className="flex min-h-screen bg-dark-bg">
      {/* Clean Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-screen bg-dark-surface border-r-2 border-dark-border shadow-modern-xl flex flex-col transition-all duration-300 z-50 ${
          sidebarOpen ? 'w-72' : 'w-25'
        }`}
      >
        {/* Logo */}
        <div className="p-6 border-b border-dark-border/50">
          <div className="flex items-center gap-3">
            <div className="relative w-11 h-11 rounded-xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center text-white shadow-glow-primary group-hover:scale-110">
              <Mic className="w-6 h-6" />
              <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-success shadow-glow-success animate-pulse"></div>
            </div>
            {sidebarOpen && (
              <div className="animate-fade-in">
                <h1 className="text-lg font-bold text-dark-text-primary">Outvox</h1>
                <p className="text-xs text-dark-text-muted">Outbound Voice Fleet</p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4">
          <div className="space-y-1">
            {navItems.map((item, index) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`group relative flex items-center gap-3 px-3 py-3 rounded-lg font-medium transition-all duration-200 animate-slide-in-left ${
                    active
                      ? 'bg-primary/10 text-primary-light border-l-4 border-primary shadow-sm'
                      : 'text-dark-text-secondary hover:text-dark-text-primary hover:bg-dark-elevated/50 border-l-4 border-transparent'
                  }`}
                  style={{ animationDelay: `${index * 0.05}s` }}
                  title={!sidebarOpen ? item.label : undefined}
                >
                  <Icon className={`w-5 h-5 flex-shrink-0 transition-transform duration-200 ${active ? 'scale-110' : 'group-hover:scale-110'}`} />
                  
                  {sidebarOpen && (
                    <span className="truncate animate-fade-in">{item.label}</span>
                  )}
                  
                  {/* Tooltip for collapsed */}
                  {!sidebarOpen && (
                    <div className="absolute left-full ml-4 px-3 py-2 bg-dark-surface border border-dark-border rounded-lg shadow-modern-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 whitespace-nowrap z-50 animate-scale-in">
                      <span className="text-sm font-semibold text-dark-text-primary">{item.label}</span>
                      <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 w-2 h-2 bg-dark-surface border-l border-b border-dark-border rotate-45"></div>
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Toggle */}
        <div className="p-3 border-t border-dark-border/50">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center justify-center px-3 py-2 text-xs font-semibold text-dark-text-muted hover:text-primary hover:bg-primary/5 rounded-lg transition-all duration-200 group"
          >
            {sidebarOpen ? (
              <span className="flex items-center gap-2">
                <ChevronsLeft /> 
                <span className='text-[15px] font-semibold'>Collapse</span>
              </span>
            ) : (
              <ChevronsRight/>
            )}
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main
        className={`flex-1 transition-all duration-300 ${
          sidebarOpen ? 'ml-72' : 'ml-20'
        }`}
        style={{ overflowX: 'hidden', width: '100%', maxWidth: '100%' }}
      >
        {/* Clean Top Bar */}
        <header className="sticky top-0 z-40 backdrop-blur-xl bg-dark-bg/80 border-b border-dark-border/50">
          <div className="px-8 py-4 flex items-center justify-between">
            {/* Status */}
            <div className="flex items-center gap-3">
              <div className="relative flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
                <div className="absolute w-4 h-4 rounded-full bg-success/30 animate-ping"></div>
              </div>
              <div>
                <span className="text-md font-bold text-dark-text-primary">System Online</span>
                <span className="text-sm text-dark-text-muted ml-2">All services running</span>
              </div>
            </div>
            
            {/* User */}
            <div className="flex items-center gap-3">
              <div className="px-3 py-1.5 bg-dark-surface border border-dark-border/50 rounded-lg">
                <span className="text-xs font-medium text-dark-text-muted">
                  {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-dark-surface border border-dark-border/50 hover:border-primary/40 rounded-lg transition-all cursor-pointer group">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center text-white font-bold text-xs shadow-sm group-hover:shadow-glow-primary transition-shadow">
                  AD
                </div>
                <span className="text-sm font-semibold text-dark-text-primary">Admin</span>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content - Clean padding */}
        <div className="p-6 md:p-8" style={{ overflowX: 'hidden', width: '100%', maxWidth: '100%' }}>
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
