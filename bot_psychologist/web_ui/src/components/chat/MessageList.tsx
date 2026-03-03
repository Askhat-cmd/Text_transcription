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
  compactMode?: boolean;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  compactMode = false,
}) => {
  return (
    <div className={compactMode ? 'space-y-2' : 'space-y-4'}>
      {messages.map((message) => (
        <MessageItem
          key={message.id}
          message={message}
          compactMode={compactMode}
        />
      ))}
    </div>
  );
};

export default MessageList;


