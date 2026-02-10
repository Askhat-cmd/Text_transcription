/**
 * MessageList Component
 * 
 * Renders a list of chat messages.
 */

import React from 'react';
import type { Message } from '../../types';
import MessageItem from './Message';

interface MessageListProps {
  messages: Message[];
  showSources?: boolean;
  showPath?: boolean;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  showSources = true,
  showPath = true,
}) => {
  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageItem
          key={message.id}
          message={message}
          showSources={showSources}
          showPath={showPath}
        />
      ))}
    </div>
  );
};

export default MessageList;


