/**
 * SourcesList Component
 * 
 * Expandable/collapsible list of YouTube sources with timestamps.
 * Shows block type and complexity score for each source.
 */

import React, { useState } from 'react';
import clsx from 'clsx';
import { 
  FiChevronDown, 
  FiChevronUp, 
  FiExternalLink, 
  FiPlay,
  FiClock,
  FiLayers,
  FiBarChart2
} from 'react-icons/fi';
import type { Source } from '../../types';
import { formatterService } from '../../services/formatter.service';

// ===== TYPES =====

interface SourcesListProps {
  /** Array of sources from API */
  sources: Source[];
  /** Default expanded state */
  defaultExpanded?: boolean;
  /** Maximum sources to show initially */
  maxInitial?: number;
  /** Title for the section */
  title?: string;
  /** Additional CSS classes */
  className?: string;
  /** Compact mode for smaller displays */
  compact?: boolean;
}

interface SourceItemProps {
  source: Source;
  compact?: boolean;
}

// ===== HELPERS =====

/**
 * Format time from seconds to MM:SS or HH:MM:SS
 */
export const formatTime = (seconds: number | string): string => {
  return formatterService.formatTime(seconds);
};

/**
 * Get complexity color based on score
 */
const getComplexityColor = (score: number): string => {
  if (score <= 3) return 'text-green-600 dark:text-green-400';
  if (score <= 6) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
};

/**
 * Get complexity label
 */
const getComplexityLabel = (score: number): string => {
  if (score <= 3) return 'Простой';
  if (score <= 6) return 'Средний';
  return 'Сложный';
};

/**
 * Get block type icon and label
 */
const getBlockTypeInfo = (blockType: string): { icon: string; label: string } => {
  const types: Record<string, { icon: string; label: string }> = {
    teaching: { icon: '📚', label: 'Обучение' },
    exercise: { icon: '🏋️', label: 'Упражнение' },
    meditation: { icon: '🧘', label: 'Медитация' },
    story: { icon: '📖', label: 'История' },
    qa: { icon: '❓', label: 'Вопрос-ответ' },
    explanation: { icon: '💡', label: 'Объяснение' },
    practice: { icon: '🎯', label: 'Практика' },
    intro: { icon: '👋', label: 'Введение' },
    summary: { icon: '📋', label: 'Итоги' },
  };
  
  const typeLower = blockType.toLowerCase();
  return types[typeLower] || { icon: '📝', label: blockType };
};

// ===== SOURCE ITEM COMPONENT =====

/**
 * Individual source item with link and metadata
 */
const SourceItem: React.FC<SourceItemProps> = ({ source, compact = false }) => {
  const youtubeUrl = formatterService.formatYouTubeUrl(source.youtube_link, source.start);
  const blockInfo = getBlockTypeInfo(source.block_type);
  
  return (
    <a
      href={youtubeUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={clsx(
        'block rounded-lg transition-all duration-200',
        'bg-white dark:bg-gray-800',
        'hover:bg-gray-50 dark:hover:bg-gray-750',
        'hover:shadow-md',
        'border border-gray-200 dark:border-gray-700',
        compact ? 'p-2' : 'p-3'
      )}
    >
      {/* Title Row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <span className="text-red-500 flex-shrink-0">
            <FiPlay className="w-4 h-4" />
          </span>
          <span className={clsx(
            'font-medium text-gray-800 dark:text-gray-200 truncate',
            compact ? 'text-xs' : 'text-sm'
          )}>
            {source.title}
          </span>
        </div>
        <FiExternalLink 
          className="text-gray-400 dark:text-gray-500 flex-shrink-0" 
          size={compact ? 12 : 14} 
        />
      </div>

      {/* Metadata Row */}
      <div className={clsx(
        'flex flex-wrap items-center gap-x-3 gap-y-1 mt-2',
        compact ? 'text-[10px]' : 'text-xs',
        'text-gray-500 dark:text-gray-400'
      )}>
        {/* Time Range */}
        <span className="flex items-center gap-1">
          <FiClock className="w-3 h-3" />
          {formatTime(source.start)} — {formatTime(source.end)}
        </span>

        {/* Block Type */}
        <span className="flex items-center gap-1">
          <span>{blockInfo.icon}</span>
          {blockInfo.label}
        </span>

        {/* Complexity Score */}
        {!compact && (
          <span className={clsx('flex items-center gap-1', getComplexityColor(source.complexity_score))}>
            <FiBarChart2 className="w-3 h-3" />
            {getComplexityLabel(source.complexity_score)} ({source.complexity_score}/10)
          </span>
        )}
      </div>
    </a>
  );
};

// ===== MAIN SOURCES LIST COMPONENT =====

/**
 * Expandable list of sources
 */
export const SourcesList: React.FC<SourcesListProps> = ({
  sources,
  defaultExpanded = false,
  maxInitial = 3,
  title = '📚 Источники',
  className,
  compact = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [showAll, setShowAll] = useState(false);

  if (sources.length === 0) {
    return null;
  }

  const displayedSources = showAll ? sources : sources.slice(0, maxInitial);
  const hasMore = sources.length > maxInitial;

  return (
    <div className={clsx('border-t border-gray-200 dark:border-gray-700 pt-3 mt-3', className)}>
      {/* Header Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={clsx(
          'flex items-center gap-2 w-full text-left',
          'text-gray-600 dark:text-gray-400',
          'hover:text-gray-800 dark:hover:text-gray-200',
          'transition-colors duration-200',
          compact ? 'text-xs' : 'text-sm'
        )}
      >
        {isExpanded ? (
          <FiChevronUp className="flex-shrink-0" />
        ) : (
          <FiChevronDown className="flex-shrink-0" />
        )}
        <span className="font-medium">{title}</span>
        <span className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs">
          {sources.length}
        </span>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className={clsx('mt-3 space-y-2', compact ? 'space-y-1' : 'space-y-2')}>
          {displayedSources.map((source, idx) => (
            <SourceItem key={source.block_id || idx} source={source} compact={compact} />
          ))}

          {/* Show More Button */}
          {hasMore && !showAll && (
            <button
              onClick={() => setShowAll(true)}
              className={clsx(
                'w-full py-2 text-center text-sm',
                'text-purple-600 dark:text-purple-400',
                'hover:text-purple-700 dark:hover:text-purple-300',
                'hover:bg-purple-50 dark:hover:bg-purple-900/20',
                'rounded-lg transition-colors duration-200'
              )}
            >
              Показать ещё {sources.length - maxInitial} источников
            </button>
          )}

          {/* Show Less Button */}
          {showAll && hasMore && (
            <button
              onClick={() => setShowAll(false)}
              className={clsx(
                'w-full py-2 text-center text-sm',
                'text-gray-500 dark:text-gray-400',
                'hover:text-gray-700 dark:hover:text-gray-300',
                'hover:bg-gray-50 dark:hover:bg-gray-800',
                'rounded-lg transition-colors duration-200'
              )}
            >
              Свернуть
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// ===== INLINE SOURCES (Compact Single-Line) =====

interface InlineSourcesProps {
  sources: Source[];
  max?: number;
  className?: string;
}

/**
 * Inline compact sources display
 */
export const InlineSources: React.FC<InlineSourcesProps> = ({
  sources,
  max = 2,
  className,
}) => {
  if (sources.length === 0) return null;

  const displayed = sources.slice(0, max);
  const remaining = sources.length - max;

  return (
    <div className={clsx('flex flex-wrap items-center gap-2', className)}>
      <FiLayers className="w-3 h-3 text-gray-400" />
      {displayed.map((source, idx) => (
        <a
          key={source.block_id || idx}
          href={formatterService.formatYouTubeUrl(source.youtube_link, source.start)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-purple-600 dark:text-purple-400 hover:underline truncate max-w-[150px]"
        >
          {source.title}
        </a>
      ))}
      {remaining > 0 && (
        <span className="text-xs text-gray-400">+{remaining}</span>
      )}
    </div>
  );
};

export default SourcesList;
