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
import { StateCardCompact } from '../insights/StateCard';
import { SourcesList } from '../insights/SourcesList';
import { PathBuilderCompact } from '../insights/PathBuilder';

interface MessageItemProps {
  message: Message;
  showSources?: boolean;
  showPath?: boolean;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  showSources = true,
  showPath = true,
}) => {
  const isUser = message.role === 'user';

  return (
    <div className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={clsx(
          'max-w-[85%] md:max-w-2xl rounded-2xl p-4',
          isUser
            ? 'bg-purple-600 text-white rounded-br-md'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-bl-md'
        )}
      >
        {/* Message Content */}
        <div className={clsx(
          'prose prose-sm max-w-none',
          isUser ? 'prose-invert' : 'dark:prose-invert'
        )}>
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Bot-specific content */}
        {!isUser && (
          <>
            {/* Processing Time */}
            {message.processingTime !== undefined && (
              <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mt-2">
                <FiClock size={12} />
                {formatterService.formatProcessingTime(message.processingTime)}
              </div>
            )}

            {/* State Indicator */}
            {message.state && (
              <StateCardCompact state={message.state} confidence={message.confidence} className="mt-3" />
            )}

            {/* Concepts Tags */}
            {message.concepts && message.concepts.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {message.concepts.slice(0, 5).map((concept, idx) => (
                  <span
                    key={idx}
                    className="bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 px-2 py-0.5 rounded-full text-xs"
                  >
                    {concept}
                  </span>
                ))}
                {message.concepts.length > 5 && (
                  <span className="text-xs text-gray-500">
                    +{message.concepts.length - 5}
                  </span>
                )}
              </div>
            )}

            {/* Sources */}
            {showSources && message.sources && message.sources.length > 0 && (
              <SourcesList sources={message.sources} />
            )}

            {/* Path Recommendation */}
            {showPath && message.path && (
              <div className="mt-3 border-t border-gray-200 dark:border-gray-700 pt-3">
                <h4 className="font-semibold text-sm mb-2 flex items-center gap-1">
                  🛤️ Персональный путь
                </h4>
                <PathBuilderCompact path={message.path} />
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
          isUser ? 'text-white/70' : 'text-gray-400 dark:text-gray-500'
        )}>
          {formatterService.formatMessageTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
};

export default MessageItem;


