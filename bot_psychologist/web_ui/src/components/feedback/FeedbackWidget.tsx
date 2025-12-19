/**
 * FeedbackWidget Component
 * 
 * Widget for collecting user feedback on bot responses.
 * Includes quick reaction buttons, star rating, and optional comment.
 */

import React, { useState, useCallback } from 'react';
import clsx from 'clsx';
import { 
  FiThumbsUp, 
  FiThumbsDown, 
  FiMinus,
  FiSend,
  FiX,
  FiCheck,
  FiMessageSquare
} from 'react-icons/fi';
import type { FeedbackType, FeedbackRequest } from '../../types';
import { apiService } from '../../services/api.service';
import { RatingStars } from './RatingStars';

// ===== TYPES =====

interface FeedbackWidgetProps {
  /** User ID for feedback submission */
  userId: string;
  /** Turn index in conversation */
  turnIndex: number;
  /** Message ID (for tracking) */
  messageId?: string;
  /** Callback after successful feedback submission */
  onSubmit?: (feedback: FeedbackRequest) => void;
  /** Compact mode (only quick buttons) */
  compact?: boolean;
  /** Show comment field */
  showComment?: boolean;
  /** Prompt text to display */
  prompt?: string;
  /** Additional CSS classes */
  className?: string;
}

type FeedbackStatus = 'idle' | 'submitting' | 'success' | 'error';

// ===== QUICK FEEDBACK BUTTON =====

interface QuickFeedbackButtonProps {
  type: FeedbackType;
  selected: boolean;
  onClick: () => void;
  disabled?: boolean;
}

const QuickFeedbackButton: React.FC<QuickFeedbackButtonProps> = ({
  type,
  selected,
  onClick,
  disabled,
}) => {
  const config: Record<FeedbackType, { icon: React.ReactNode; label: string; color: string; selectedColor: string }> = {
    positive: { 
      icon: <FiThumbsUp />, 
      label: 'Полезно',
      color: 'text-gray-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20',
      selectedColor: 'text-green-500 bg-green-100 dark:bg-green-900/30'
    },
    negative: { 
      icon: <FiThumbsDown />, 
      label: 'Не полезно',
      color: 'text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20',
      selectedColor: 'text-red-500 bg-red-100 dark:bg-red-900/30'
    },
    neutral: { 
      icon: <FiMinus />, 
      label: 'Нейтрально',
      color: 'text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700',
      selectedColor: 'text-gray-600 bg-gray-200 dark:bg-gray-700'
    },
  };

  const { icon, label, color, selectedColor } = config[type];

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-all duration-200',
        selected ? selectedColor : color,
        disabled && 'opacity-50 cursor-not-allowed'
      )}
      title={label}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
};

// ===== MAIN COMPONENT =====

/**
 * Full feedback widget with reactions, rating, and comment
 */
export const FeedbackWidget: React.FC<FeedbackWidgetProps> = ({
  userId,
  turnIndex,
  messageId: _messageId,
  onSubmit,
  compact = false,
  showComment = true,
  prompt,
  className,
}) => {
  // Note: messageId is available for future tracking purposes
  void _messageId;
  const [feedbackType, setFeedbackType] = useState<FeedbackType | null>(null);
  const [rating, setRating] = useState<number>(0);
  const [comment, setComment] = useState<string>('');
  const [status, setStatus] = useState<FeedbackStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isExpanded, setIsExpanded] = useState(false);

  const handleQuickFeedback = useCallback(async (type: FeedbackType) => {
    // Toggle selection
    const newType = feedbackType === type ? null : type;
    setFeedbackType(newType);

    // In compact mode, submit immediately on positive/negative
    if (compact && newType && newType !== 'neutral') {
      await submitFeedback(newType, 0, '');
    } else if (!compact) {
      setIsExpanded(true);
    }
  }, [feedbackType, compact]);

  const submitFeedback = async (
    type: FeedbackType,
    stars: number,
    text: string
  ) => {
    if (!type) return;

    setStatus('submitting');
    setErrorMessage('');

    const feedback: FeedbackRequest = {
      user_id: userId,
      turn_index: turnIndex,
      feedback: type,
      rating: stars > 0 ? stars : undefined,
      comment: text || undefined,
    };

    try {
      await apiService.submitFeedback(feedback);
      setStatus('success');
      onSubmit?.(feedback);
      
      // Reset after success
      setTimeout(() => {
        setIsExpanded(false);
      }, 2000);
    } catch (error) {
      setStatus('error');
      setErrorMessage(error instanceof Error ? error.message : 'Ошибка отправки');
    }
  };

  const handleSubmit = async () => {
    if (!feedbackType) return;
    await submitFeedback(feedbackType, rating, comment);
  };

  const handleCancel = () => {
    setFeedbackType(null);
    setRating(0);
    setComment('');
    setIsExpanded(false);
    setStatus('idle');
    setErrorMessage('');
  };

  // Success state
  if (status === 'success') {
    return (
      <div className={clsx(
        'flex items-center gap-2 text-green-600 dark:text-green-400 text-sm',
        className
      )}>
        <FiCheck className="w-4 h-4" />
        <span>Спасибо за отзыв!</span>
      </div>
    );
  }

  // Compact mode - just quick buttons
  if (compact) {
    return (
      <div className={clsx('flex items-center gap-2', className)}>
        {prompt && (
          <span className="text-xs text-gray-500 dark:text-gray-400 mr-2">
            {prompt}
          </span>
        )}
        <QuickFeedbackButton
          type="positive"
          selected={feedbackType === 'positive'}
          onClick={() => handleQuickFeedback('positive')}
          disabled={status === 'submitting'}
        />
        <QuickFeedbackButton
          type="negative"
          selected={feedbackType === 'negative'}
          onClick={() => handleQuickFeedback('negative')}
          disabled={status === 'submitting'}
        />
      </div>
    );
  }

  // Full mode
  return (
    <div className={clsx(
      'border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden',
      className
    )}>
      {/* Header */}
      <div className="bg-gray-50 dark:bg-gray-800 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {prompt || 'Был ли этот ответ полезен?'}
          </span>
          {isExpanded && (
            <button
              onClick={handleCancel}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <FiX className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Quick Feedback Buttons */}
      <div className="px-4 py-3">
        <div className="flex items-center gap-2">
          <QuickFeedbackButton
            type="positive"
            selected={feedbackType === 'positive'}
            onClick={() => handleQuickFeedback('positive')}
            disabled={status === 'submitting'}
          />
          <QuickFeedbackButton
            type="neutral"
            selected={feedbackType === 'neutral'}
            onClick={() => handleQuickFeedback('neutral')}
            disabled={status === 'submitting'}
          />
          <QuickFeedbackButton
            type="negative"
            selected={feedbackType === 'negative'}
            onClick={() => handleQuickFeedback('negative')}
            disabled={status === 'submitting'}
          />
        </div>
      </div>

      {/* Expanded Section */}
      {isExpanded && feedbackType && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-200 dark:border-gray-700 pt-4">
          {/* Rating */}
          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-2">
              Оцените ответ (опционально)
            </label>
            <RatingStars
              value={rating}
              onChange={setRating}
              size="lg"
            />
          </div>

          {/* Comment */}
          {showComment && (
            <div>
              <label className="block text-sm text-gray-600 dark:text-gray-400 mb-2">
                <FiMessageSquare className="inline w-4 h-4 mr-1" />
                Комментарий (опционально)
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Расскажите подробнее..."
                rows={2}
                className={clsx(
                  'w-full px-3 py-2 text-sm rounded-lg border',
                  'border-gray-300 dark:border-gray-600',
                  'bg-white dark:bg-gray-800',
                  'text-gray-900 dark:text-gray-100',
                  'placeholder-gray-400 dark:placeholder-gray-500',
                  'focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent',
                  'resize-none'
                )}
              />
            </div>
          )}

          {/* Error Message */}
          {errorMessage && (
            <p className="text-sm text-red-500">{errorMessage}</p>
          )}

          {/* Submit Button */}
          <div className="flex justify-end gap-2">
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
            >
              Отмена
            </button>
            <button
              onClick={handleSubmit}
              disabled={status === 'submitting'}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                'bg-purple-600 text-white',
                'hover:bg-purple-700',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-colors duration-200'
              )}
            >
              {status === 'submitting' ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Отправка...
                </>
              ) : (
                <>
                  <FiSend className="w-4 h-4" />
                  Отправить
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ===== INLINE FEEDBACK =====

interface InlineFeedbackProps {
  userId: string;
  turnIndex: number;
  onSubmit?: (feedback: FeedbackRequest) => void;
  className?: string;
}

/**
 * Minimal inline feedback buttons
 */
export const InlineFeedback: React.FC<InlineFeedbackProps> = ({
  userId,
  turnIndex,
  onSubmit,
  className,
}) => {
  return (
    <FeedbackWidget
      userId={userId}
      turnIndex={turnIndex}
      onSubmit={onSubmit}
      compact
      showComment={false}
      className={className}
    />
  );
};

// ===== FEEDBACK PROMPT DISPLAY =====

interface FeedbackPromptProps {
  prompt: string;
  userId: string;
  turnIndex: number;
  onSubmit?: (feedback: FeedbackRequest) => void;
  className?: string;
}

/**
 * Display feedback prompt with quick action buttons
 */
export const FeedbackPrompt: React.FC<FeedbackPromptProps> = ({
  prompt,
  userId,
  turnIndex,
  onSubmit,
  className,
}) => {
  return (
    <div className={clsx(
      'bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3',
      className
    )}>
      <p className="text-sm text-purple-700 dark:text-purple-300 italic mb-2">
        {prompt}
      </p>
      <InlineFeedback
        userId={userId}
        turnIndex={turnIndex}
        onSubmit={onSubmit}
      />
    </div>
  );
};

export default FeedbackWidget;
