/**
 * Storage Service for Bot Psychologist Web UI
 *
 * Type-safe wrapper around localStorage with fallback support.
 */

import type { UserSettings } from '../types';

const LEGACY_USER_LEVEL_KEY = 'bot_user_level';

// Storage keys
const STORAGE_KEYS = {
  API_KEY: 'bot_api_key',
  USER_ID: 'bot_user_id',
  THEME: 'bot_theme',
  SETTINGS: 'bot_settings',
  CHAT_HISTORY: 'bot_chat_history',
} as const;

type StorageKey = typeof STORAGE_KEYS[keyof typeof STORAGE_KEYS];

class StorageService {
  private isAvailable: boolean;

  constructor() {
    this.isAvailable = this.checkAvailability();
  }

  private checkAvailability(): boolean {
    try {
      const testKey = '__storage_test__';
      localStorage.setItem(testKey, testKey);
      localStorage.removeItem(testKey);
      return true;
    } catch {
      console.warn('localStorage is not available');
      return false;
    }
  }

  // === GENERIC METHODS ===

  get<T>(key: StorageKey, defaultValue: T): T {
    if (!this.isAvailable) return defaultValue;

    try {
      const item = localStorage.getItem(key);
      if (item === null) return defaultValue;
      return JSON.parse(item) as T;
    } catch {
      return defaultValue;
    }
  }

  set<T>(key: StorageKey, value: T): boolean {
    if (!this.isAvailable) return false;

    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      console.error('Failed to save to localStorage:', error);
      return false;
    }
  }

  remove(key: StorageKey): boolean {
    if (!this.isAvailable) return false;

    try {
      localStorage.removeItem(key);
      return true;
    } catch {
      return false;
    }
  }

  clear(): boolean {
    if (!this.isAvailable) return false;

    try {
      Object.values(STORAGE_KEYS).forEach((key) => {
        localStorage.removeItem(key);
      });

      // Cleanup key from previous versions.
      localStorage.removeItem(LEGACY_USER_LEVEL_KEY);
      return true;
    } catch {
      return false;
    }
  }

  // === TYPED METHODS ===

  // API Key
  getApiKey(): string {
    if (!this.isAvailable) return '';
    return localStorage.getItem(STORAGE_KEYS.API_KEY) || '';
  }

  setApiKey(key: string): boolean {
    if (!this.isAvailable) return false;
    try {
      localStorage.setItem(STORAGE_KEYS.API_KEY, key);
      return true;
    } catch {
      return false;
    }
  }

  clearApiKey(): boolean {
    return this.remove(STORAGE_KEYS.API_KEY);
  }

  hasApiKey(): boolean {
    return Boolean(this.getApiKey());
  }

  // User ID
  getUserId(): string {
    if (!this.isAvailable) return this.generateUserId();

    let userId = localStorage.getItem(STORAGE_KEYS.USER_ID);
    if (!userId) {
      userId = this.generateUserId();
      localStorage.setItem(STORAGE_KEYS.USER_ID, userId);
    }
    return userId;
  }

  setUserId(id: string): boolean {
    if (!this.isAvailable) return false;
    try {
      localStorage.setItem(STORAGE_KEYS.USER_ID, id);
      return true;
    } catch {
      return false;
    }
  }

  private generateUserId(): string {
    return `user_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  }

  // Theme
  getTheme(): 'light' | 'dark' | 'system' {
    if (!this.isAvailable) return 'system';
    const theme = localStorage.getItem(STORAGE_KEYS.THEME);
    if (theme === 'light' || theme === 'dark') {
      return theme;
    }
    return 'system';
  }

  setTheme(theme: 'light' | 'dark' | 'system'): boolean {
    if (!this.isAvailable) return false;
    try {
      localStorage.setItem(STORAGE_KEYS.THEME, theme);
      return true;
    } catch {
      return false;
    }
  }

  // Full Settings
  getSettings(): UserSettings {
    const defaultSettings: UserSettings = {
      apiKey: this.getApiKey(),
      userId: this.getUserId(),
      theme: this.getTheme(),
      showSources: true,
      showPath: true,
      autoScroll: true,
      soundEnabled: false,
    };

    return this.get<UserSettings>(STORAGE_KEYS.SETTINGS, defaultSettings);
  }

  setSettings(settings: Partial<UserSettings>): boolean {
    const current = this.getSettings();
    const updated = { ...current, ...settings };

    if (settings.apiKey !== undefined) this.setApiKey(settings.apiKey);
    if (settings.userId !== undefined) this.setUserId(settings.userId);
    if (settings.theme !== undefined) this.setTheme(settings.theme);

    return this.set(STORAGE_KEYS.SETTINGS, updated);
  }
}

// Singleton instance
export const storageService = new StorageService();
