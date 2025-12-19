/**
 * SettingsPage Component
 * 
 * Settings page for API key, user ID, and preferences.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  FiKey, 
  FiUser, 
  FiLayers, 
  FiCheck, 
  FiAlertCircle,
  FiArrowLeft,
  FiSun,
  FiMoon,
  FiEye,
  FiEyeOff
} from 'react-icons/fi';
import clsx from 'clsx';
import { apiService } from '../services/api.service';
import { storageService } from '../services/storage.service';
import { useTheme } from '../hooks/useTheme';
import type { UserLevel } from '../types';

type ValidationStatus = 'idle' | 'validating' | 'success' | 'error';

const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  // Get return URL and message from navigation state
  const returnUrl = (location.state as any)?.returnUrl || '/chat';
  const navMessage = (location.state as any)?.message;

  // Form state
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [userId, setUserId] = useState('');
  const [userLevel, setUserLevel] = useState<UserLevel>('beginner');
  const [showSources, setShowSources] = useState(true);
  const [showPath, setShowPath] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);

  // Validation state
  const [validationStatus, setValidationStatus] = useState<ValidationStatus>('idle');
  const [validationMessage, setValidationMessage] = useState('');

  // Load saved settings on mount
  useEffect(() => {
    const savedKey = storageService.getApiKey();
    const savedUserId = storageService.getUserId();
    const savedLevel = storageService.getUserLevel();
    const savedSettings = storageService.getSettings();

    if (savedKey) setApiKey(savedKey);
    if (savedUserId) setUserId(savedUserId);
    if (savedLevel) setUserLevel(savedLevel);
    if (savedSettings) {
      setShowSources(savedSettings.showSources);
      setShowPath(savedSettings.showPath);
      setAutoScroll(savedSettings.autoScroll);
    }
  }, []);

  // Generate random user ID
  const generateUserId = () => {
    const id = `user_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    setUserId(id);
  };

  // Validate API key and save settings
  const handleSave = async () => {
    if (!apiKey.trim()) {
      setValidationStatus('error');
      setValidationMessage('API ключ обязателен');
      return;
    }

    setValidationStatus('validating');
    setValidationMessage('Проверка подключения...');

    try {
      // Set API key temporarily
      apiService.setAPIKey(apiKey);

      // Test connection with health check
      await apiService.healthCheck();

      // Save all settings
      storageService.setApiKey(apiKey);
      
      const finalUserId = userId.trim() || `user_${Date.now()}`;
      storageService.setUserId(finalUserId);
      storageService.setUserLevel(userLevel);
      storageService.setSettings({
        apiKey,
        userId: finalUserId,
        userLevel,
        theme,
        showSources,
        showPath,
        autoScroll,
      });

      setValidationStatus('success');
      setValidationMessage('✅ Настройки сохранены! Переход в чат...');

      // Navigate to chat after delay
      setTimeout(() => {
        navigate(returnUrl);
      }, 1500);

    } catch (error) {
      setValidationStatus('error');
      setValidationMessage(
        error instanceof Error 
          ? `❌ ${error.message}` 
          : '❌ Не удалось подключиться к API'
      );
      // Clear invalid API key
      apiService.setAPIKey('');
    }
  };

  // Handle back navigation
  const handleBack = () => {
    navigate(-1);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-900 dark:to-purple-900/20">
      <div className="max-w-lg mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={handleBack}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <FiArrowLeft className="w-5 h-5" />
          </button>
          
          <button
            onClick={toggleTheme}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            {theme === 'dark' ? <FiSun className="w-5 h-5" /> : <FiMoon className="w-5 h-5" />}
          </button>
        </div>

        {/* Main Card */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-8 text-white text-center">
            <h1 className="text-3xl font-bold mb-2">Bot Psychologist</h1>
            <p className="text-purple-200">Настройки подключения</p>
          </div>

          {/* Navigation message */}
          {navMessage && (
            <div className="px-6 pt-4">
              <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg text-sm text-yellow-800 dark:text-yellow-200">
                {navMessage}
              </div>
            </div>
          )}

          {/* Form */}
          <div className="p-6 space-y-6">
            {/* API Key */}
            <div>
              <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                <FiKey className="w-4 h-4" />
                API Ключ <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Введите API ключ..."
                  className={clsx(
                    'w-full px-4 py-3 pr-12 rounded-xl border',
                    'bg-gray-50 dark:bg-gray-700',
                    'text-gray-900 dark:text-white',
                    'placeholder-gray-400 dark:placeholder-gray-500',
                    'focus:outline-none focus:ring-2 focus:ring-purple-500',
                    validationStatus === 'error' && 'border-red-500',
                    validationStatus === 'success' && 'border-green-500',
                    validationStatus === 'idle' && 'border-gray-300 dark:border-gray-600'
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showApiKey ? <FiEyeOff className="w-5 h-5" /> : <FiEye className="w-5 h-5" />}
                </button>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Получить ключ можно у администратора API
              </p>
            </div>

            {/* User ID */}
            <div>
              <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                <FiUser className="w-4 h-4" />
                ID пользователя
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="user_123 (необязательно)"
                  className={clsx(
                    'flex-1 px-4 py-3 rounded-xl border',
                    'bg-gray-50 dark:bg-gray-700',
                    'border-gray-300 dark:border-gray-600',
                    'text-gray-900 dark:text-white',
                    'placeholder-gray-400 dark:placeholder-gray-500',
                    'focus:outline-none focus:ring-2 focus:ring-purple-500'
                  )}
                />
                <button
                  type="button"
                  onClick={generateUserId}
                  className={clsx(
                    'px-4 py-3 rounded-xl',
                    'bg-gray-200 dark:bg-gray-600',
                    'text-gray-700 dark:text-gray-200',
                    'hover:bg-gray-300 dark:hover:bg-gray-500',
                    'transition-colors'
                  )}
                >
                  Создать
                </button>
              </div>
            </div>

            {/* User Level */}
            <div>
              <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                <FiLayers className="w-4 h-4" />
                Уровень
              </label>
              <select
                value={userLevel}
                onChange={(e) => setUserLevel(e.target.value as UserLevel)}
                className={clsx(
                  'w-full px-4 py-3 rounded-xl border',
                  'bg-gray-50 dark:bg-gray-700',
                  'border-gray-300 dark:border-gray-600',
                  'text-gray-900 dark:text-white',
                  'focus:outline-none focus:ring-2 focus:ring-purple-500'
                )}
              >
                <option value="beginner">🌱 Начинающий — базовые объяснения</option>
                <option value="intermediate">🌿 Средний — более глубокие темы</option>
                <option value="advanced">🌳 Продвинутый — сложные концепции</option>
              </select>
            </div>

            {/* Display Options */}
            <div className="space-y-3">
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                Отображение
              </p>
              
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Показывать источники
                </span>
                <input
                  type="checkbox"
                  checked={showSources}
                  onChange={(e) => setShowSources(e.target.checked)}
                  className="w-5 h-5 rounded text-purple-600 focus:ring-purple-500"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Показывать путь развития
                </span>
                <input
                  type="checkbox"
                  checked={showPath}
                  onChange={(e) => setShowPath(e.target.checked)}
                  className="w-5 h-5 rounded text-purple-600 focus:ring-purple-500"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Автопрокрутка чата
                </span>
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  className="w-5 h-5 rounded text-purple-600 focus:ring-purple-500"
                />
              </label>
            </div>

            {/* Validation Message */}
            {validationMessage && (
              <div className={clsx(
                'flex items-center gap-2 p-4 rounded-xl text-sm',
                validationStatus === 'success' && 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300',
                validationStatus === 'error' && 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300',
                validationStatus === 'validating' && 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
              )}>
                {validationStatus === 'success' && <FiCheck className="w-5 h-5" />}
                {validationStatus === 'error' && <FiAlertCircle className="w-5 h-5" />}
                {validationStatus === 'validating' && (
                  <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                )}
                {validationMessage}
              </div>
            )}

            {/* Submit Button */}
            <button
              onClick={handleSave}
              disabled={!apiKey.trim() || validationStatus === 'validating'}
              className={clsx(
                'w-full py-4 rounded-xl font-semibold text-lg',
                'bg-gradient-to-r from-purple-600 to-indigo-600',
                'text-white',
                'hover:from-purple-700 hover:to-indigo-700',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-all duration-200'
              )}
            >
              {validationStatus === 'validating' ? 'Проверка...' : 'Сохранить и начать'}
            </button>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-gray-400 mt-6">
          Bot Psychologist v0.6.0 • API URL: {import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1'}
        </p>
      </div>
    </div>
  );
};

export default SettingsPage;
