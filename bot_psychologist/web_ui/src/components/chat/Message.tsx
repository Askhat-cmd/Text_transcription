/**
 * Message Component
 * 
 * Individual chat message with support for markdown, sources, and insights.
 * Uses standalone insight components from ../insights for consistent UI.
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { FiClock } from 'react-icons/fi';
import type { Message } from '../../types';
import { formatterService } from '../../services/formatter.service';
import clsx from 'clsx';

// Import standalone insight components
import { InlineDebugTrace } from './InlineDebugTrace';

interface MessageItemProps {
  message: Message;
  compactMode?: boolean;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  compactMode = false,
}) => {
  const isUser = message.role === 'user';

  return (
    <div className="flex justify-start">
      <div
        className={clsx(
          isUser ? 'message-user' : 'message-bot',
          compactMode ? 'p-3' : 'p-4'
        )}
      >
        {/* Message Content */}
        <div className={clsx(
          'prose prose-sm max-w-none',
          isUser ? 'text-zinc-900' : 'dark:prose-invert'
        )}>
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Bot-specific content */}
        {!isUser && (
          <>
            {message.trace && (
              <InlineDebugTrace trace={message.trace} />
            )}

            {/* Processing Time */}
            {message.processingTime !== undefined && (
              <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mt-2">
                <FiClock size={12} />
                {formatterService.formatProcessingTime(message.processingTime)}
              </div>
            )}

            {/* Feedback Prompt */}
            {message.feedbackPrompt && (
              <p className="text-xs mt-3 italic text-gray-500 dark:text-gray-400">
                {message.feedbackPrompt}
              </p>
            )}
          </>
        )}

        {/* Timestamp */}
        <div className={clsx(
          'text-xs mt-2',
          isUser ? 'text-zinc-500' : 'text-gray-400 dark:text-gray-500'
        )}>
          {formatterService.formatMessageTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
};

export default MessageItem;


