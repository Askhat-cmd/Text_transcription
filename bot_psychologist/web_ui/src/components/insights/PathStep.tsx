/**
 * PathStep Component
 * 
 * Individual step of the transformation path with title,
 * practices, key concepts, and duration.
 */

import React, { useState } from 'react';
import clsx from 'clsx';
import { 
  FiCheck, 
  FiCircle, 
  FiClock, 
  FiChevronDown, 
  FiChevronUp,
  FiTarget,
  FiBookOpen
} from 'react-icons/fi';
import type { PathStep } from '../../types';

// ===== TYPES =====

interface PathStepCardProps {
  /** Step data from API */
  step: PathStep;
  /** Is this the currently active step */
  isActive?: boolean;
  /** Is this step completed */
  isCompleted?: boolean;
  /** Show expanded details by default */
  defaultExpanded?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Compact mode */
  compact?: boolean;
  /** Callback when step is clicked */
  onClick?: () => void;
}

interface PathStepListProps {
  steps: PathStep[];
  currentStepIndex?: number;
  onStepClick?: (index: number) => void;
  className?: string;
}

// ===== STEP INDICATOR ICON =====

interface StepIndicatorProps {
  stepNumber: number;
  isActive: boolean;
  isCompleted: boolean;
}

const StepIndicator: React.FC<StepIndicatorProps> = ({ 
  stepNumber, 
  isActive, 
  isCompleted 
}) => {
  if (isCompleted) {
    return (
      <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
        <FiCheck className="text-white w-4 h-4" />
      </div>
    );
  }

  if (isActive) {
    return (
      <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center animate-pulse">
        <span className="text-white font-bold text-sm">{stepNumber}</span>
      </div>
    );
  }

  return (
    <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
      <span className="text-gray-500 dark:text-gray-400 font-medium text-sm">{stepNumber}</span>
    </div>
  );
};

// ===== TAGS LIST =====

interface TagsListProps {
  items: string[];
  icon: React.ReactNode;
  label: string;
  color: string;
  maxShow?: number;
}

const TagsList: React.FC<TagsListProps> = ({ 
  items, 
  icon, 
  label, 
  color,
  maxShow = 5 
}) => {
  const [showAll, setShowAll] = useState(false);
  
  if (items.length === 0) return null;

  const displayed = showAll ? items : items.slice(0, maxShow);
  const remaining = items.length - maxShow;

  return (
    <div className="mt-2">
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
        {icon}
        {label}
      </p>
      <div className="flex flex-wrap gap-1">
        {displayed.map((item, idx) => (
          <span
            key={idx}
            className={clsx(
              'px-2 py-0.5 rounded-full text-xs',
              color
            )}
          >
            {item}
          </span>
        ))}
        {remaining > 0 && !showAll && (
          <button
            onClick={() => setShowAll(true)}
            className="px-2 py-0.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            +{remaining}
          </button>
        )}
      </div>
    </div>
  );
};

// ===== MAIN PATH STEP CARD =====

/**
 * Card displaying a single path step with expandable details
 */
export const PathStepCard: React.FC<PathStepCardProps> = ({
  step,
  isActive = false,
  isCompleted = false,
  defaultExpanded = false,
  className,
  compact = false,
  onClick,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded || isActive);

  const handleToggle = () => {
    if (onClick) {
      onClick();
    }
    setIsExpanded(!isExpanded);
  };

  return (
    <div
      className={clsx(
        'rounded-lg border transition-all duration-200',
        isActive 
          ? 'border-purple-400 dark:border-purple-600 bg-purple-50 dark:bg-purple-900/20 shadow-md'
          : isCompleted
            ? 'border-green-300 dark:border-green-700 bg-green-50/50 dark:bg-green-900/10'
            : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800',
        onClick && 'cursor-pointer hover:shadow-md',
        className
      )}
    >
      {/* Header (always visible) */}
      <button
        onClick={handleToggle}
        className="w-full p-3 flex items-center gap-3 text-left"
      >
        {/* Step Indicator */}
        <StepIndicator 
          stepNumber={step.step_number} 
          isActive={isActive} 
          isCompleted={isCompleted} 
        />

        {/* Title and Duration */}
        <div className="flex-1 min-w-0">
          <h4 className={clsx(
            'font-semibold truncate',
            isActive 
              ? 'text-purple-700 dark:text-purple-300' 
              : isCompleted
                ? 'text-green-700 dark:text-green-400'
                : 'text-gray-800 dark:text-gray-200',
            compact ? 'text-sm' : 'text-base'
          )}>
            {step.title}
          </h4>
          <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-0.5">
            <FiClock className="w-3 h-3" />
            {step.duration_weeks} {step.duration_weeks === 1 ? 'неделя' : step.duration_weeks < 5 ? 'недели' : 'недель'}
          </p>
        </div>

        {/* Expand/Collapse Icon */}
        {!compact && (
          <div className="text-gray-400">
            {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
          </div>
        )}
      </button>

      {/* Expanded Content */}
      {isExpanded && !compact && (
        <div className="px-3 pb-3 pt-0 border-t border-gray-100 dark:border-gray-700 mt-0">
          {/* Practices */}
          <TagsList
            items={step.practices}
            icon={<FiTarget className="w-3 h-3" />}
            label="Практики"
            color={isActive 
              ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
              : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
            }
          />

          {/* Key Concepts */}
          <TagsList
            items={step.key_concepts}
            icon={<FiBookOpen className="w-3 h-3" />}
            label="Ключевые концепции"
            color={isActive 
              ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300'
              : 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
            }
          />

          {/* Status Badge */}
          <div className="mt-3 flex items-center gap-2">
            {isCompleted && (
              <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-2 py-0.5 rounded-full">
                <FiCheck className="w-3 h-3" />
                Завершено
              </span>
            )}
            {isActive && (
              <span className="inline-flex items-center gap-1 text-xs text-purple-600 dark:text-purple-400 bg-purple-100 dark:bg-purple-900/30 px-2 py-0.5 rounded-full">
                <FiCircle className="w-3 h-3 fill-current" />
                В процессе
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// ===== PATH STEP LIST =====

/**
 * List of all path steps with timeline visualization
 */
export const PathStepList: React.FC<PathStepListProps> = ({
  steps,
  currentStepIndex = 0,
  onStepClick,
  className,
}) => {
  if (steps.length === 0) return null;

  return (
    <div className={clsx('relative', className)}>
      {/* Timeline Line */}
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700" />

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((step, idx) => (
          <div key={step.step_number || idx} className="relative">
            {/* Connector dot overlay */}
            {idx < steps.length - 1 && (
              <div 
                className={clsx(
                  'absolute left-4 top-full w-0.5 h-3 -translate-x-1/2',
                  idx < currentStepIndex 
                    ? 'bg-green-500' 
                    : 'bg-gray-200 dark:bg-gray-700'
                )} 
              />
            )}
            
            <PathStepCard
              step={step}
              isActive={idx === currentStepIndex}
              isCompleted={idx < currentStepIndex}
              onClick={onStepClick ? () => onStepClick(idx) : undefined}
              className="ml-0"
            />
          </div>
        ))}
      </div>
    </div>
  );
};

// ===== COMPACT STEP INDICATOR =====

interface PathStepCompactProps {
  step: PathStep;
  isActive?: boolean;
  isCompleted?: boolean;
}

/**
 * Compact inline step indicator
 */
export const PathStepCompact: React.FC<PathStepCompactProps> = ({
  step,
  isActive = false,
  isCompleted = false,
}) => {
  return (
    <div className={clsx(
      'flex items-center gap-2 px-2 py-1 rounded-full text-xs',
      isActive 
        ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
        : isCompleted
          ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
    )}>
      {isCompleted ? (
        <FiCheck className="w-3 h-3" />
      ) : (
        <span className="font-medium">{step.step_number}</span>
      )}
      <span className="truncate max-w-[150px]">{step.title}</span>
    </div>
  );
};

export default PathStepCard;
