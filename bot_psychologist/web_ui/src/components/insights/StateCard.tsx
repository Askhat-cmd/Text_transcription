/**
 * StateCard Component
 * 
 * Displays user psychological state with color indication,
 * emoji, and confidence progress bar.
 * 
 * Supports 10 states: curious, overwhelmed, resistant, committed,
 * practicing, stagnant, breakthrough, integrated, confused, unaware
 */

import React from 'react';
import clsx from 'clsx';
import { FiTrendingUp, FiTrendingDown, FiMinus } from 'react-icons/fi';
import type { StateAnalysis } from '../../types';

// ===== TYPES =====

interface StateCardProps {
  /** User state from API */
  state: string;
  /** Confidence score (0-1) */
  confidence?: number;
  /** Show compact version (inline) */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Emotional tone for trend indicator */
  emotionalTone?: string;
  /** Show recommendations */
  showRecommendations?: boolean;
  /** State recommendations */
  recommendations?: string[];
}

// Full state analysis variant
interface StateCardFullProps {
  stateAnalysis: StateAnalysis;
  compact?: boolean;
  className?: string;
}

// ===== HELPERS =====

/**
 * Get Tailwind color classes for state
 */
export const getStateColor = (state: string): string => {
  const colors: Record<string, string> = {
    curious: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700',
    overwhelmed: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700',
    resistant: 'bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-700',
    committed: 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700',
    practicing: 'bg-indigo-100 text-indigo-800 border-indigo-300 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-700',
    stagnant: 'bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-700',
    breakthrough: 'bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-700',
    integrated: 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-700',
    confused: 'bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600',
    unaware: 'bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-700 dark:text-slate-300 dark:border-slate-600',
  };
  return colors[state.toLowerCase()] || colors.confused;
};

/**
 * Get emoji for state
 */
export const getStateEmoji = (state: string): string => {
  const emojis: Record<string, string> = {
    curious: '🤔',
    overwhelmed: '😰',
    resistant: '😤',
    committed: '💪',
    practicing: '🧘',
    stagnant: '🪨',
    breakthrough: '⚡',
    integrated: '🌟',
    confused: '😕',
    unaware: '🙈',
  };
  return emojis[state.toLowerCase()] || '❓';
};

/**
 * Get state description in Russian
 */
export const getStateDescription = (state: string): string => {
  const descriptions: Record<string, string> = {
    curious: 'Любопытство и открытость к новому',
    overwhelmed: 'Чувство перегруженности информацией',
    resistant: 'Сопротивление изменениям',
    committed: 'Приверженность практике',
    practicing: 'Активная практика и интеграция',
    stagnant: 'Застой в развитии',
    breakthrough: 'Момент прорыва и инсайта',
    integrated: 'Полная интеграция знаний',
    confused: 'Неопределённость и замешательство',
    unaware: 'Неосознанность текущего состояния',
  };
  return descriptions[state.toLowerCase()] || 'Текущее состояние';
};

/**
 * Get progress bar color for state
 */
const getProgressColor = (state: string): string => {
  const progressColors: Record<string, string> = {
    curious: 'bg-blue-500',
    overwhelmed: 'bg-red-500',
    resistant: 'bg-orange-500',
    committed: 'bg-green-500',
    practicing: 'bg-indigo-500',
    stagnant: 'bg-yellow-500',
    breakthrough: 'bg-purple-500',
    integrated: 'bg-emerald-500',
    confused: 'bg-gray-500',
    unaware: 'bg-slate-500',
  };
  return progressColors[state.toLowerCase()] || 'bg-gray-500';
};

/**
 * Get trend icon based on emotional tone
 */
const getTrendIcon = (tone?: string) => {
  if (!tone) return null;
  
  const positiveWords = ['positive', 'hopeful', 'excited', 'motivated', 'calm'];
  const negativeWords = ['negative', 'frustrated', 'anxious', 'worried', 'sad'];
  
  const toneLower = tone.toLowerCase();
  
  if (positiveWords.some(word => toneLower.includes(word))) {
    return <FiTrendingUp className="text-green-500" />;
  }
  if (negativeWords.some(word => toneLower.includes(word))) {
    return <FiTrendingDown className="text-red-500" />;
  }
  return <FiMinus className="text-gray-400" />;
};

// ===== COMPACT STATE CARD =====

/**
 * Compact inline state indicator
 */
export const StateCardCompact: React.FC<StateCardProps> = ({
  state,
  confidence = 0,
  className,
}) => {
  return (
    <div
      className={clsx(
        'inline-flex items-center gap-2 rounded-lg px-3 py-1.5 border',
        getStateColor(state),
        className
      )}
    >
      <span className="text-base">{getStateEmoji(state)}</span>
      <span className="font-medium capitalize text-sm">{state}</span>
      {confidence > 0 && (
        <span className="text-xs opacity-70">
          ({Math.round(confidence * 100)}%)
        </span>
      )}
    </div>
  );
};

// ===== MAIN STATE CARD =====

/**
 * Full state card with progress bar and details
 */
export const StateCard: React.FC<StateCardProps> = ({
  state,
  confidence = 0,
  compact = false,
  className,
  emotionalTone,
  showRecommendations = false,
  recommendations = [],
}) => {
  // Compact version
  if (compact) {
    return <StateCardCompact state={state} confidence={confidence} className={className} />;
  }

  return (
    <div
      className={clsx(
        'rounded-xl border-2 p-4 transition-all duration-200',
        getStateColor(state),
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{getStateEmoji(state)}</span>
          <div>
            <h4 className="font-semibold capitalize text-base">{state}</h4>
            <p className="text-xs opacity-70">{getStateDescription(state)}</p>
          </div>
        </div>
        {getTrendIcon(emotionalTone)}
      </div>

      {/* Confidence Progress Bar */}
      {confidence > 0 && (
        <div className="mb-3">
          <div className="flex justify-between items-center text-xs mb-1">
            <span className="opacity-70">Уверенность</span>
            <span className="font-semibold">{Math.round(confidence * 100)}%</span>
          </div>
          <div className="w-full bg-white/50 dark:bg-gray-800/50 rounded-full h-2 overflow-hidden">
            <div
              className={clsx('h-full rounded-full transition-all duration-500', getProgressColor(state))}
              style={{ width: `${Math.round(confidence * 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Emotional Tone */}
      {emotionalTone && (
        <div className="text-xs">
          <span className="opacity-70">Эмоциональный тон: </span>
          <span className="font-medium capitalize">{emotionalTone}</span>
        </div>
      )}

      {/* Recommendations */}
      {showRecommendations && recommendations.length > 0 && (
        <div className="mt-3 pt-3 border-t border-current border-opacity-20">
          <p className="text-xs font-semibold mb-2 opacity-80">💡 Рекомендации:</p>
          <ul className="text-xs space-y-1">
            {recommendations.slice(0, 3).map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="opacity-50">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

// ===== STATE CARD FROM FULL ANALYSIS =====

/**
 * State card initialized from full StateAnalysis object
 */
export const StateCardFull: React.FC<StateCardFullProps> = ({
  stateAnalysis,
  compact = false,
  className,
}) => {
  return (
    <StateCard
      state={stateAnalysis.primary_state}
      confidence={stateAnalysis.confidence}
      emotionalTone={stateAnalysis.emotional_tone}
      recommendations={stateAnalysis.recommendations}
      showRecommendations={!compact}
      compact={compact}
      className={className}
    />
  );
};

export default StateCard;
