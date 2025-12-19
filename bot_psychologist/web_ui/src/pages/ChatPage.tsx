/**
 * ChatPage Component
 * 
 * Main chat interface page with adaptive QA functionality.
 */

import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ChatWindow } from '../components/chat';
import { useChat } from '../hooks/useChat';
import { storageService } from '../services/storage.service';
import type { UserLevel } from '../types';

const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Get user settings from URL params or storage
  const urlUserId = searchParams.get('user_id');
  const urlLevel = searchParams.get('level') as UserLevel | null;
  
  const userId = urlUserId || storageService.getUserId() || `user_${Date.now()}`;
  const userLevel: UserLevel = urlLevel || storageService.getUserLevel() || 'beginner';
  const settings = storageService.getSettings();

  // Chat hook
  const {
    messages,
    isLoading,
    error,
    currentUserState,
    sendQuestion,
    clearChat,
    clearError,
  } = useChat({
    userId,
    userLevel,
    includePath: settings.showPath,
    includeFeedback: true,
  });

  // Check API key on mount
  useEffect(() => {
    if (!storageService.hasApiKey()) {
      navigate('/settings', { 
        state: { 
          returnUrl: `/chat?user_id=${userId}&level=${userLevel}`,
          message: 'Для использования чата необходимо настроить API ключ'
        }
      });
    }
  }, [navigate, userId, userLevel]);

  // Save user ID if it was generated
  useEffect(() => {
    if (!storageService.getUserId()) {
      storageService.setUserId(userId);
    }
  }, [userId]);

  // Handle new message send
  const handleSendMessage = (message: string) => {
    sendQuestion(message);
    clearError();
  };

  // Handle clear chat
  const handleClearChat = () => {
    clearChat();
  };

  // Handle settings navigation
  const handleSettingsClick = () => {
    navigate('/settings');
  };

  // Handle profile navigation
  const handleProfileClick = () => {
    navigate(`/profile?user_id=${userId}`);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        error={error}
        onSendMessage={handleSendMessage}
        onClearChat={handleClearChat}
        onSettingsClick={handleSettingsClick}
        onProfileClick={handleProfileClick}
        currentUserState={currentUserState}
        userId={userId}
        userLevel={userLevel}
      />
    </div>
  );
};

export default ChatPage;
