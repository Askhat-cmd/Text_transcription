/**
 * Footer Component
 * 
 * Bottom bar with version info and links.
 */

import React from 'react';
import { FiGithub, FiHeart } from 'react-icons/fi';

interface FooterProps {
  className?: string;
}

export const Footer: React.FC<FooterProps> = ({ className = '' }) => {
  return (
    <footer className={`bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          {/* Version info */}
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Bot Psychologist v1.0.0 • Phase 6 Web UI
          </div>

          {/* Made with love */}
          <div className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
            Made with <FiHeart className="text-red-500" /> for self-development
          </div>

          {/* Links */}
          <div className="flex items-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
            >
              <FiGithub size={20} />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;


