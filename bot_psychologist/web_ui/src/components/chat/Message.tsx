/**
 * Message Component
 * 
 * Individual chat message with support for markdown, sources, and insights.
 * Uses standalone insight components from ../insights for consistent UI.
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FiClock } from 'react-icons/fi';
import type { Message } from '../../types';
import { useMultiAgentTrace } from '../../hooks';
import { apiService } from '../../services/api.service';
import { formatterService } from '../../services/formatter.service';
import clsx from 'clsx';

// Import standalone insight components
import { MultiAgentTraceWidget } from './MultiAgentTraceWidget';
import type { TraceAvailability } from '../../types';

interface MessageItemProps {
  message: Message;
  sessionId?: string;
  compactMode?: boolean;
}

const TraceUnavailableNotice: React.FC<{
  availability: TraceAvailability | null;
  error: string | null;
}> = ({ availability, error }) => {
  const requestedTurn = availability?.requested_turn_index;
  const availableTurns = availability?.available_turn_indices ?? [];

  return (
    <div className="mt-3 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
      <div className="font-semibold">Trace unavailable</div>
      <div className="mt-1">
        {availability?.reason || error || 'No trace payload was found for this assistant turn.'}
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-amber-800">
        {requestedTurn !== undefined && requestedTurn !== null && (
          <span>requested turn: {requestedTurn}</span>
        )}
        {availableTurns.length > 0 && (
          <span>available turns: {availableTurns.join(', ')}</span>
        )}
        {availability?.reason_code && (
          <span>reason: {availability.reason_code}</span>
        )}
      </div>
    </div>
  );
};

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
  const {
    trace: multiagentTrace,
    availability: multiagentTraceAvailability,
    isLoading: multiagentTraceLoading,
    error: multiagentTraceError,
  } = useMultiAgentTrace(
    sessionId,
    message.id,
    message.turnNumber,
    shouldLoadMultiagentTrace
  );
  const showMultiagentTrace = Boolean(shouldLoadMultiagentTrace && (multiagentTrace || multiagentTraceLoading));
  const showTraceUnavailable = Boolean(
    shouldLoadMultiagentTrace &&
      !multiagentTrace &&
      !multiagentTraceLoading &&
      multiagentTraceAvailability?.status === 'unavailable'
  );

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
          'prose prose-sm max-w-none chat-markdown',
          !isUser && 'assistant-markdown',
          isUser ? 'text-zinc-900' : 'dark:prose-invert'
        )}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Bot-specific content */}
        {!isUser && (
          <>
            {showMultiagentTrace && (
              <MultiAgentTraceWidget trace={multiagentTrace} isLoading={multiagentTraceLoading} />
            )}
            {showTraceUnavailable && (
              <TraceUnavailableNotice
                availability={multiagentTraceAvailability}
                error={multiagentTraceError}
              />
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


