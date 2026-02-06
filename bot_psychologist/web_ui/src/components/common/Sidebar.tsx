/**
 * Sidebar Component
 * 
 * Side navigation panel (optional, for future use).
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiHome, FiMessageCircle, FiUser, FiSettings, FiX } from 'react-icons/fi';
import clsx from 'clsx';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  onClick?: () => void;
}

const NavItem: React.FC<NavItemProps> = ({ to, icon, label, isActive, onClick }) => (
  <Link
    to={to}
    onClick={onClick}
    className={clsx(
      'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
      isActive
        ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
        : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
    )}
  >
    {icon}
    <span>{label}</span>
  </Link>
);

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();

  const navItems = [
    { to: '/', icon: <FiHome size={20} />, label: 'Главная' },
    { to: '/chat', icon: <FiMessageCircle size={20} />, label: 'Чат' },
    { to: '/profile', icon: <FiUser size={20} />, label: 'Профиль' },
    { to: '/settings', icon: <FiSettings size={20} />, label: 'Настройки' },
  ];

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed top-0 left-0 h-full w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 z-50 transform transition-transform duration-300 lg:translate-x-0 lg:static',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🧠</span>
            <span className="font-bold text-lg text-gray-900 dark:text-white">
              Bot Psychologist
            </span>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <FiX size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2">
          {navItems.map((item) => (
            <NavItem
              key={item.to}
              to={item.to}
              icon={item.icon}
              label={item.label}
              isActive={location.pathname === item.to}
              onClick={onClose}
            />
          ))}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-800">
          <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
            v1.0.0 • Phase 6
          </p>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;


