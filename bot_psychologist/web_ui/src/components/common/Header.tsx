/**
 * Header Component
 * 
 * Top navigation bar with logo, navigation links, and theme toggle.
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiSun, FiMoon, FiMonitor, FiSettings, FiUser, FiMessageCircle, FiHome } from 'react-icons/fi';
import { useTheme } from '../../hooks/useTheme';
import clsx from 'clsx';

interface NavLinkProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
}

const NavLink: React.FC<NavLinkProps> = ({ to, icon, label, isActive }) => (
  <Link
    to={to}
    className={clsx(
      'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
      isActive
        ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
        : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
    )}
  >
    {icon}
    <span className="hidden sm:inline">{label}</span>
  </Link>
);

export const Header: React.FC = () => {
  const location = useLocation();
  const { theme, setTheme, isDark } = useTheme();

  const navLinks = [
    { to: '/', icon: <FiHome size={20} />, label: 'Главная' },
    { to: '/chat', icon: <FiMessageCircle size={20} />, label: 'Чат' },
    { to: '/profile', icon: <FiUser size={20} />, label: 'Профиль' },
    { to: '/settings', icon: <FiSettings size={20} />, label: 'Настройки' },
  ];

  const cycleTheme = () => {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  };

  const ThemeIcon = () => {
    if (theme === 'system') return <FiMonitor size={20} />;
    if (isDark) return <FiMoon size={20} />;
    return <FiSun size={20} />;
  };

  return (
    <header className="sticky top-0 z-50 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">🧠</span>
            <span className="font-bold text-xl text-gray-900 dark:text-white hidden sm:inline">
              Bot Psychologist
            </span>
          </Link>

          {/* Navigation */}
          <nav className="flex items-center gap-1">
            {navLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                icon={link.icon}
                label={link.label}
                isActive={location.pathname === link.to}
              />
            ))}

            {/* Theme Toggle */}
            <button
              onClick={cycleTheme}
              className="ml-2 p-2 rounded-lg text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 transition-colors"
              title={`Theme: ${theme}`}
            >
              <ThemeIcon />
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;
