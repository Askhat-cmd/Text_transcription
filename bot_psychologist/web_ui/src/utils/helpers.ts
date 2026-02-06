/**
 * Helper Functions for Bot Psychologist Web UI
 * 
 * General-purpose utility functions used throughout the application.
 */

import { clsx, type ClassValue } from 'clsx';
import { STATE_COLORS, STATE_EMOJIS, ANIMATION } from './constants';

// ===== TIME FORMATTING =====

/**
 * Format seconds to MM:SS or HH:MM:SS format
 * @param seconds - Number of seconds to format
 * @returns Formatted time string (e.g., "03:45" or "1:23:45")
 */
export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return '00:00';
  }

  const totalSeconds = Math.floor(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  const paddedMinutes = String(minutes).padStart(2, '0');
  const paddedSeconds = String(secs).padStart(2, '0');

  if (hours > 0) {
    return `${hours}:${paddedMinutes}:${paddedSeconds}`;
  }
  
  return `${paddedMinutes}:${paddedSeconds}`;
}

/**
 * Parse timecode string to seconds
 * @param timecode - Timecode string (e.g., "03:45" or "1:23:45")
 * @returns Number of seconds
 */
export function parseTimecode(timecode: string): number {
  const parts = timecode.split(':').map(Number);
  
  if (parts.some(isNaN)) {
    return 0;
  }

  if (parts.length === 3) {
    // HH:MM:SS
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  } else if (parts.length === 2) {
    // MM:SS
    return parts[0] * 60 + parts[1];
  }
  
  return 0;
}

/**
 * Format processing time for display
 * @param seconds - Processing time in seconds
 * @returns Formatted string (e.g., "1.23 сек")
 */
export function formatProcessingTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return '0 сек';
  }

  if (seconds < 1) {
    return `${Math.round(seconds * 1000)} мс`;
  }

  return `${seconds.toFixed(2)} сек`;
}

// ===== ID GENERATION =====

/**
 * Generate a unique user ID
 * @returns UUID v4 string
 */
export function generateUserId(): string {
  // Use crypto.randomUUID if available (modern browsers)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Generate a unique message ID
 * @returns Unique string ID
 */
export function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// ===== TEXT MANIPULATION =====

/**
 * Truncate text to a maximum length with ellipsis
 * @param text - Text to truncate
 * @param maxLength - Maximum length (default: 100)
 * @param suffix - Suffix to add when truncated (default: "...")
 * @returns Truncated text
 */
export function truncateText(
  text: string,
  maxLength: number = 100,
  suffix: string = '...'
): string {
  if (!text || text.length <= maxLength) {
    return text || '';
  }

  // Try to break at a word boundary
  const truncated = text.substring(0, maxLength - suffix.length);
  const lastSpace = truncated.lastIndexOf(' ');

  if (lastSpace > maxLength * 0.7) {
    return truncated.substring(0, lastSpace) + suffix;
  }

  return truncated + suffix;
}

/**
 * Capitalize first letter of a string
 * @param text - Text to capitalize
 * @returns Capitalized text
 */
export function capitalize(text: string): string {
  if (!text) return '';
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * Convert text to title case
 * @param text - Text to convert
 * @returns Title case text
 */
export function toTitleCase(text: string): string {
  if (!text) return '';
  return text
    .toLowerCase()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// ===== CLASS NAMES HELPER =====

/**
 * Merge class names using clsx
 * Wrapper around clsx for consistent usage
 * @param inputs - Class values to merge
 * @returns Merged class string
 */
export function classNames(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

/**
 * Alias for classNames
 */
export const cn = classNames;

// ===== STATE HELPERS =====

/**
 * Get color for a psychological state
 * @param state - State name
 * @returns Color hex code
 */
export function getStateColor(state: string): string {
  const normalizedState = state.toLowerCase().trim();
  return STATE_COLORS[normalizedState] || STATE_COLORS['default'];
}

/**
 * Get emoji for a psychological state
 * @param state - State name
 * @returns Emoji character
 */
export function getStateEmoji(state: string): string {
  const normalizedState = state.toLowerCase().trim();
  return STATE_EMOJIS[normalizedState] || STATE_EMOJIS['default'];
}

// ===== DATE/TIME HELPERS =====

/**
 * Format date for display
 * @param date - Date object or ISO string
 * @returns Formatted date string
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  
  if (isNaN(d.getTime())) {
    return '';
  }

  return d.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

/**
 * Format date and time for display
 * @param date - Date object or ISO string
 * @returns Formatted datetime string
 */
export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  
  if (isNaN(d.getTime())) {
    return '';
  }

  return d.toLocaleString('ru-RU', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Get relative time string (e.g., "5 минут назад")
 * @param date - Date object or ISO string
 * @returns Relative time string
 */
export function getRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  
  if (isNaN(d.getTime())) {
    return '';
  }

  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return 'только что';
  } else if (diffMinutes < 60) {
    return `${diffMinutes} ${pluralize(diffMinutes, 'минуту', 'минуты', 'минут')} назад`;
  } else if (diffHours < 24) {
    return `${diffHours} ${pluralize(diffHours, 'час', 'часа', 'часов')} назад`;
  } else if (diffDays < 7) {
    return `${diffDays} ${pluralize(diffDays, 'день', 'дня', 'дней')} назад`;
  } else {
    return formatDate(d);
  }
}

/**
 * Russian pluralization helper
 * @param n - Number
 * @param one - Form for 1
 * @param few - Form for 2-4
 * @param many - Form for 5+
 * @returns Correct plural form
 */
export function pluralize(n: number, one: string, few: string, many: string): string {
  const absN = Math.abs(n);
  const lastTwo = absN % 100;
  const lastOne = absN % 10;

  if (lastTwo >= 11 && lastTwo <= 19) {
    return many;
  }

  if (lastOne === 1) {
    return one;
  }

  if (lastOne >= 2 && lastOne <= 4) {
    return few;
  }

  return many;
}

// ===== MISC HELPERS =====

/**
 * Delay execution
 * @param ms - Milliseconds to wait
 * @returns Promise that resolves after delay
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Calculate typing animation duration based on text length
 * @param text - Text to "type"
 * @param maxDuration - Maximum duration in ms (default: 2000)
 * @returns Duration in milliseconds
 */
export function getTypingDuration(text: string, maxDuration: number = 2000): number {
  const calculatedDuration = text.length * ANIMATION.TYPING_DELAY;
  return Math.min(calculatedDuration, maxDuration);
}

/**
 * Create a debounced function
 * @param fn - Function to debounce
 * @param wait - Wait time in ms
 * @returns Debounced function
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;

  return function debounced(...args: Parameters<T>) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      fn(...args);
      timeoutId = undefined;
    }, wait);
  };
}

/**
 * Create a throttled function
 * @param fn - Function to throttle
 * @param limit - Throttle limit in ms
 * @returns Throttled function
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false;

  return function throttled(...args: Parameters<T>) {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

/**
 * Deep clone an object
 * @param obj - Object to clone
 * @returns Cloned object
 */
export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Check if running in browser environment
 * @returns True if in browser
 */
export function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

/**
 * Get confidence level label
 * @param confidence - Confidence value (0-1)
 * @returns Label string
 */
export function getConfidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return 'Высокая';
  if (confidence >= 0.5) return 'Средняя';
  return 'Низкая';
}

/**
 * Get confidence color
 * @param confidence - Confidence value (0-1)
 * @returns Tailwind color class
 */
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-green-600';
  if (confidence >= 0.5) return 'text-yellow-600';
  return 'text-red-600';
}


