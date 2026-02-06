/**
 * TypingIndicator Component
 * 
 * Animated indicator showing bot is processing.
 */

import React from 'react';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
      <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-full px-4 py-2">
        <div 
          className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"
          style={{ animationDelay: '0ms' }}
        />
        <div 
          className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"
          style={{ animationDelay: '150ms' }}
        />
        <div 
          className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"
          style={{ animationDelay: '300ms' }}
        />
      </div>
      <span className="text-sm">Bot думает...</span>
    </div>
  );
};

export default TypingIndicator;


