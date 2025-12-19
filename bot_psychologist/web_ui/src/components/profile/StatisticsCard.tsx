/**
 * StatisticsCard Component
 * 
 * Card displaying user statistics including total turns,
 * state distribution, and rating history.
 */

import React from 'react';
import clsx from 'clsx';
import { 
  FiBarChart2, 
  FiActivity, 
  FiStar,
  FiPieChart,
  FiTrendingUp,
  FiMessageSquare
} from 'react-icons/fi';
import type { UserProfileStats } from '../../types';
import { getStateEmoji } from '../insights/StateCard';

// ===== TYPES =====

interface StatisticsCardProps {
  /** Total turns/messages */
  totalTurns: number;
  /** Top states distribution (state -> count) */
  topStates: Record<string, number>;
  /** Rating distribution (1-5 -> count) */
  ratingDistribution?: Record<number, number>;
  /** Average rating */
  averageRating?: number;
  /** Full profile stats (optional, for extended view) */
  profileStats?: UserProfileStats;
  /** Compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

interface StateBarProps {
  state: string;
  count: number;
  total: number;
  maxCount: number;
}

interface RatingBarProps {
  rating: number;
  count: number;
  total: number;
  maxCount: number;
}

// ===== HELPERS =====

/**
 * Calculate percentage
 */
const calcPercent = (value: number, total: number): number => {
  if (total === 0) return 0;
  return Math.round((value / total) * 100);
};

/**
 * Get rating star color
 */
const getRatingColor = (rating: number): string => {
  if (rating >= 4) return 'bg-green-500';
  if (rating >= 3) return 'bg-yellow-500';
  return 'bg-red-500';
};

// ===== SUBCOMPONENTS =====

/**
 * State distribution bar
 */
const StateBar: React.FC<StateBarProps> = ({ state, count, total, maxCount }) => {
  const percent = calcPercent(count, total);
  const barWidth = maxCount > 0 ? (count / maxCount) * 100 : 0;
  
  return (
    <div className="flex items-center gap-2">
      <div className="w-6 text-center">
        {getStateEmoji(state)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium capitalize text-gray-700 dark:text-gray-300 truncate">
            {state}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {count} ({percent}%)
          </span>
        </div>
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div 
            className={clsx(
              'h-full rounded-full transition-all duration-500',
              state === 'curious' && 'bg-blue-500',
              state === 'overwhelmed' && 'bg-red-500',
              state === 'resistant' && 'bg-orange-500',
              state === 'committed' && 'bg-green-500',
              state === 'practicing' && 'bg-indigo-500',
              state === 'stagnant' && 'bg-yellow-500',
              state === 'breakthrough' && 'bg-purple-500',
              state === 'integrated' && 'bg-emerald-500',
              !['curious', 'overwhelmed', 'resistant', 'committed', 'practicing', 'stagnant', 'breakthrough', 'integrated'].includes(state) && 'bg-gray-500'
            )}
            style={{ width: `${barWidth}%` }}
          />
        </div>
      </div>
    </div>
  );
};

/**
 * Rating distribution bar
 */
const RatingBar: React.FC<RatingBarProps> = ({ rating, count, total, maxCount }) => {
  const percent = calcPercent(count, total);
  const barWidth = maxCount > 0 ? (count / maxCount) * 100 : 0;
  
  return (
    <div className="flex items-center gap-2">
      <div className="w-12 flex items-center gap-0.5">
        {Array.from({ length: rating }).map((_, i) => (
          <FiStar 
            key={i} 
            className="w-2.5 h-2.5 fill-yellow-400 text-yellow-400" 
          />
        ))}
      </div>
      <div className="flex-1">
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div 
            className={clsx('h-full rounded-full transition-all duration-500', getRatingColor(rating))}
            style={{ width: `${barWidth}%` }}
          />
        </div>
      </div>
      <span className="w-12 text-right text-xs text-gray-500 dark:text-gray-400">
        {count} ({percent}%)
      </span>
    </div>
  );
};

/**
 * Summary stat item
 */
const SummaryStat: React.FC<{ icon: React.ReactNode; value: string | number; label: string }> = ({ 
  icon, 
  value, 
  label 
}) => (
  <div className="text-center">
    <div className="text-purple-500 mb-1">{icon}</div>
    <p className="font-bold text-xl text-gray-800 dark:text-gray-200">{value}</p>
    <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
  </div>
);

// ===== MAIN COMPONENT =====

/**
 * Full statistics card
 */
export const StatisticsCard: React.FC<StatisticsCardProps> = ({
  totalTurns,
  topStates,
  ratingDistribution = {},
  averageRating = 0,
  profileStats: _profileStats,
  compact = false,
  className,
}) => {
  // Note: profileStats available for future extended stats display
  void _profileStats;
  // Calculate totals and max for state distribution
  const stateEntries = Object.entries(topStates)
    .sort(([, a], [, b]) => b - a);
  const totalStates = stateEntries.reduce((sum, [, count]) => sum + count, 0);
  const maxStateCount = Math.max(...Object.values(topStates), 1);

  // Calculate totals and max for rating distribution
  const ratingEntries = Object.entries(ratingDistribution)
    .map(([k, v]) => [Number(k), v] as [number, number])
    .sort(([a], [b]) => b - a);
  const totalRatings = ratingEntries.reduce((sum, [, count]) => sum + count, 0);
  const maxRatingCount = Math.max(...Object.values(ratingDistribution), 1);

  const hasStates = stateEntries.length > 0;
  const hasRatings = ratingEntries.length > 0;

  if (compact) {
    return (
      <div className={clsx(
        'bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-3',
        className
      )}>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            <FiMessageSquare className="inline w-4 h-4 mr-1" />
            {totalTurns} сообщений
          </span>
          {averageRating > 0 && (
            <span className="text-sm text-gray-600 dark:text-gray-400">
              <FiStar className="inline w-4 h-4 mr-1 text-yellow-500" />
              {averageRating.toFixed(1)}
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={clsx(
      'bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden',
      className
    )}>
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
          <FiBarChart2 className="text-indigo-500" />
          Статистика
        </h3>
      </div>

      <div className="p-4">
        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6 pb-4 border-b border-gray-200 dark:border-gray-700">
          <SummaryStat
            icon={<FiMessageSquare className="w-5 h-5 mx-auto" />}
            value={totalTurns}
            label="Сообщений"
          />
          <SummaryStat
            icon={<FiActivity className="w-5 h-5 mx-auto" />}
            value={stateEntries.length}
            label="Состояний"
          />
          <SummaryStat
            icon={<FiStar className="w-5 h-5 mx-auto" />}
            value={averageRating > 0 ? averageRating.toFixed(1) : '—'}
            label="Рейтинг"
          />
        </div>

        {/* State Distribution */}
        {hasStates && (
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
              <FiPieChart className="w-4 h-4 text-purple-500" />
              Распределение состояний
            </h4>
            <div className="space-y-3">
              {stateEntries.slice(0, 5).map(([state, count]) => (
                <StateBar
                  key={state}
                  state={state}
                  count={count}
                  total={totalStates}
                  maxCount={maxStateCount}
                />
              ))}
              {stateEntries.length > 5 && (
                <p className="text-xs text-gray-400 text-center mt-2">
                  +{stateEntries.length - 5} других состояний
                </p>
              )}
            </div>
          </div>
        )}

        {/* Rating Distribution */}
        {hasRatings && (
          <div>
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
              <FiTrendingUp className="w-4 h-4 text-yellow-500" />
              История оценок
            </h4>
            <div className="space-y-2">
              {[5, 4, 3, 2, 1].map((rating) => (
                <RatingBar
                  key={rating}
                  rating={rating}
                  count={ratingDistribution[rating] || 0}
                  total={totalRatings}
                  maxCount={maxRatingCount}
                />
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!hasStates && !hasRatings && (
          <div className="text-center py-6 text-gray-400">
            <FiActivity className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">Пока нет статистики</p>
            <p className="text-xs mt-1">Начните диалог, чтобы собрать данные</p>
          </div>
        )}
      </div>
    </div>
  );
};

// ===== STATS SUMMARY INLINE =====

interface StatsSummaryProps {
  totalTurns: number;
  totalStates: number;
  averageRating: number;
  className?: string;
}

/**
 * Inline stats summary for compact views
 */
export const StatsSummary: React.FC<StatsSummaryProps> = ({
  totalTurns,
  totalStates,
  averageRating,
  className,
}) => (
  <div className={clsx('flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400', className)}>
    <span className="flex items-center gap-1">
      <FiMessageSquare className="w-4 h-4" />
      {totalTurns}
    </span>
    <span className="flex items-center gap-1">
      <FiActivity className="w-4 h-4" />
      {totalStates}
    </span>
    {averageRating > 0 && (
      <span className="flex items-center gap-1">
        <FiStar className="w-4 h-4 text-yellow-500" />
        {averageRating.toFixed(1)}
      </span>
    )}
  </div>
);

export default StatisticsCard;
