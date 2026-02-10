/**
 * ChatWindow Component
 *
 * Main chat container with header, messages area, and input box.
 */

import React, { useEffect, useRef, useState } from 'react';
import type { Message } from '../../types';
import MessageList from './MessageList';
import InputBox from './InputBox';
import TypingIndicator from './TypingIndicator';
import { FiChevronDown, FiMenu, FiRefreshCw, FiSettings, FiUser } from 'react-icons/fi';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
  onClearChat?: () => void;
  currentUserState?: string;
  currentStateConfidence?: number;
  error?: string | null;
  onClearError?: () => void;
  onSettingsClick?: () => void;
  onProfileClick?: () => void;
  onToggleSidebar?: () => void;
  userId?: string;
  chatTitle?: string;
  showSources?: boolean;
  showPath?: boolean;
  autoScroll?: boolean;
  compactMode?: boolean;
}

function formatState(state: string): string {
  if (!state) return '';
  return state.charAt(0).toUpperCase() + state.slice(1);
}

function formatConfidence(confidence?: number): string {
  if (confidence === undefined) return 'н/д';
  return `${Math.round(confidence * 100)}%`;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onClearChat,
  currentUserState,
  currentStateConfidence,
  error,
  onClearError,
  onSettingsClick,
  onProfileClick,
  onToggleSidebar,
  userId,
  chatTitle,
  showSources = true,
  showPath = true,
  autoScroll = true,
  compactMode = false,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isStateDetailsOpen, setIsStateDetailsOpen] = useState(false);

  useEffect(() => {
    if (!autoScroll) {
      return;
    }
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, autoScroll]);

  useEffect(() => {
    if (!currentUserState) {
      setIsStateDetailsOpen(false);
    }
  }, [currentUserState]);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-900">
      <div className="border-b border-slate-200 dark:border-slate-700 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            {onToggleSidebar && (
              <button
                onClick={onToggleSidebar}
                className="md:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 transition-colors"
                title="Открыть список чатов"
              >
                <FiMenu size={18} />
              </button>
            )}
            <div className="min-w-0">
              <h1 className="text-base font-semibold text-slate-900 dark:text-slate-100 truncate">
                {chatTitle || 'Новый чат'}
              </h1>
              {userId && (
                <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                  {userId}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1">
            {onClearChat && messages.length > 0 && (
              <button
                onClick={onClearChat}
                className="p-2 rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 transition-colors"
                title="Очистить чат"
              >
                <FiRefreshCw size={17} />
              </button>
            )}
            {onProfileClick && (
              <button
                onClick={onProfileClick}
                className="p-2 rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 transition-colors"
                title="Профиль"
              >
                <FiUser size={17} />
              </button>
            )}
            {onSettingsClick && (
              <button
                onClick={onSettingsClick}
                className="p-2 rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 transition-colors"
                title="Настройки"
              >
                <FiSettings size={17} />
              </button>
            )}
          </div>
        </div>

        {currentUserState && (
          <div className="mt-2 relative inline-block">
            <button
              onClick={() => setIsStateDetailsOpen((prev) => !prev)}
              className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
            >
              Состояние: {formatState(currentUserState)}
              <FiChevronDown size={12} />
            </button>

            {isStateDetailsOpen && (
              <div className="absolute left-0 mt-2 w-64 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-lg p-3 z-20">
                <p className="text-xs text-slate-500 dark:text-slate-400">Текущее состояние</p>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 mt-1">
                  {formatState(currentUserState)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Уверенность</p>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 mt-1">
                  {formatConfidence(currentStateConfidence)}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="bg-rose-50 dark:bg-rose-900/20 border-b border-rose-200 dark:border-rose-800 px-4 py-2 flex items-center justify-between gap-2">
          <span className="text-rose-700 dark:text-rose-300 text-sm truncate">{error}</span>
          {onClearError && (
            <button
              onClick={onClearError}
              className="text-rose-600 hover:text-rose-800 dark:text-rose-400 text-xs underline"
            >
              Закрыть
            </button>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
            <div className="text-center max-w-md">
              <p className="text-3xl mb-3">Начните диалог</p>
              <p className="text-sm">
                Задайте вопрос, и ассистент адаптирует ответ под ваш текущий контекст.
              </p>
            </div>
          </div>
        ) : (
          <>
            <MessageList
              messages={messages}
              showSources={showSources}
              showPath={showPath}
              compactMode={compactMode}
            />
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <InputBox onSendMessage={onSendMessage} isLoading={isLoading} />
    </div>
  );
};

export default ChatWindow;

