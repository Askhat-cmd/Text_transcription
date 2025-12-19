/**
 * Formatter Service for Bot Psychologist Web UI
 * 
 * Utility functions for formatting dates, times, and other data.
 */

import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns';
import { ru } from 'date-fns/locale';

class FormatterService {
  // === TIME FORMATTING ===

  /**
   * Format seconds to MM:SS or HH:MM:SS format
   */
  formatTime(seconds: number | string): string {
    const totalSeconds = typeof seconds === 'string' ? parseInt(seconds, 10) : seconds;
    
    if (isNaN(totalSeconds) || totalSeconds < 0) return '00:00';
    
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const secs = Math.floor(totalSeconds % 60);
    
    if (hours > 0) {
      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  /**
   * Parse timecode string (HH:MM:SS or MM:SS) to seconds
   */
  parseTimecode(timecode: string): number {
    const parts = timecode.split(':').map(p => parseInt(p, 10));
    
    if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    } else if (parts.length === 2) {
      return parts[0] * 60 + parts[1];
    }
    return 0;
  }

  /**
   * Format processing time in seconds to human readable format
   */
  formatProcessingTime(seconds: number): string {
    if (seconds < 1) {
      return `${Math.round(seconds * 1000)}ms`;
    }
    return `${seconds.toFixed(2)}s`;
  }

  // === DATE FORMATTING ===

  /**
   * Format date to localized string
   */
  formatDate(date: Date | string, formatStr: string = 'dd MMMM yyyy'): string {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    
    if (!isValid(dateObj)) return 'Invalid date';
    
    return format(dateObj, formatStr, { locale: ru });
  }

  /**
   * Format date to relative time (e.g., "5 минут назад")
   */
  formatRelativeTime(date: Date | string): string {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    
    if (!isValid(dateObj)) return 'Invalid date';
    
    return formatDistanceToNow(dateObj, { addSuffix: true, locale: ru });
  }

  /**
   * Format date for chat messages
   */
  formatMessageTime(date: Date | string): string {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    
    if (!isValid(dateObj)) return '';
    
    const now = new Date();
    const isToday = dateObj.toDateString() === now.toDateString();
    
    if (isToday) {
      return format(dateObj, 'HH:mm', { locale: ru });
    }
    
    return format(dateObj, 'dd MMM, HH:mm', { locale: ru });
  }

  /**
   * Format ISO timestamp from API
   */
  formatTimestamp(timestamp: string): string {
    try {
      const date = parseISO(timestamp);
      return this.formatMessageTime(date);
    } catch {
      return timestamp;
    }
  }

  // === NUMBER FORMATTING ===

  /**
   * Format number with thousand separators
   */
  formatNumber(num: number): string {
    return new Intl.NumberFormat('ru-RU').format(num);
  }

  /**
   * Format percentage
   */
  formatPercent(value: number, decimals: number = 0): string {
    return `${(value * 100).toFixed(decimals)}%`;
  }

  /**
   * Format confidence score (0-1) to percentage
   */
  formatConfidence(confidence: number): string {
    return this.formatPercent(confidence, 0);
  }

  // === TEXT FORMATTING ===

  /**
   * Truncate text with ellipsis
   */
  truncate(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength - 3) + '...';
  }

  /**
   * Capitalize first letter
   */
  capitalize(text: string): string {
    if (!text) return '';
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  /**
   * Format user level to Russian
   */
  formatUserLevel(level: string): string {
    const levels: Record<string, string> = {
      beginner: 'Начинающий',
      intermediate: 'Средний',
      advanced: 'Продвинутый',
    };
    return levels[level] || level;
  }

  /**
   * Format feedback type to Russian
   */
  formatFeedbackType(type: string): string {
    const types: Record<string, string> = {
      positive: 'Положительный',
      negative: 'Отрицательный',
      neutral: 'Нейтральный',
    };
    return types[type] || type;
  }

  // === URL FORMATTING ===

  /**
   * Create YouTube URL with timestamp
   */
  formatYouTubeUrl(baseUrl: string, startSeconds: number | string): string {
    const seconds = typeof startSeconds === 'string' 
      ? this.parseTimecode(startSeconds) 
      : startSeconds;
    
    // Handle different YouTube URL formats
    if (baseUrl.includes('youtu.be/')) {
      return `${baseUrl}?t=${seconds}`;
    }
    
    if (baseUrl.includes('youtube.com/watch')) {
      const separator = baseUrl.includes('?') ? '&' : '?';
      return `${baseUrl}${separator}t=${seconds}`;
    }
    
    return baseUrl;
  }
}

// Singleton instance
export const formatterService = new FormatterService();
