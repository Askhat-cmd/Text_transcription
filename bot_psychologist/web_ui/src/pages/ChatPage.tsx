/**
 * ChatPage Component
 *
 * Chat interface with server-side multi-chat sidebar and grouped history.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  FiCheck,
  FiEye,
  FiEyeOff,
  FiKey,
  FiMessageSquare,
  FiPlus,
  FiTrash2,
  FiUser,
  FiX,
} from 'react-icons/fi';
import clsx from 'clsx';
import { ChatWindow } from '../components/chat';
import { useChat } from '../hooks/useChat';
import { formatterService } from '../services/formatter.service';
import { storageService } from '../services/storage.service';
import { apiService } from '../services/api.service';
import type { ChatSessionInfo, ConversationTurn, Message, UserSettings } from '../types';

type ValidationStatus = 'idle' | 'validating' | 'success' | 'error';

type SessionGroupKey = 'today' | 'yesterday' | 'week' | 'older';

interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  turnsCount: number;
  preview: string;
}

interface SessionGroup {
  key: SessionGroupKey;
  title: string;
  sessions: ChatSession[];
}

function buildChatTitle(messages: Message[]): string {
  const firstUserMessage = messages.find((message) => message.role === 'user');
  if (!firstUserMessage) {
    return 'New chat';
  }

  const compact = firstUserMessage.content.replace(/\s+/g, ' ').trim();
  if (compact.length <= 42) {
    return compact;
  }

  return `${compact.slice(0, 42)}...`;
}

function buildChatPreview(messages: Message[]): string {
  if (messages.length === 0) {
    return 'No messages yet';
  }

  const lastMessage = messages[messages.length - 1];
  const compact = lastMessage.content.replace(/\s+/g, ' ').trim();
  if (compact.length <= 44) {
    return compact;
  }

  return `${compact.slice(0, 44)}...`;
}

function formatSessionTime(isoDate: string): string {
  try {
    return formatterService.formatRelativeTime(new Date(isoDate));
  } catch {
    return '';
  }
}

function mapServerSession(item: ChatSessionInfo): ChatSession {
  return {
    id: item.session_id,
    title: item.title || 'New chat',
    createdAt: item.created_at,
    updatedAt: item.last_active || item.created_at,
    turnsCount: item.turns_count || 0,
    preview: item.last_user_input || item.last_bot_response || 'No messages yet',
  };
}

function sortSessionsByUpdatedAt(sessions: ChatSession[]): ChatSession[] {
  return [...sessions].sort((left, right) => (
    new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime()
  ));
}

function historyToMessages(sessionId: string, turns: ConversationTurn[]): Message[] {
  const mapped: Message[] = [];

  turns.forEach((turn, index) => {
    const turnTime = new Date(turn.timestamp);

    mapped.push({
      id: `${sessionId}-u-${index}`,
      role: 'user',
      content: turn.user_input,
      timestamp: turnTime,
    });

    mapped.push({
      id: `${sessionId}-b-${index}`,
      role: 'bot',
      content: turn.bot_response,
      timestamp: turnTime,
      state: turn.user_state,
      concepts: turn.concepts,
    });
  });

  return mapped;
}

function getSessionGroupKey(isoDate: string): SessionGroupKey {
  const now = new Date();
  const date = new Date(isoDate);

  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);
  const sevenDaysAgo = new Date(startOfToday);
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

  if (date >= startOfToday) {
    return 'today';
  }

  if (date >= startOfYesterday) {
    return 'yesterday';
  }

  if (date >= sevenDaysAgo) {
    return 'week';
  }

  return 'older';
}

const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const urlUserId = searchParams.get('user_id');
  const shouldOpenSettings = searchParams.get('open_settings') === '1';
  const settingsNoticeFromQuery = searchParams.get('settings_notice');
  const userId = urlUserId || storageService.getUserId() || `user_${Date.now()}`;

  const [chatSettings, setChatSettings] = useState<UserSettings>(() => storageService.getSettings());

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState('');
  const [isSessionsLoading, setIsSessionsLoading] = useState(true);
  const [sidebarError, setSidebarError] = useState<string | null>(null);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsNotice, setSettingsNotice] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [settingsUserId, setSettingsUserId] = useState(userId);
  const [showSources, setShowSources] = useState(true);
  const [showPath, setShowPath] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const [validationStatus, setValidationStatus] = useState<ValidationStatus>('idle');
  const [validationMessage, setValidationMessage] = useState('');

  const {
    messages,
    isLoading,
    error,
    currentUserState,
    currentStateConfidence,
    sendQuestion,
    replaceMessages,
    clearError,
  } = useChat({
    userId,
    includePath: chatSettings.showPath,
    includeFeedback: true,
    sessionId: activeChatId || undefined,
  });

  const groupedSessions = useMemo<SessionGroup[]>(() => {
    const groups: Record<SessionGroupKey, ChatSession[]> = {
      today: [],
      yesterday: [],
      week: [],
      older: [],
    };

    sessions.forEach((session) => {
      groups[getSessionGroupKey(session.updatedAt)].push(session);
    });

    const ordered: Array<[SessionGroupKey, string]> = [
      ['today', 'Сегодня'],
      ['yesterday', 'Вчера'],
      ['week', 'Последние 7 дней'],
      ['older', 'Старые'],
    ];

    return ordered
      .map(([key, title]) => ({ key, title, sessions: groups[key] }))
      .filter((group) => group.sessions.length > 0);
  }, [sessions]);

  const loadActiveChatHistory = useCallback(async (sessionId: string) => {
    try {
      const history = await apiService.getUserHistory(sessionId, 100);
      const loadedMessages = historyToMessages(sessionId, history.turns);
      replaceMessages(loadedMessages);
      clearError();
    } catch (historyError) {
      replaceMessages([]);
      setSidebarError(historyError instanceof Error ? historyError.message : 'Failed to load chat history');
    }
  }, [replaceMessages, clearError]);

  const loadSessions = useCallback(async (preferredSessionId?: string) => {
    if (!apiService.hasAPIKey()) {
      setIsSessionsLoading(false);
      setSessions([]);
      return;
    }

    setIsSessionsLoading(true);
    setSidebarError(null);

    try {
      const response = await apiService.getUserSessions(userId, 200);
      let mapped = response.sessions.map(mapServerSession);

      if (mapped.length === 0) {
        const created = await apiService.createUserSession(userId);
        mapped = [mapServerSession(created)];
      }

      const sorted = sortSessionsByUpdatedAt(mapped);
      setSessions(sorted);

      setActiveChatId((currentActiveId) => {
        if (preferredSessionId && sorted.some((session) => session.id === preferredSessionId)) {
          return preferredSessionId;
        }
        if (currentActiveId && sorted.some((session) => session.id === currentActiveId)) {
          return currentActiveId;
        }
        return sorted[0].id;
      });
    } catch (sessionsError) {
      setSidebarError(sessionsError instanceof Error ? sessionsError.message : 'Failed to load sessions');
    } finally {
      setIsSessionsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    const stored = storageService.getSettings();

    setChatSettings(stored);
    setApiKey(stored.apiKey || storageService.getApiKey());
    setSettingsUserId(stored.userId || userId);
    setShowSources(stored.showSources);
    setShowPath(stored.showPath);
    setAutoScroll(stored.autoScroll);
  }, [userId]);

  useEffect(() => {
    if (!storageService.getUserId()) {
      storageService.setUserId(userId);
    }
  }, [userId]);

  useEffect(() => {
    if (!apiService.hasAPIKey()) {
      setSettingsNotice('API key is required before using chat.');
      setIsSettingsOpen(true);
      setIsSessionsLoading(false);
      return;
    }

    void loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    if (shouldOpenSettings) {
      setIsSettingsOpen(true);
      if (settingsNoticeFromQuery) {
        setSettingsNotice(settingsNoticeFromQuery);
      }

      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('open_settings');
      nextParams.delete('settings_notice');
      setSearchParams(nextParams, { replace: true });
    }
  }, [shouldOpenSettings, settingsNoticeFromQuery, searchParams, setSearchParams]);

  useEffect(() => {
    if (!isSettingsOpen) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsSettingsOpen(false);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isSettingsOpen]);

  useEffect(() => {
    if (!activeChatId) {
      replaceMessages([]);
      return;
    }

    void loadActiveChatHistory(activeChatId);
  }, [activeChatId, loadActiveChatHistory, replaceMessages]);

  useEffect(() => {
    if (!activeChatId) return;

    setSessions((previous) => {
      const next = previous.map((session) => {
        if (session.id !== activeChatId) {
          return session;
        }

        const lastTimestamp = messages.length > 0
          ? messages[messages.length - 1].timestamp.toISOString()
          : session.updatedAt;

        return {
          ...session,
          title: buildChatTitle(messages),
          preview: buildChatPreview(messages),
          updatedAt: lastTimestamp,
          turnsCount: messages.filter((message) => message.role === 'user').length,
        };
      });

      return sortSessionsByUpdatedAt(next);
    });
  }, [messages, activeChatId]);

  const handleSendMessage = (message: string) => {
    if (!activeChatId) return;
    void sendQuestion(message);
    clearError();
  };

  const handleNewChat = async () => {
    try {
      const created = await apiService.createUserSession(userId);
      const mapped = mapServerSession(created);

      setSessions((prev) => sortSessionsByUpdatedAt([mapped, ...prev]));
      setActiveChatId(mapped.id);
      replaceMessages([]);
      clearError();
      setSidebarError(null);
      setIsMobileSidebarOpen(false);
    } catch (createError) {
      setSidebarError(createError instanceof Error ? createError.message : 'Failed to create chat');
    }
  };

  const handleSelectChat = (chatId: string) => {
    setActiveChatId(chatId);
    setIsMobileSidebarOpen(false);
    clearError();
  };

  const handleDeleteChat = async (chatId: string) => {
    try {
      await apiService.deleteUserSession(userId, chatId);

      const remaining = sessions.filter((session) => session.id !== chatId);

      if (remaining.length === 0) {
        const created = await apiService.createUserSession(userId);
        const mapped = mapServerSession(created);
        setSessions([mapped]);
        setActiveChatId(mapped.id);
        replaceMessages([]);
        return;
      }

      setSessions(remaining);
      if (chatId === activeChatId) {
        setActiveChatId(remaining[0].id);
      }
    } catch (deleteError) {
      setSidebarError(deleteError instanceof Error ? deleteError.message : 'Failed to delete chat');
    }
  };

  const handleClearChat = async () => {
    if (!activeChatId) return;

    try {
      await apiService.deleteUserSession(userId, activeChatId);
      const created = await apiService.createUserSession(userId);
      const mapped = mapServerSession(created);

      setSessions((prev) => {
        const remaining = prev.filter((session) => session.id !== activeChatId);
        return sortSessionsByUpdatedAt([mapped, ...remaining]);
      });
      setActiveChatId(mapped.id);
      replaceMessages([]);
      clearError();
    } catch (clearChatError) {
      setSidebarError(clearChatError instanceof Error ? clearChatError.message : 'Failed to clear chat');
    }
  };

  const handleSettingsClick = () => {
    setSettingsNotice(null);
    setIsSettingsOpen(true);
  };

  const handleProfileClick = () => {
    navigate(`/profile?user_id=${userId}`);
  };

  const generateSettingsUserId = () => {
    setSettingsUserId(`user_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`);
  };

  const handleSaveSettings = async () => {
    if (!apiKey.trim()) {
      setValidationStatus('error');
      setValidationMessage('API key is required');
      return;
    }

    setValidationStatus('validating');
    setValidationMessage('Checking API connection...');

    try {
      apiService.setAPIKey(apiKey.trim());
      await apiService.healthCheck();

      const nextUserId = settingsUserId.trim() || userId;
      const updatedSettings: UserSettings = {
        ...chatSettings,
        apiKey: apiKey.trim(),
        userId: nextUserId,
        showSources,
        showPath,
        autoScroll,
      };

      storageService.setApiKey(updatedSettings.apiKey);
      storageService.setUserId(updatedSettings.userId);
      storageService.setSettings(updatedSettings);
      setChatSettings(updatedSettings);

      setValidationStatus('success');
      setValidationMessage('Settings saved');
      setIsSettingsOpen(false);
      setSettingsNotice(null);

      if (nextUserId !== userId) {
        navigate(`/chat?user_id=${encodeURIComponent(nextUserId)}`, { replace: true });
        return;
      }

      await loadSessions();
    } catch (settingsError) {
      setValidationStatus('error');
      setValidationMessage(settingsError instanceof Error ? settingsError.message : 'Failed to connect to API');
      apiService.clearAPIKey();
    }
  };

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeChatId),
    [sessions, activeChatId]
  );

  const renderSidebar = (mobile: boolean) => (
    <aside className="w-72 h-full bg-slate-900 text-slate-100 flex flex-col border-r border-slate-700">
      <div className="p-3 border-b border-slate-700">
        <button
          onClick={() => void handleNewChat()}
          className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-slate-600 px-3 py-2 text-sm font-medium hover:bg-slate-800 transition-colors"
        >
          <FiPlus size={16} />
          New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-4">
        {isSessionsLoading && (
          <p className="px-2 text-xs text-slate-400">Loading sessions...</p>
        )}

        {!isSessionsLoading && groupedSessions.length === 0 && (
          <p className="px-2 text-xs text-slate-400">No chats yet</p>
        )}

        {groupedSessions.map((group) => (
          <div key={group.key} className="space-y-1">
            <p className="px-2 text-[11px] uppercase tracking-wide text-slate-500">{group.title}</p>

            {group.sessions.map((session) => {
              const isActive = session.id === activeChatId;

              return (
                <button
                  key={session.id}
                  onClick={() => handleSelectChat(session.id)}
                  className={`group w-full text-left rounded-lg px-3 py-2 transition-colors ${
                    isActive
                      ? 'bg-slate-700 text-white'
                      : 'hover:bg-slate-800 text-slate-200'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <FiMessageSquare size={14} className="shrink-0 mt-0.5" />
                        <p className="truncate text-sm font-medium">{session.title}</p>
                      </div>
                      <p className="mt-1 text-xs text-slate-400 truncate">{session.preview}</p>
                      <p className="mt-1 text-[11px] text-slate-500">{formatSessionTime(session.updatedAt)}</p>
                    </div>

                    <span
                      onClick={(event) => {
                        event.stopPropagation();
                        void handleDeleteChat(session.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-600 transition-all"
                    >
                      <FiTrash2 size={13} />
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-slate-700 text-xs text-slate-400 min-h-10">
        {sidebarError && <p className="mb-2 text-rose-300">{sidebarError}</p>}
        {mobile && (
          <button
            onClick={() => setIsMobileSidebarOpen(false)}
            className="inline-flex items-center gap-1 hover:text-slate-200"
          >
            <FiX size={13} />
            Close
          </button>
        )}
      </div>
    </aside>
  );

  return (
    <div className="h-screen bg-slate-100 dark:bg-slate-950">
      <div className="h-full flex">
        <div className="hidden md:block h-full">{renderSidebar(false)}</div>

        {isMobileSidebarOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setIsMobileSidebarOpen(false)}
            />
            <div className="relative z-10 h-full">{renderSidebar(true)}</div>
          </div>
        )}

        <main className="flex-1 min-w-0">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            error={error}
            onSendMessage={handleSendMessage}
            onClearChat={() => { void handleClearChat(); }}
            onSettingsClick={handleSettingsClick}
            onProfileClick={handleProfileClick}
            onClearError={clearError}
            onToggleSidebar={() => setIsMobileSidebarOpen(true)}
            currentUserState={currentUserState}
            currentStateConfidence={currentStateConfidence}
            userId={userId}
            chatTitle={activeSession?.title || 'New chat'}
            showSources={chatSettings.showSources}
            showPath={chatSettings.showPath}
            autoScroll={chatSettings.autoScroll}
          />
        </main>
      </div>

      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setIsSettingsOpen(false)} />

          <div className="relative z-10 w-full max-w-lg rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Settings</h2>
              <button
                onClick={() => setIsSettingsOpen(false)}
                className="p-1 rounded text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <FiX size={16} />
              </button>
            </div>

            <div className="p-5 space-y-5">
              {settingsNotice && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
                  {settingsNotice}
                </div>
              )}

              <div>
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                  <FiKey className="w-4 h-4" />
                  API key
                </label>
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={(event) => setApiKey(event.target.value)}
                    placeholder="Enter API key"
                    className="w-full px-4 py-3 pr-12 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey((prev) => !prev)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showApiKey ? <FiEyeOff className="w-5 h-5" /> : <FiEye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                  <FiUser className="w-4 h-4" />
                  User ID
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={settingsUserId}
                    onChange={(event) => setSettingsUserId(event.target.value)}
                    className="flex-1 px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                  />
                  <button
                    type="button"
                    onClick={generateSettingsUserId}
                    className="px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                  >
                    Generate
                  </button>
                </div>
              </div>

              <div className="space-y-3 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Interface options</p>

                <label className="flex items-center justify-between cursor-pointer text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Show sources</span>
                  <input
                    type="checkbox"
                    checked={showSources}
                    onChange={(event) => setShowSources(event.target.checked)}
                    className="w-4 h-4"
                  />
                </label>

                <label className="flex items-center justify-between cursor-pointer text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Show path recommendations</span>
                  <input
                    type="checkbox"
                    checked={showPath}
                    onChange={(event) => setShowPath(event.target.checked)}
                    className="w-4 h-4"
                  />
                </label>

                <label className="flex items-center justify-between cursor-pointer text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Auto scroll</span>
                  <input
                    type="checkbox"
                    checked={autoScroll}
                    onChange={(event) => setAutoScroll(event.target.checked)}
                    className="w-4 h-4"
                  />
                </label>
              </div>

              {validationMessage && (
                <div className={clsx(
                  'flex items-center gap-2 rounded-xl px-3 py-2 text-sm',
                  validationStatus === 'success' && 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300',
                  validationStatus === 'error' && 'bg-rose-50 text-rose-700 dark:bg-rose-900/20 dark:text-rose-300',
                  validationStatus === 'validating' && 'bg-sky-50 text-sky-700 dark:bg-sky-900/20 dark:text-sky-300'
                )}>
                  {validationStatus === 'success' && <FiCheck className="w-4 h-4" />}
                  {validationMessage}
                </div>
              )}

              <button
                onClick={() => void handleSaveSettings()}
                className="w-full py-3 rounded-xl font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
              >
                {validationStatus === 'validating' ? 'Checking...' : 'Save settings'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatPage;

