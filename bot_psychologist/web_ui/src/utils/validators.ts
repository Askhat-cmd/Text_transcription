/**
 * Validators for Bot Psychologist Web UI
 * 
 * Input validation and sanitization utilities.
 */

import { PATTERNS, LIMITS } from './constants';

// ===== API KEY VALIDATION =====

/**
 * Validate API key format
 * @param apiKey - API key to validate
 * @returns True if valid format
 */
export function isValidApiKey(apiKey: string | null | undefined): boolean {
  if (!apiKey || typeof apiKey !== 'string') {
    return false;
  }

  const trimmed = apiKey.trim();
  
  // Must be at least 20 characters
  if (trimmed.length < 20) {
    return false;
  }

  // Must match allowed pattern (alphanumeric, dash, underscore)
  return PATTERNS.API_KEY.test(trimmed);
}

/**
 * Get API key validation error message
 * @param apiKey - API key to validate
 * @returns Error message or null if valid
 */
export function getApiKeyError(apiKey: string | null | undefined): string | null {
  if (!apiKey || typeof apiKey !== 'string') {
    return 'API ключ обязателен';
  }

  const trimmed = apiKey.trim();

  if (trimmed.length === 0) {
    return 'API ключ не может быть пустым';
  }

  if (trimmed.length < 20) {
    return 'API ключ должен быть не менее 20 символов';
  }

  if (!PATTERNS.API_KEY.test(trimmed)) {
    return 'API ключ может содержать только буквы, цифры, дефис и подчёркивание';
  }

  return null;
}

// ===== USER ID VALIDATION =====

/**
 * Validate user ID format
 * @param userId - User ID to validate
 * @returns True if valid format
 */
export function isValidUserId(userId: string | null | undefined): boolean {
  if (!userId || typeof userId !== 'string') {
    return false;
  }

  const trimmed = userId.trim();

  // Check for UUID format
  if (PATTERNS.UUID.test(trimmed)) {
    return true;
  }

  // Check for custom ID format (8-64 chars, alphanumeric + dash/underscore)
  return PATTERNS.USER_ID.test(trimmed);
}

/**
 * Get user ID validation error message
 * @param userId - User ID to validate
 * @returns Error message or null if valid
 */
export function getUserIdError(userId: string | null | undefined): string | null {
  if (!userId || typeof userId !== 'string') {
    return 'User ID обязателен';
  }

  const trimmed = userId.trim();

  if (trimmed.length === 0) {
    return 'User ID не может быть пустым';
  }

  if (trimmed.length < 8) {
    return 'User ID должен быть не менее 8 символов';
  }

  if (trimmed.length > 64) {
    return 'User ID не должен превышать 64 символа';
  }

  if (!PATTERNS.USER_ID.test(trimmed) && !PATTERNS.UUID.test(trimmed)) {
    return 'User ID может содержать только буквы, цифры, дефис и подчёркивание';
  }

  return null;
}

// ===== INPUT SANITIZATION =====

/**
 * Sanitize user input by removing potentially dangerous content
 * @param input - Raw user input
 * @returns Sanitized input
 */
export function sanitizeInput(input: string | null | undefined): string {
  if (!input || typeof input !== 'string') {
    return '';
  }

  return input
    // Remove null bytes
    .replace(/\0/g, '')
    // Remove control characters (except newlines and tabs)
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '')
    // Trim whitespace
    .trim();
}

/**
 * Sanitize and normalize message input
 * @param input - Raw message input
 * @returns Sanitized message
 */
export function sanitizeMessage(input: string | null | undefined): string {
  const sanitized = sanitizeInput(input);
  
  if (!sanitized) {
    return '';
  }

  // Normalize multiple newlines to max 2
  let normalized = sanitized.replace(/\n{3,}/g, '\n\n');

  // Normalize multiple spaces to single space (but preserve newlines)
  normalized = normalized.replace(/[^\S\n]+/g, ' ');

  // Truncate if too long
  if (normalized.length > LIMITS.MAX_MESSAGE_LENGTH) {
    normalized = normalized.substring(0, LIMITS.MAX_MESSAGE_LENGTH);
  }

  return normalized;
}

/**
 * Escape HTML special characters
 * @param html - String potentially containing HTML
 * @returns Escaped string safe for display
 */
export function escapeHtml(html: string | null | undefined): string {
  if (!html || typeof html !== 'string') {
    return '';
  }

  const htmlEscapes: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };

  return html.replace(/[&<>"']/g, (char) => htmlEscapes[char] || char);
}

// ===== MESSAGE VALIDATION =====

/**
 * Validate message content
 * @param message - Message to validate
 * @returns True if valid
 */
export function isValidMessage(message: string | null | undefined): boolean {
  if (!message || typeof message !== 'string') {
    return false;
  }

  const trimmed = message.trim();
  
  // Must have content
  if (trimmed.length === 0) {
    return false;
  }

  // Must not exceed max length
  if (trimmed.length > LIMITS.MAX_MESSAGE_LENGTH) {
    return false;
  }

  return true;
}

/**
 * Get message validation error
 * @param message - Message to validate
 * @returns Error message or null if valid
 */
export function getMessageError(message: string | null | undefined): string | null {
  if (!message || typeof message !== 'string') {
    return 'Сообщение обязательно';
  }

  const trimmed = message.trim();

  if (trimmed.length === 0) {
    return 'Введите сообщение';
  }

  if (trimmed.length > LIMITS.MAX_MESSAGE_LENGTH) {
    return `Сообщение не должно превышать ${LIMITS.MAX_MESSAGE_LENGTH} символов`;
  }

  return null;
}

// ===== RATING VALIDATION =====

/**
 * Validate rating value
 * @param rating - Rating to validate
 * @returns True if valid (1-5)
 */
export function isValidRating(rating: number | null | undefined): boolean {
  if (rating === null || rating === undefined) {
    return false;
  }

  if (typeof rating !== 'number' || !Number.isInteger(rating)) {
    return false;
  }

  return rating >= LIMITS.MIN_RATING && rating <= LIMITS.MAX_RATING;
}

// ===== URL VALIDATION =====

/**
 * Validate URL format
 * @param url - URL to validate
 * @returns True if valid URL
 */
export function isValidUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== 'string') {
    return false;
  }

  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validate YouTube URL
 * @param url - URL to validate
 * @returns True if valid YouTube URL
 */
export function isValidYoutubeUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== 'string') {
    return false;
  }

  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname.toLowerCase();
    
    return (
      hostname === 'youtube.com' ||
      hostname === 'www.youtube.com' ||
      hostname === 'youtu.be' ||
      hostname === 'm.youtube.com'
    );
  } catch {
    return false;
  }
}

/**
 * Extract YouTube video ID from URL
 * @param url - YouTube URL
 * @returns Video ID or null
 */
export function extractYoutubeVideoId(url: string | null | undefined): string | null {
  if (!url || typeof url !== 'string') {
    return null;
  }

  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname.toLowerCase();

    // Handle youtu.be/VIDEO_ID format
    if (hostname === 'youtu.be') {
      return parsed.pathname.slice(1) || null;
    }

    // Handle youtube.com/watch?v=VIDEO_ID format
    if (hostname.includes('youtube.com')) {
      return parsed.searchParams.get('v') || null;
    }

    return null;
  } catch {
    return null;
  }
}

// ===== TIMECODE VALIDATION =====

/**
 * Validate timecode format (MM:SS or HH:MM:SS)
 * @param timecode - Timecode string
 * @returns True if valid format
 */
export function isValidTimecode(timecode: string | null | undefined): boolean {
  if (!timecode || typeof timecode !== 'string') {
    return false;
  }

  return PATTERNS.TIMECODE.test(timecode.trim());
}

// ===== EMAIL VALIDATION =====

/**
 * Validate email format (basic validation)
 * @param email - Email to validate
 * @returns True if valid format
 */
export function isValidEmail(email: string | null | undefined): boolean {
  if (!email || typeof email !== 'string') {
    return false;
  }

  // Basic email validation
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailPattern.test(email.trim());
}

// ===== TYPE GUARDS =====

/**
 * Check if value is non-null and non-undefined
 * @param value - Value to check
 * @returns True if value exists
 */
export function isDefined<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}

/**
 * Check if value is a non-empty string
 * @param value - Value to check
 * @returns True if non-empty string
 */
export function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

/**
 * Check if value is a positive number
 * @param value - Value to check
 * @returns True if positive number
 */
export function isPositiveNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0;
}


