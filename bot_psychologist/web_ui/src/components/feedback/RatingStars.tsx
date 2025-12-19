/**
 * RatingStars Component
 * 
 * Interactive 5-star rating component with hover states.
 * Supports both controlled and uncontrolled modes.
 */

import React, { useState } from 'react';
import clsx from 'clsx';
import { FiStar } from 'react-icons/fi';

// ===== TYPES =====

interface RatingStarsProps {
  /** Current rating value (1-5) */
  value?: number;
  /** Callback when rating changes */
  onChange?: (rating: number) => void;
  /** Maximum stars count */
  maxStars?: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Read-only mode (no interaction) */
  readOnly?: boolean;
  /** Show numeric rating */
  showValue?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Disabled state */
  disabled?: boolean;
}

// ===== HELPERS =====

const getSizeClasses = (size: 'sm' | 'md' | 'lg') => {
  const sizes = {
    sm: { star: 'w-4 h-4', gap: 'gap-0.5', text: 'text-xs' },
    md: { star: 'w-6 h-6', gap: 'gap-1', text: 'text-sm' },
    lg: { star: 'w-8 h-8', gap: 'gap-1.5', text: 'text-base' },
  };
  return sizes[size];
};

// ===== SINGLE STAR COMPONENT =====

interface StarProps {
  filled: boolean;
  highlighted: boolean;
  size: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  onMouseEnter?: () => void;
  disabled?: boolean;
  readOnly?: boolean;
}

const Star: React.FC<StarProps> = ({
  filled,
  highlighted,
  size,
  onClick,
  onMouseEnter,
  disabled,
  readOnly,
}) => {
  const sizeClasses = getSizeClasses(size);
  const isInteractive = !readOnly && !disabled;

  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      disabled={disabled || readOnly}
      className={clsx(
        'transition-all duration-150',
        sizeClasses.star,
        isInteractive && 'cursor-pointer hover:scale-110',
        disabled && 'cursor-not-allowed opacity-50',
        readOnly && 'cursor-default'
      )}
    >
      <FiStar
        className={clsx(
          'w-full h-full transition-colors duration-150',
          (filled || highlighted) 
            ? 'fill-yellow-400 text-yellow-400' 
            : 'fill-transparent text-gray-300 dark:text-gray-600'
        )}
      />
    </button>
  );
};

// ===== MAIN COMPONENT =====

/**
 * Interactive star rating component
 */
export const RatingStars: React.FC<RatingStarsProps> = ({
  value = 0,
  onChange,
  maxStars = 5,
  size = 'md',
  readOnly = false,
  showValue = false,
  className,
  disabled = false,
}) => {
  const [hoverValue, setHoverValue] = useState<number | null>(null);
  const sizeClasses = getSizeClasses(size);

  const handleClick = (rating: number) => {
    if (!readOnly && !disabled && onChange) {
      // Allow deselecting by clicking the same rating
      onChange(rating === value ? 0 : rating);
    }
  };

  const handleMouseEnter = (rating: number) => {
    if (!readOnly && !disabled) {
      setHoverValue(rating);
    }
  };

  const handleMouseLeave = () => {
    setHoverValue(null);
  };

  const displayValue = hoverValue ?? value;

  return (
    <div 
      className={clsx('inline-flex items-center', sizeClasses.gap, className)}
      onMouseLeave={handleMouseLeave}
    >
      {Array.from({ length: maxStars }, (_, i) => i + 1).map((rating) => (
        <Star
          key={rating}
          filled={rating <= value}
          highlighted={hoverValue !== null && rating <= hoverValue}
          size={size}
          onClick={() => handleClick(rating)}
          onMouseEnter={() => handleMouseEnter(rating)}
          disabled={disabled}
          readOnly={readOnly}
        />
      ))}
      
      {showValue && (
        <span className={clsx(
          'ml-2 font-medium text-gray-600 dark:text-gray-400',
          sizeClasses.text
        )}>
          {displayValue > 0 ? displayValue.toFixed(1) : '—'}
        </span>
      )}
    </div>
  );
};

// ===== RATING DISPLAY COMPONENT =====

interface RatingDisplayProps {
  value: number;
  maxStars?: number;
  size?: 'sm' | 'md' | 'lg';
  showCount?: boolean;
  count?: number;
  className?: string;
}

/**
 * Read-only rating display with optional count
 */
export const RatingDisplay: React.FC<RatingDisplayProps> = ({
  value,
  maxStars = 5,
  size = 'sm',
  showCount = false,
  count = 0,
  className,
}) => {
  const sizeClasses = getSizeClasses(size);
  const roundedValue = Math.round(value);

  return (
    <div className={clsx('inline-flex items-center', sizeClasses.gap, className)}>
      {Array.from({ length: maxStars }, (_, i) => i + 1).map((rating) => (
        <FiStar
          key={rating}
          className={clsx(
            sizeClasses.star,
            rating <= roundedValue 
              ? 'fill-yellow-400 text-yellow-400' 
              : 'fill-transparent text-gray-300 dark:text-gray-600'
          )}
        />
      ))}
      
      <span className={clsx(
        'ml-1 font-medium text-gray-600 dark:text-gray-400',
        sizeClasses.text
      )}>
        {value.toFixed(1)}
      </span>
      
      {showCount && count > 0 && (
        <span className={clsx(
          'text-gray-400 dark:text-gray-500',
          sizeClasses.text
        )}>
          ({count})
        </span>
      )}
    </div>
  );
};

// ===== RATING INPUT COMPONENT =====

interface RatingInputProps {
  value: number;
  onChange: (rating: number) => void;
  label?: string;
  required?: boolean;
  error?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * Rating input with label and validation
 */
export const RatingInput: React.FC<RatingInputProps> = ({
  value,
  onChange,
  label,
  required = false,
  error,
  disabled = false,
  className,
}) => {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      <RatingStars
        value={value}
        onChange={onChange}
        size="lg"
        disabled={disabled}
      />
      
      {error && (
        <p className="mt-1 text-xs text-red-500">{error}</p>
      )}
    </div>
  );
};

export default RatingStars;
