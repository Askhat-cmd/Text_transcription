/**
 * InterestsCard Component
 * 
 * Card displaying user's primary interests and top concepts
 * with tag-style visualization.
 */

import React, { useState } from 'react';
import clsx from 'clsx';
import { 
  FiHash, 
  FiTrendingUp, 
  FiChevronDown, 
  FiChevronUp,
  FiBookmark
} from 'react-icons/fi';

// ===== TYPES =====

interface InterestsCardProps {
  /** Primary interests list */
  primaryInterests: string[];
  /** Top concepts (optional) */
  topConcepts?: string[];
  /** Maximum interests to show initially */
  maxInitial?: number;
  /** Compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Click handler for interest tag */
  onInterestClick?: (interest: string) => void;
}

interface InterestTagProps {
  text: string;
  variant?: 'primary' | 'concept';
  onClick?: () => void;
}

// ===== SUBCOMPONENTS =====

/**
 * Individual interest/concept tag
 */
const InterestTag: React.FC<InterestTagProps> = ({ 
  text, 
  variant = 'primary',
  onClick 
}) => {
  const baseClasses = 'inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm transition-all duration-200';
  
  const variantClasses = variant === 'primary'
    ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-900/60'
    : 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-900/60';

  return (
    <button
      onClick={onClick}
      className={clsx(baseClasses, variantClasses, onClick && 'cursor-pointer')}
    >
      {variant === 'primary' ? (
        <FiHash className="w-3 h-3" />
      ) : (
        <FiBookmark className="w-3 h-3" />
      )}
      <span>{text}</span>
    </button>
  );
};

// ===== MAIN COMPONENT =====

/**
 * Card showing user interests and concepts
 */
export const InterestsCard: React.FC<InterestsCardProps> = ({
  primaryInterests,
  topConcepts = [],
  maxInitial = 6,
  compact = false,
  className,
  onInterestClick,
}) => {
  const [showAllInterests, setShowAllInterests] = useState(false);
  const [showAllConcepts, setShowAllConcepts] = useState(false);

  const hasInterests = primaryInterests.length > 0;
  const hasConcepts = topConcepts.length > 0;
  const hasContent = hasInterests || hasConcepts;

  if (!hasContent) {
    return (
      <div className={clsx(
        'bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4',
        className
      )}>
        <div className="text-center py-6 text-gray-400">
          <FiHash className="w-8 h-8 mx-auto mb-2" />
          <p className="text-sm">Пока нет данных об интересах</p>
          <p className="text-xs mt-1">Задайте несколько вопросов, чтобы выявить ваши интересы</p>
        </div>
      </div>
    );
  }

  const displayedInterests = showAllInterests 
    ? primaryInterests 
    : primaryInterests.slice(0, maxInitial);
  
  const displayedConcepts = showAllConcepts 
    ? topConcepts 
    : topConcepts.slice(0, maxInitial);

  const remainingInterests = primaryInterests.length - maxInitial;
  const remainingConcepts = topConcepts.length - maxInitial;

  if (compact) {
    return (
      <div className={clsx(
        'bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-3',
        className
      )}>
        <div className="flex flex-wrap gap-1">
          {primaryInterests.slice(0, 5).map((interest, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded-full text-xs"
            >
              {interest}
            </span>
          ))}
          {primaryInterests.length > 5 && (
            <span className="text-xs text-gray-400 py-0.5">
              +{primaryInterests.length - 5}
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
      <div className="bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
          <FiTrendingUp className="text-purple-500" />
          Ваши интересы
        </h3>
      </div>

      <div className="p-4 space-y-4">
        {/* Primary Interests */}
        {hasInterests && (
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
              <FiHash className="w-3 h-3" />
              Основные темы ({primaryInterests.length})
            </p>
            <div className="flex flex-wrap gap-2">
              {displayedInterests.map((interest, idx) => (
                <InterestTag
                  key={idx}
                  text={interest}
                  variant="primary"
                  onClick={onInterestClick ? () => onInterestClick(interest) : undefined}
                />
              ))}
            </div>
            
            {/* Show More/Less Button */}
            {remainingInterests > 0 && (
              <button
                onClick={() => setShowAllInterests(!showAllInterests)}
                className="mt-2 text-xs text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 flex items-center gap-1"
              >
                {showAllInterests ? (
                  <>
                    <FiChevronUp className="w-3 h-3" />
                    Свернуть
                  </>
                ) : (
                  <>
                    <FiChevronDown className="w-3 h-3" />
                    Показать ещё {remainingInterests}
                  </>
                )}
              </button>
            )}
          </div>
        )}

        {/* Top Concepts */}
        {hasConcepts && (
          <div className={hasInterests ? 'pt-4 border-t border-gray-200 dark:border-gray-700' : ''}>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
              <FiBookmark className="w-3 h-3" />
              Ключевые концепции ({topConcepts.length})
            </p>
            <div className="flex flex-wrap gap-2">
              {displayedConcepts.map((concept, idx) => (
                <InterestTag
                  key={idx}
                  text={concept}
                  variant="concept"
                />
              ))}
            </div>

            {/* Show More/Less Button */}
            {remainingConcepts > 0 && (
              <button
                onClick={() => setShowAllConcepts(!showAllConcepts)}
                className="mt-2 text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 flex items-center gap-1"
              >
                {showAllConcepts ? (
                  <>
                    <FiChevronUp className="w-3 h-3" />
                    Свернуть
                  </>
                ) : (
                  <>
                    <FiChevronDown className="w-3 h-3" />
                    Показать ещё {remainingConcepts}
                  </>
                )}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ===== INTERESTS INLINE =====

interface InterestsInlineProps {
  interests: string[];
  max?: number;
  className?: string;
}

/**
 * Inline interests display for compact views
 */
export const InterestsInline: React.FC<InterestsInlineProps> = ({
  interests,
  max = 3,
  className,
}) => {
  if (interests.length === 0) return null;

  const displayed = interests.slice(0, max);
  const remaining = interests.length - max;

  return (
    <div className={clsx('flex flex-wrap items-center gap-1', className)}>
      {displayed.map((interest, idx) => (
        <span
          key={idx}
          className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded-full text-xs"
        >
          {interest}
        </span>
      ))}
      {remaining > 0 && (
        <span className="text-xs text-gray-400">+{remaining}</span>
      )}
    </div>
  );
};

export default InterestsCard;


