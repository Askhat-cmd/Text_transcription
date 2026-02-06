/**
 * Loader Component
 * 
 * Loading spinner with various sizes and styles.
 */

import React from 'react';
import clsx from 'clsx';

interface LoaderProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  color?: 'primary' | 'white' | 'gray';
  className?: string;
  text?: string;
}

export const Loader: React.FC<LoaderProps> = ({
  size = 'md',
  color = 'primary',
  className = '',
  text,
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
    xl: 'w-16 h-16 border-4',
  };

  const colorClasses = {
    primary: 'border-purple-200 border-t-purple-600 dark:border-purple-800 dark:border-t-purple-400',
    white: 'border-white/30 border-t-white',
    gray: 'border-gray-200 border-t-gray-600 dark:border-gray-700 dark:border-t-gray-400',
  };

  return (
    <div className={clsx('flex flex-col items-center justify-center gap-3', className)}>
      <div
        className={clsx(
          'rounded-full animate-spin',
          sizeClasses[size],
          colorClasses[color]
        )}
      />
      {text && (
        <span className="text-sm text-gray-500 dark:text-gray-400">{text}</span>
      )}
    </div>
  );
};

/**
 * Full page loader overlay
 */
export const PageLoader: React.FC<{ text?: string }> = ({ text = 'Загрузка...' }) => (
  <div className="fixed inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm z-50">
    <Loader size="xl" text={text} />
  </div>
);

/**
 * Inline loader for buttons
 */
export const ButtonLoader: React.FC = () => (
  <Loader size="sm" color="white" />
);

export default Loader;


