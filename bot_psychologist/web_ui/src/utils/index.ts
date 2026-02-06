/**
 * Utils Index - Re-export all utilities from a single entry point
 */

// Constants
export {
  // API Configuration
  API_BASE_URL,
  API_ENDPOINTS,
  API_TIMEOUT,
  
  // Default Values
  DEFAULT_USER_LEVEL,
  DEFAULT_THEME,
  DEFAULT_HISTORY_TURNS,
  DEFAULT_SETTINGS,
  
  // Storage Keys
  STORAGE_KEYS,
  
  // State Mappings
  STATE_COLORS,
  STATE_EMOJIS,
  
  // User Levels
  USER_LEVELS,
  USER_LEVEL_LABELS,
  USER_LEVEL_DESCRIPTIONS,
  
  // Feedback
  FEEDBACK_TYPES,
  FEEDBACK_LABELS,
  FEEDBACK_EMOJIS,
  
  // Theme
  THEMES,
  THEME_LABELS,
  
  // Animation
  ANIMATION,
  
  // Limits
  LIMITS,
  
  // Patterns
  PATTERNS,
} from './constants';

// Helpers
export {
  // Time formatting
  formatTime,
  parseTimecode,
  formatProcessingTime,
  
  // ID generation
  generateUserId,
  generateMessageId,
  
  // Text manipulation
  truncateText,
  capitalize,
  toTitleCase,
  
  // Class names
  classNames,
  cn,
  
  // State helpers
  getStateColor,
  getStateEmoji,
  
  // Date/time helpers
  formatDate,
  formatDateTime,
  getRelativeTime,
  pluralize,
  
  // Misc helpers
  delay,
  getTypingDuration,
  debounce,
  throttle,
  deepClone,
  isBrowser,
  getConfidenceLabel,
  getConfidenceColor,
} from './helpers';

// Validators
export {
  // API Key validation
  isValidApiKey,
  getApiKeyError,
  
  // User ID validation
  isValidUserId,
  getUserIdError,
  
  // Input sanitization
  sanitizeInput,
  sanitizeMessage,
  escapeHtml,
  
  // Message validation
  isValidMessage,
  getMessageError,
  
  // Rating validation
  isValidRating,
  
  // URL validation
  isValidUrl,
  isValidYoutubeUrl,
  extractYoutubeVideoId,
  
  // Timecode validation
  isValidTimecode,
  
  // Email validation
  isValidEmail,
  
  // Type guards
  isDefined,
  isNonEmptyString,
  isPositiveNumber,
} from './validators';


