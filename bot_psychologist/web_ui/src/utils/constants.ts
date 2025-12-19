/**
 * Constants for Bot Psychologist Web UI
 * 
 * Centralized configuration and constant values used throughout the application.
 */

// ===== API CONFIGURATION =====

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1';

export const API_ENDPOINTS = {
  // Questions
  QUESTIONS_ADAPTIVE: '/questions/adaptive',
  QUESTIONS_BASIC: '/questions/basic',
  QUESTIONS_SAG_AWARE: '/questions/sag-aware',
  QUESTIONS_GRAPH: '/questions/graph-powered',
  
  // Users
  USER_HISTORY: (userId: string) => `/users/${userId}/history`,
  
  // Feedback
  FEEDBACK: '/feedback',
  
  // Stats & Health
  STATS: '/stats',
  HEALTH: '/health',
} as const;

export const API_TIMEOUT = 60000; // 60 seconds for LLM responses

// ===== DEFAULT VALUES =====

export const DEFAULT_USER_LEVEL = 'beginner' as const;
export const DEFAULT_THEME = 'system' as const;
export const DEFAULT_HISTORY_TURNS = 10;

export const DEFAULT_SETTINGS = {
  apiKey: '',
  userId: '',
  userLevel: DEFAULT_USER_LEVEL,
  theme: DEFAULT_THEME,
  showSources: true,
  showPath: true,
  autoScroll: true,
  soundEnabled: false,
} as const;

// ===== STORAGE KEYS =====

export const STORAGE_KEYS = {
  API_KEY: 'bot_api_key',
  USER_ID: 'bot_user_id',
  SETTINGS: 'bot_settings',
  THEME: 'bot_theme',
  MESSAGES: 'bot_messages',
} as const;

// ===== STATE COLORS MAPPING =====

/**
 * Colors for psychological/emotional states
 * Based on Sadhguru's framework for inner states
 */
export const STATE_COLORS: Record<string, string> = {
  // Positive states
  'joy': '#FFD700',        // Gold
  'peace': '#87CEEB',      // Sky blue
  'love': '#FF69B4',       // Pink
  'clarity': '#00CED1',    // Turquoise
  'gratitude': '#98FB98',  // Pale green
  'enthusiasm': '#FFA500', // Orange
  'compassion': '#DDA0DD', // Plum
  'awareness': '#E6E6FA',  // Lavender
  'equanimity': '#B0E0E6', // Powder blue
  'bliss': '#FFE4B5',      // Moccasin
  
  // Challenging states
  'anxiety': '#FF6B6B',    // Coral red
  'stress': '#FF4500',     // Orange red
  'confusion': '#808080',  // Gray
  'anger': '#DC143C',      // Crimson
  'fear': '#4B0082',       // Indigo
  'sadness': '#6495ED',    // Cornflower blue
  'frustration': '#CD853F', // Peru
  'restlessness': '#DAA520', // Goldenrod
  
  // Neutral/Transition states
  'neutral': '#A9A9A9',    // Dark gray
  'seeking': '#7B68EE',    // Medium slate blue
  'curious': '#40E0D0',    // Turquoise
  'contemplative': '#708090', // Slate gray
  
  // Default
  'default': '#6B7280',    // Gray-500
} as const;

// ===== STATE EMOJIS MAPPING =====

/**
 * Emojis for psychological/emotional states visualization
 */
export const STATE_EMOJIS: Record<string, string> = {
  // Positive states
  'joy': '😊',
  'peace': '🕊️',
  'love': '💝',
  'clarity': '💎',
  'gratitude': '🙏',
  'enthusiasm': '✨',
  'compassion': '💗',
  'awareness': '👁️',
  'equanimity': '⚖️',
  'bliss': '🌟',
  
  // Challenging states
  'anxiety': '😰',
  'stress': '😫',
  'confusion': '😕',
  'anger': '😠',
  'fear': '😨',
  'sadness': '😢',
  'frustration': '😤',
  'restlessness': '🌀',
  
  // Neutral/Transition states
  'neutral': '😐',
  'seeking': '🔍',
  'curious': '🤔',
  'contemplative': '🧘',
  
  // Default
  'default': '💭',
} as const;

// ===== USER LEVELS =====

export const USER_LEVELS = ['beginner', 'intermediate', 'advanced'] as const;

export const USER_LEVEL_LABELS: Record<string, string> = {
  'beginner': 'Начинающий',
  'intermediate': 'Практикующий',
  'advanced': 'Продвинутый',
} as const;

export const USER_LEVEL_DESCRIPTIONS: Record<string, string> = {
  'beginner': 'Только начинаю изучение',
  'intermediate': 'Имею базовый опыт практики',
  'advanced': 'Глубокое понимание и регулярная практика',
} as const;

// ===== FEEDBACK =====

export const FEEDBACK_TYPES = ['positive', 'negative', 'neutral'] as const;

export const FEEDBACK_LABELS: Record<string, string> = {
  'positive': 'Полезно',
  'negative': 'Не полезно',
  'neutral': 'Нейтрально',
} as const;

export const FEEDBACK_EMOJIS: Record<string, string> = {
  'positive': '👍',
  'negative': '👎',
  'neutral': '😐',
} as const;

// ===== THEME =====

export const THEMES = ['light', 'dark', 'system'] as const;

export const THEME_LABELS: Record<string, string> = {
  'light': 'Светлая',
  'dark': 'Тёмная',
  'system': 'Системная',
} as const;

// ===== ANIMATION TIMINGS =====

export const ANIMATION = {
  DURATION_FAST: 150,    // ms
  DURATION_NORMAL: 300,  // ms
  DURATION_SLOW: 500,    // ms
  TYPING_DELAY: 50,      // ms per character
} as const;

// ===== LIMITS =====

export const LIMITS = {
  MAX_MESSAGE_LENGTH: 4096,
  MAX_SOURCES_DISPLAY: 5,
  MAX_CONCEPTS_DISPLAY: 10,
  MAX_PATH_STEPS_DISPLAY: 5,
  MIN_RATING: 1,
  MAX_RATING: 5,
} as const;

// ===== REGEX PATTERNS =====

export const PATTERNS = {
  API_KEY: /^[a-zA-Z0-9_-]{20,}$/,
  USER_ID: /^[a-zA-Z0-9_-]{8,64}$/,
  UUID: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
  TIMECODE: /^(\d{1,2}:)?[0-5]?\d:[0-5]\d$/,
} as const;
