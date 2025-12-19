/**
 * InputBox Component
 * 
 * Chat input field with send button.
 */

import React, { useState, useRef, useEffect } from 'react';
import { FiSend } from 'react-icons/fi';
import clsx from 'clsx';

interface InputBoxProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  placeholder?: string;
}

export const InputBox: React.FC<InputBoxProps> = ({
  onSendMessage,
  isLoading,
  placeholder = 'Задайте вопрос о саморазвитии...',
}) => {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput('');
      // Reset height
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = input.trim().length > 0 && !isLoading;

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-4">
      <div className="flex items-end gap-3">
        <div className="flex-1 relative">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            rows={1}
            className={clsx(
              'w-full px-4 py-3 pr-12 rounded-xl border resize-none',
              'bg-white dark:bg-gray-700',
              'border-gray-300 dark:border-gray-600',
              'text-gray-900 dark:text-white',
              'placeholder-gray-400 dark:placeholder-gray-500',
              'focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-all duration-200'
            )}
          />
          <div className="absolute right-3 bottom-3 text-xs text-gray-400">
            {input.length > 0 && `${input.length}/500`}
          </div>
        </div>
        
        <button
          onClick={handleSend}
          disabled={!canSend}
          className={clsx(
            'flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center',
            'transition-all duration-200',
            canSend
              ? 'bg-purple-600 hover:bg-purple-700 text-white shadow-lg hover:shadow-xl'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
          )}
          title="Отправить (Enter)"
        >
          <FiSend size={20} className={canSend ? 'translate-x-0.5' : ''} />
        </button>
      </div>
      
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-2 text-center">
        Enter — отправить • Shift+Enter — новая строка
      </p>
    </div>
  );
};

export default InputBox;
