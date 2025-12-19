/**
 * PathBuilder Component
 * 
 * Visualization of user's transformation path from current state to target state.
 * Shows progress bar, steps count, duration, and key focus.
 */

import React from 'react';
import clsx from 'clsx';
import { 
  FiTarget, 
  FiTrendingUp, 
  FiClock, 
  FiLayers,
  FiArrowRight,
  FiCheckCircle
} from 'react-icons/fi';
import type { PathRecommendation, PathStep } from '../../types';
import { getStateEmoji, getStateColor } from './StateCard';
import PathStepCard from './PathStep';

// ===== TYPES =====

interface PathBuilderProps {
  /** Path recommendation from API */
  path: PathRecommendation;
  /** Current progress percentage (0-100) */
  progress?: number;
  /** Show first step details */
  showFirstStep?: boolean;
  /** Compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

interface PathBuilderFullProps {
  path: PathRecommendation;
  allSteps?: PathStep[];
  currentStepIndex?: number;
  className?: string;
}

// ===== HELPER FUNCTIONS =====

/**
 * Calculate estimated completion date
 */
const getEstimatedCompletion = (weeks: number): string => {
  const date = new Date();
  date.setDate(date.getDate() + weeks * 7);
  return date.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' });
};

// ===== STATE BADGE COMPONENT =====

interface StateBadgeProps {
  state: string;
  label?: string;
  size?: 'sm' | 'md';
}

const StateBadge: React.FC<StateBadgeProps> = ({ state, label, size = 'md' }) => {
  const isSm = size === 'sm';
  
  return (
    <div className="text-center">
      {label && (
        <p className={clsx(
          'text-gray-500 dark:text-gray-400 mb-1',
          isSm ? 'text-[10px]' : 'text-xs'
        )}>
          {label}
        </p>
      )}
      <div className={clsx(
        'inline-flex items-center gap-1 rounded-full px-3 py-1 border',
        getStateColor(state),
        isSm ? 'text-xs' : 'text-sm'
      )}>
        <span>{getStateEmoji(state)}</span>
        <span className="font-medium capitalize">{state}</span>
      </div>
    </div>
  );
};

// ===== PROGRESS BAR COMPONENT =====

interface ProgressBarProps {
  progress: number;
  showLabel?: boolean;
  className?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ 
  progress, 
  showLabel = true,
  className 
}) => {
  return (
    <div className={className}>
      {showLabel && (
        <div className="flex justify-between items-center text-xs mb-1">
          <span className="text-gray-500 dark:text-gray-400">Прогресс</span>
          <span className="font-semibold text-purple-600 dark:text-purple-400">
            {progress}%
          </span>
        </div>
      )}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};

// ===== STATS GRID COMPONENT =====

interface StatsGridProps {
  stepsCount: number;
  durationWeeks: number;
  keyFocus?: string;
  compact?: boolean;
}

const StatsGrid: React.FC<StatsGridProps> = ({ 
  stepsCount, 
  durationWeeks, 
  keyFocus,
  compact = false 
}) => {
  const stats = [
    { 
      icon: FiLayers, 
      value: stepsCount, 
      label: 'Шагов',
      color: 'text-blue-500'
    },
    { 
      icon: FiClock, 
      value: durationWeeks, 
      label: 'Недель',
      color: 'text-green-500'
    },
  ];

  return (
    <div className={clsx(
      'grid gap-3',
      keyFocus && !compact ? 'grid-cols-3' : 'grid-cols-2'
    )}>
      {stats.map((stat, idx) => (
        <div 
          key={idx}
          className="text-center p-2 bg-white/50 dark:bg-gray-800/50 rounded-lg"
        >
          <stat.icon className={clsx('w-4 h-4 mx-auto mb-1', stat.color)} />
          <p className="font-bold text-lg text-gray-800 dark:text-gray-200">
            {stat.value}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {stat.label}
          </p>
        </div>
      ))}
      
      {keyFocus && !compact && (
        <div className="text-center p-2 bg-white/50 dark:bg-gray-800/50 rounded-lg">
          <FiTarget className="w-4 h-4 mx-auto mb-1 text-purple-500" />
          <p className="font-bold text-sm text-gray-800 dark:text-gray-200 truncate">
            {keyFocus.split(':')[0] || keyFocus.split(' ').slice(0, 2).join(' ')}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Фокус
          </p>
        </div>
      )}
    </div>
  );
};

// ===== COMPACT PATH BUILDER =====

/**
 * Compact inline path visualization
 */
export const PathBuilderCompact: React.FC<PathBuilderProps> = ({
  path,
  progress = 0,
  className,
}) => {
  return (
    <div className={clsx(
      'bg-gradient-to-r from-purple-50 to-indigo-50',
      'dark:from-purple-900/20 dark:to-indigo-900/20',
      'rounded-lg p-3',
      className
    )}>
      <div className="flex items-center justify-between gap-3">
        {/* States */}
        <div className="flex items-center gap-2 text-sm">
          <span>{getStateEmoji(path.current_state)}</span>
          <span className="font-medium capitalize">{path.current_state}</span>
          <FiArrowRight className="text-gray-400" />
          <span>{getStateEmoji(path.target_state)}</span>
          <span className="font-medium capitalize">{path.target_state}</span>
        </div>

        {/* Stats */}
        <div className="text-xs text-gray-500 dark:text-gray-400">
          {path.steps_count} шагов • {path.total_duration_weeks} нед.
        </div>
      </div>

      {/* Progress Bar */}
      <ProgressBar progress={progress} showLabel={false} className="mt-2" />
    </div>
  );
};

// ===== MAIN PATH BUILDER =====

/**
 * Full path visualization with all details
 */
export const PathBuilder: React.FC<PathBuilderProps> = ({
  path,
  progress = 0,
  showFirstStep = true,
  compact = false,
  className,
}) => {
  if (compact) {
    return <PathBuilderCompact path={path} progress={progress} className={className} />;
  }

  return (
    <div className={clsx(
      'bg-gradient-to-br from-purple-50 via-indigo-50 to-blue-50',
      'dark:from-purple-900/20 dark:via-indigo-900/20 dark:to-blue-900/20',
      'rounded-xl p-5 border border-purple-200 dark:border-purple-800',
      className
    )}>
      {/* Header */}
      <h3 className="font-bold text-base mb-4 flex items-center gap-2 text-gray-800 dark:text-gray-200">
        <FiTrendingUp className="text-purple-500" />
        🛤️ Ваш путь трансформации
      </h3>

      {/* Current → Target States */}
      <div className="flex items-center justify-between gap-4 mb-5">
        <StateBadge state={path.current_state} label="Текущее" />
        
        <div className="flex-1 relative px-4">
          <div className="h-1 bg-gradient-to-r from-purple-400 to-indigo-500 rounded-full" />
          <div 
            className="absolute top-1/2 -translate-y-1/2 bg-white dark:bg-gray-800 rounded-full p-1 shadow-md"
            style={{ left: `${progress}%` }}
          >
            <FiArrowRight className="text-purple-500 w-4 h-4" />
          </div>
        </div>
        
        <StateBadge state={path.target_state} label="Целевое" />
      </div>

      {/* Progress Bar */}
      <ProgressBar progress={progress} className="mb-4" />

      {/* Stats Grid */}
      <StatsGrid 
        stepsCount={path.steps_count}
        durationWeeks={path.total_duration_weeks}
        keyFocus={path.key_focus}
      />

      {/* Key Focus */}
      <div className="mt-4 p-3 bg-white/60 dark:bg-gray-800/60 rounded-lg border border-purple-200 dark:border-purple-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
          💡 Ключевой фокус
        </p>
        <p className="text-sm text-purple-700 dark:text-purple-300 italic">
          {path.key_focus}
        </p>
      </div>

      {/* First Step Preview */}
      {showFirstStep && path.first_step && (
        <div className="mt-4">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">
            📌 Первый шаг
          </p>
          <PathStepCard step={path.first_step} isActive />
        </div>
      )}

      {/* Estimated Completion */}
      <div className="mt-4 text-center text-xs text-gray-500 dark:text-gray-400">
        <FiCheckCircle className="inline w-3 h-3 mr-1" />
        Ожидаемое завершение: {getEstimatedCompletion(path.total_duration_weeks)}
      </div>
    </div>
  );
};

// ===== FULL PATH BUILDER WITH ALL STEPS =====

/**
 * Path builder with all steps visualization
 */
export const PathBuilderFull: React.FC<PathBuilderFullProps> = ({
  path,
  allSteps = [],
  currentStepIndex = 0,
  className,
}) => {
  const steps = allSteps.length > 0 ? allSteps : (path.first_step ? [path.first_step] : []);
  const progress = allSteps.length > 0 
    ? Math.round((currentStepIndex / allSteps.length) * 100) 
    : 0;

  return (
    <div className={clsx(
      'bg-gradient-to-br from-purple-50 via-indigo-50 to-blue-50',
      'dark:from-purple-900/20 dark:via-indigo-900/20 dark:to-blue-900/20',
      'rounded-xl p-5 border border-purple-200 dark:border-purple-800',
      className
    )}>
      {/* Header with States */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-base flex items-center gap-2 text-gray-800 dark:text-gray-200">
          🛤️ Путь трансформации
        </h3>
        <div className="flex items-center gap-2 text-sm">
          <StateBadge state={path.current_state} size="sm" />
          <FiArrowRight className="text-gray-400" />
          <StateBadge state={path.target_state} size="sm" />
        </div>
      </div>

      {/* Progress */}
      <ProgressBar progress={progress} className="mb-4" />

      {/* Steps List */}
      {steps.length > 0 && (
        <div className="space-y-3">
          {steps.map((step, idx) => (
            <PathStepCard
              key={step.step_number || idx}
              step={step}
              isActive={idx === currentStepIndex}
              isCompleted={idx < currentStepIndex}
            />
          ))}
        </div>
      )}

      {/* Summary */}
      <div className="mt-4 pt-4 border-t border-purple-200 dark:border-purple-700">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">
            {currentStepIndex} из {path.steps_count} шагов
          </span>
          <span className="text-gray-500 dark:text-gray-400">
            ~{path.total_duration_weeks} недель
          </span>
        </div>
      </div>
    </div>
  );
};

export default PathBuilder;
