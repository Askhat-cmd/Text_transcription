/**
 * ChatWindow Component
 * 
 * Main chat container with header, messages area, and input box.
 */

import React, { useEffect, useRef } from 'react';
import type { Message, UserLevel } from '../../types';
import MessageList from './MessageList';
import InputBox from './InputBox';
import TypingIndicator from './TypingIndicator';
import { FiRefreshCw, FiSettings, FiUser } from 'react-icons/fi';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
  onClearChat?: () => void;
  currentUserState?: string;
  error?: string | null;
  onClearError?: () => void;
  onSettingsClick?: () => void;
  onProfileClick?: () => void;
  userId?: string;
  userLevel?: UserLevel;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onClearChat,
  currentUserState,
  error,
  onClearError,
  onSettingsClick,
  onProfileClick,
  userId,
  userLevel,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-purple-700 text-white p-4 shadow-md">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h1 className="text-xl font-bold">🧠 Bot Psychologist</h1>
            <p className="text-sm opacity-90">Адаптивный QA с состояниями и путями</p>
          </div>
          
          {/* Header Actions */}
          <div className="flex items-center gap-2">
            {onClearChat && messages.length > 0 && (
              <button
                onClick={onClearChat}
                className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
                title="Очистить чат"
              >
                <FiRefreshCw size={18} />
              </button>
            )}
            {onProfileClick && (
              <button
                onClick={onProfileClick}
                className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
                title="Профиль"
              >
                <FiUser size={18} />
              </button>
            )}
            {onSettingsClick && (
              <button
                onClick={onSettingsClick}
                className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
                title="Настройки"
              >
                <FiSettings size={18} />
              </button>
            )}
          </div>
        </div>
        
        {/* User info and state */}
        <div className="flex items-center gap-3 mt-2 flex-wrap">
          {userId && (
            <span className="text-xs bg-white/20 px-2 py-1 rounded">
              👤 {userId}
            </span>
          )}
          {userLevel && (
            <span className="text-xs bg-white/20 px-2 py-1 rounded">
              📊 {userLevel === 'beginner' ? '🌱 Начинающий' : userLevel === 'intermediate' ? '🌿 Средний' : '🌳 Продвинутый'}
            </span>
          )}
          {currentUserState && (
            <span className="text-xs bg-white/20 px-2 py-1 rounded">
              🧠 {currentUserState}
            </span>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-100 dark:bg-red-900/30 border-b border-red-200 dark:border-red-800 p-3 flex items-center justify-between">
          <span className="text-red-700 dark:text-red-300 text-sm">
            ⚠️ {error}
          </span>
          {onClearError && (
            <button
              onClick={onClearError}
              className="text-red-500 hover:text-red-700 dark:text-red-400 text-sm underline"
            >
              Закрыть
            </button>
          )}
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
            <div className="text-center max-w-md">
              <p className="text-4xl mb-4">👋</p>
              <p className="text-lg font-semibold mb-2">Добро пожаловать!</p>
              <p className="text-sm">
                Задайте вопрос о саморазвитии, и я помогу вам на пути трансформации.
                Я учитываю ваше состояние и адаптирую ответы под ваш уровень.
              </p>
            </div>
          </div>
        ) : (
          <>
            <MessageList messages={messages} />
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <InputBox onSendMessage={onSendMessage} isLoading={isLoading} />
    </div>
  );
};

export default ChatWindow;
