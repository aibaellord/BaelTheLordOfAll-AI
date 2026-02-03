import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Puzzle,
  Workflow,
  Users,
  Activity,
  Settings,
  Menu,
  X,
  Bell,
  User,
  LogOut,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { motion, AnimatePresence } from 'framer-motion';

interface LayoutProps {
  children: React.ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Plugins', href: '/plugins', icon: Puzzle },
  { name: 'Workflows', href: '/workflows', icon: Workflow },
  { name: 'Agents', href: '/agents', icon: Users },
  { name: 'Monitoring', href: '/monitoring', icon: Activity },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const { user, logout } = useAuthStore();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-gray-600 z-40 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              transition={{ type: 'spring', damping: 30 }}
              className="fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-xl lg:hidden"
            >
              <div className="flex items-center justify-between h-16 px-4 border-b">
                <span className="text-2xl font-bold text-indigo-600">BAEL</span>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="p-2 rounded-md hover:bg-gray-100"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <nav className="px-3 py-4 space-y-1">
                {navigation.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.href;
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      onClick={() => setSidebarOpen(false)}
                      className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                        isActive
                          ? 'bg-indigo-50 text-indigo-600'
                          : 'text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      <Icon className="w-5 h-5 mr-3" />
                      {item.name}
                    </Link>
                  );
                })}
              </nav>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-grow pt-5 overflow-y-auto bg-white border-r">
          <div className="flex items-center flex-shrink-0 px-4">
            <span className="text-2xl font-bold text-indigo-600">BAEL</span>
            <span className="ml-2 text-sm text-gray-500">v2.1.0</span>
          </div>
          <nav className="flex-1 px-3 mt-8 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-600'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="w-5 h-5 mr-3" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top nav */}
        <div className="sticky top-0 z-10 flex h-16 bg-white border-b shadow-sm">
          <button
            onClick={() => setSidebarOpen(true)}
            className="px-4 text-gray-500 lg:hidden focus:outline-none"
          >
            <Menu className="w-6 h-6" />
          </button>
          <div className="flex items-center justify-between flex-1 px-4">
            <h1 className="text-xl font-semibold text-gray-900">
              {navigation.find((item) => item.href === location.pathname)?.name || 'Dashboard'}
            </h1>
            <div className="flex items-center space-x-4">
              <button className="p-2 text-gray-500 rounded-md hover:bg-gray-100">
                <Bell className="w-5 h-5" />
              </button>
              <div className="flex items-center space-x-3">
                <div className="flex items-center justify-center w-8 h-8 text-white bg-indigo-600 rounded-full">
                  <User className="w-5 h-5" />
                </div>
                <div className="hidden md:block">
                  <p className="text-sm font-medium text-gray-900">{user?.name || 'Admin'}</p>
                  <p className="text-xs text-gray-500">{user?.email || 'admin@bael.ai'}</p>
                </div>
                <button
                  onClick={logout}
                  className="p-2 text-gray-500 rounded-md hover:bg-gray-100"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="py-6">
          <div className="px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
