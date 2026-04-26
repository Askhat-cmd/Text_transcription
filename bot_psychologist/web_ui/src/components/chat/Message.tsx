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
import { useMultiAgentTrace } from '../../hooks';
import { apiService } from '../../services/api.service';
import { formatterService } from '../../services/formatter.service';
import clsx from 'clsx';

// Import standalone insight components
import { InlineDebugTrace } from './InlineDebugTrace';
import { MultiAgentTraceWidget } from './MultiAgentTraceWidget';

interface MessageItemProps {
  message: Message;
  sessionId?: string;
  compactMode?: boolean;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  sessionId,
  compactMode = false,
}) => {
  const isUser = message.role === 'user';
  const inlineTrace = message.trace ?? null;
  const isDevMode = apiService.hasDevKey();
  const hasBotTurnPattern = /-b-(\d+)$/.test(message.id);
  const isMultiagentTraceCandidate =
    Boolean((inlineTrace as Record<string, unknown> | null)?.multiagent_enabled) ||
    (inlineTrace as Record<string, unknown> | null)?.pipeline_version === 'multiagent_v1';
  const shouldLoadMultiagentTrace = Boolean(
    !isUser &&
      sessionId &&
      isDevMode &&
      (isMultiagentTraceCandidate || hasBotTurnPattern)
  );
  const { trace: multiagentTrace, isLoading: multiagentTraceLoading } = useMultiAgentTrace(
    sessionId,
    message.id,
    shouldLoadMultiagentTrace
  );
  const showLegacyInlineTrace = Boolean(inlineTrace);
  const showMultiagentTrace = Boolean(shouldLoadMultiagentTrace && (multiagentTrace || multiagentTraceLoading));

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
            {showMultiagentTrace && (
              <MultiAgentTraceWidget trace={multiagentTrace} isLoading={multiagentTraceLoading} />
            )}

            {showLegacyInlineTrace && inlineTrace && (
              <InlineDebugTrace trace={inlineTrace} />
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


