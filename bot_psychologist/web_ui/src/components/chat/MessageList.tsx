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
}

export const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
    </div>
  );
};

export default MessageList;
