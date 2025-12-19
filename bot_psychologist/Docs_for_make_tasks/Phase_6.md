# 📋 Phase 6: Web UI (React.js) — Полный ПРД

## Обзор Phase 6

**Phase 6** — полнофункциональный веб-интерфейс для взаимодействия с Bot Agent через REST API (Phase 5).

**Что добавляет:**
- 🎨 **React SPA** — современный интерфейс
- 💬 **Chat Interface** — красивое диалоговое окно
- 👤 **User Profile** — история, интересы, статистика
- 🛤️ **Path Visualization** — визуализация персонального пути
- 🎯 **State Indicator** — текущее состояние пользователя
- ⭐ **Feedback Widget** — оценка ответов (1-5 звезд)
- 📱 **Responsive Design** — работает на любых устройствах
- 🔗 **API Integration** — полная интеграция с Phase 5
- 📊 **Real-time Updates** — WebSocket для live обновлений
- 🎨 **Modern UI/UX** — Tailwind CSS + Custom Components

---

## 🏗️ Архитектура Phase 6

```
┌─────────────────────────────────────────────────────┐
│          Web Browser / Mobile Browser               │
├─────────────────────────────────────────────────────┤
│                React Application                     │
│  ┌───────────────────────────────────────────────┐  │
│  │  Pages/Views                                  │  │
│  │  ├─ HomePage (entry point)                   │  │
│  │  ├─ ChatPage (main interface)                │  │
│  │  ├─ ProfilePage (user stats)                 │  │
│  │  └─ SettingsPage (API key, preferences)      │  │
│  └──────────────────┬──────────────────────────┘  │
│                     │                              │
│  ┌──────────────────▼──────────────────────────┐  │
│  │  Components                                 │  │
│  │  ├─ ChatWindow (диалоговое окно)            │  │
│  │  ├─ MessageList (список сообщений)          │  │
│  │  ├─ InputBox (ввод вопроса)                 │  │
│  │  ├─ StateCard (показатель состояния)        │  │
│  │  ├─ PathBuilder (визуализация пути)         │  │
│  │  ├─ SourcesList (источники/ссылки)          │  │
│  │  └─ FeedbackWidget (оценка)                 │  │
│  └──────────────────┬──────────────────────────┘  │
│                     │                              │
│  ┌──────────────────▼──────────────────────────┐  │
│  │  Hooks & State Management                   │  │
│  │  ├─ useChat (state управления)              │  │
│  │  ├─ useAPI (интеграция с API)               │  │
│  │  ├─ useWebSocket (real-time)                │  │
│  │  └─ useTheme (dark/light mode)              │  │
│  └───────────────────────────────────────────────┘  │
│                     │                              │
│  ┌──────────────────▼──────────────────────────┐  │
│  │  Services                                   │  │
│  │  ├─ api.service.ts (API calls)              │  │
│  │  ├─ storage.service.ts (localStorage)       │  │
│  │  ├─ websocket.service.ts (WebSocket)        │  │
│  │  └─ formatter.service.ts (formatting)       │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
             ↓ HTTP/WebSocket ↓
┌─────────────────────────────────────────────────────┐
│    FastAPI Server (Phase 5) :8001                   │
│    ├─ /api/v1/questions/adaptive                    │
│    ├─ /api/v1/users/{user_id}/history              │
│    ├─ /api/v1/feedback                             │
│    └─ /api/v1/stats                                │
└─────────────────────────────────────────────────────┘
```

---

## 📂 Структура проекта React

```
web_ui/
├── public/
│   ├── index.html
│   ├── favicon.ico
│   └── manifest.json
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── Loader.tsx
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── Message.tsx
│   │   │   ├── InputBox.tsx
│   │   │   └── TypingIndicator.tsx
│   │   ├── insights/
│   │   │   ├── StateCard.tsx
│   │   │   ├── PathBuilder.tsx
│   │   │   ├── PathStep.tsx
│   │   │   └── SourcesList.tsx
│   │   ├── feedback/
│   │   │   ├── FeedbackWidget.tsx
│   │   │   └── RatingStars.tsx
│   │   └── profile/
│   │       ├── UserProfile.tsx
│   │       ├── InterestsCard.tsx
│   │       └── StatisticsCard.tsx
│   ├── pages/
│   │   ├── HomePage.tsx
│   │   ├── ChatPage.tsx
│   │   ├── ProfilePage.tsx
│   │   ├── SettingsPage.tsx
│   │   └── NotFoundPage.tsx
│   ├── hooks/
│   │   ├── useChat.ts
│   │   ├── useAPI.ts
│   │   ├── useWebSocket.ts
│   │   ├── useTheme.ts
│   │   └── useLocalStorage.ts
│   ├── services/
│   │   ├── api.service.ts
│   │   ├── storage.service.ts
│   │   ├── websocket.service.ts
│   │   └── formatter.service.ts
│   ├── types/
│   │   ├── api.types.ts
│   │   ├── chat.types.ts
│   │   └── user.types.ts
│   ├── styles/
│   │   ├── globals.css
│   │   ├── variables.css
│   │   └── animations.css
│   ├── utils/
│   │   ├── constants.ts
│   │   ├── helpers.ts
│   │   └── validators.ts
│   ├── App.tsx
│   └── main.tsx
├── .env.example
├── .env.local
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── README.md
```

---

## 🚀 Шаг 1: Инициализация React проекта

### Создание проекта с Vite

```bash
# Создать новый React проект с Vite + TypeScript
npm create vite@latest web_ui -- --template react-ts

cd web_ui

# Установить зависимости
npm install

# Установить необходимые пакеты
npm install \
  react-router-dom \
  axios \
  tailwindcss postcss autoprefixer \
  zustand \
  react-markdown \
  react-icons \
  date-fns \
  clsx \
  typescript
```

### Инициализировать Tailwind CSS

```bash
npx tailwindcss init -p
```

### Структура package.json

```json
{
  "name": "bot-psychologist-ui",
  "version": "0.6.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.18.0",
    "axios": "^1.6.2",
    "zustand": "^4.4.5",
    "react-markdown": "^9.0.1",
    "react-icons": "^4.12.0",
    "date-fns": "^2.30.0",
    "clsx": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "typescript": "^5.2.2",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.3.6",
    "postcss": "^8.4.31",
    "autoprefixer": "^10.4.16"
  }
}
```

---

## 🎨 Шаг 2: Создание типов

### Файл: `src/types/api.types.ts`

```typescript
// API Response types
export interface StateAnalysis {
  primary_state: string;
  confidence: number;
  emotional_tone: string;
  recommendations: string[];
}

export interface PathStep {
  step_number: number;
  title: string;
  duration_weeks: number;
  practices: string[];
  key_concepts: string[];
}

export interface PathRecommendation {
  current_state: string;
  target_state: string;
  key_focus: string;
  steps_count: number;
  total_duration_weeks: number;
  first_step?: PathStep;
}

export interface Source {
  block_id: string;
  title: string;
  youtube_link: string;
  start: number;
  end: number;
  block_type: string;
  complexity_score: number;
}

export interface AdaptiveAnswerResponse {
  status: string;
  answer: string;
  state_analysis: StateAnalysis;
  path_recommendation?: PathRecommendation;
  feedback_prompt: string;
  concepts: string[];
  sources: Source[];
  conversation_context: string;
  metadata: Record<string, any>;
  timestamp: string;
  processing_time_seconds: number;
}

export interface UserHistoryResponse {
  user_id: string;
  total_turns: number;
  turns: ConversationTurn[];
  primary_interests: string[];
  average_rating: number;
  last_interaction?: string;
}

export interface ConversationTurn {
  timestamp: string;
  user_input: string;
  user_state?: string;
  bot_response: string;
  blocks_used: number;
  concepts: string[];
  user_feedback?: string;
  user_rating?: number;
}

export interface FeedbackRequest {
  user_id: string;
  turn_index: number;
  feedback: 'positive' | 'negative' | 'neutral';
  rating?: number;
  comment?: string;
}
```

### Файл: `src/types/chat.types.ts`

```typescript
export interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  timestamp: Date;
  state?: string;
  confidence?: number;
  sources?: Source[];
  concepts?: string[];
  processingTime?: number;
  path?: PathRecommendation;
  feedbackPrompt?: string;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error?: string;
  currentUserState?: string;
  userLevel: 'beginner' | 'intermediate' | 'advanced';
}

export interface UserSettings {
  apiKey: string;
  userId: string;
  userLevel: 'beginner' | 'intermediate' | 'advanced';
  theme: 'light' | 'dark';
  showSources: boolean;
  showPath: boolean;
  autoScroll: boolean;
}

import { Source, PathRecommendation } from './api.types';
```

### Файл: `src/types/user.types.ts`

```typescript
export interface UserProfile {
  userId: string;
  totalQuestions: number;
  primaryInterests: string[];
  averageRating: number;
  topStates: Record<string, number>;
  lastInteraction?: Date;
}

export interface UserStats {
  totalUsers: number;
  totalQuestions: number;
  averageProcessingTime: number;
  topStates: Record<string, number>;
  topInterests: string[];
  feedbackStats: Record<string, number>;
}
```

---

## 🔌 Шаг 3: Создание API Service

### Файл: `src/services/api.service.ts`

```typescript
import axios, { AxiosInstance, AxiosError } from 'axios';
import { AdaptiveAnswerResponse, UserHistoryResponse, FeedbackRequest } from '../types/api.types';

class APIService {
  private api: AxiosInstance;
  private apiKey: string = '';

  constructor() {
    this.api = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Добавить интерцептор для API ключа
    this.api.interceptors.request.use((config) => {
      if (this.apiKey) {
        config.headers['X-API-Key'] = this.apiKey;
      }
      return config;
    });

    // Обработка ошибок
    this.api.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 403) {
          // Невалиден API ключ
          this.handleAuthError();
        }
        return Promise.reject(error);
      }
    );

    // Загрузить API ключ из localStorage
    const savedKey = localStorage.getItem('bot_api_key');
    if (savedKey) {
      this.apiKey = savedKey;
    }
  }

  setAPIKey(key: string): void {
    this.apiKey = key;
    localStorage.setItem('bot_api_key', key);
  }

  getAPIKey(): string {
    return this.apiKey;
  }

  private handleAuthError(): void {
    // Очистить API ключ и перенаправить на страницу настроек
    localStorage.removeItem('bot_api_key');
    window.location.href = '/settings';
  }

  // === QUESTION ENDPOINTS ===

  async askAdaptiveQuestion(
    query: string,
    userId: string,
    userLevel: 'beginner' | 'intermediate' | 'advanced' = 'beginner',
    includePath: boolean = true,
    includeFeedback: boolean = true
  ): Promise<AdaptiveAnswerResponse> {
    try {
      const response = await this.api.post<AdaptiveAnswerResponse>(
        '/questions/adaptive',
        {
          query,
          user_id: userId,
          user_level: userLevel,
          include_path: includePath,
          include_feedback_prompt: includeFeedback,
          debug: false,
        }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async askBasicQuestion(query: string): Promise<any> {
    try {
      const response = await this.api.post('/questions/basic', { query });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async askSagAwareQuestion(
    query: string,
    userLevel: 'beginner' | 'intermediate' | 'advanced' = 'beginner'
  ): Promise<any> {
    try {
      const response = await this.api.post('/questions/sag-aware', {
        query,
        user_level: userLevel,
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async askGraphQuestion(
    query: string,
    userLevel: 'beginner' | 'intermediate' | 'advanced' = 'beginner'
  ): Promise<any> {
    try {
      const response = await this.api.post('/questions/graph-powered', {
        query,
        user_level: userLevel,
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === USER ENDPOINTS ===

  async getUserHistory(userId: string, lastNTurns: number = 10): Promise<UserHistoryResponse> {
    try {
      const response = await this.api.post<UserHistoryResponse>(
        `/users/${userId}/history`,
        { last_n_turns: lastNTurns }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === FEEDBACK ENDPOINTS ===

  async submitFeedback(feedback: FeedbackRequest): Promise<any> {
    try {
      const response = await this.api.post('/feedback', feedback);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === STATS ENDPOINTS ===

  async getStatistics(): Promise<any> {
    try {
      const response = await this.api.get('/stats');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === HEALTH CHECK ===

  async healthCheck(): Promise<any> {
    try {
      const response = await this.api.get('/health');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === ERROR HANDLING ===

  private handleError(error: any): Error {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.detail || error.message || 'Unknown error';
      return new Error(message);
    }
    return error instanceof Error ? error : new Error('Unknown error');
  }
}

export const apiService = new APIService();
```

---

## 🪝 Шаг 4: Создание Custom Hooks

### Файл: `src/hooks/useChat.ts`

```typescript
import { useState, useCallback } from 'react';
import { Message, ChatState } from '../types/chat.types';
import { apiService } from '../services/api.service';
import { v4 as uuidv4 } from 'uuid';

export const useChat = (userId: string, userLevel: 'beginner' | 'intermediate' | 'advanced' = 'beginner') => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentUserState, setCurrentUserState] = useState<string | undefined>();

  const addMessage = useCallback((
    role: 'user' | 'bot',
    content: string,
    metadata?: Partial<Message>
  ) => {
    const message: Message = {
      id: uuidv4(),
      role,
      content,
      timestamp: new Date(),
      ...metadata,
    };
    setMessages((prev) => [...prev, message]);
    return message;
  }, []);

  const sendQuestion = useCallback(async (query: string) => {
    // Добавить сообщение пользователя
    addMessage('user', query);
    setIsLoading(true);
    setError(null);

    try {
      // Запрос к API
      const response = await apiService.askAdaptiveQuestion(
        query,
        userId,
        userLevel,
        true,
        true
      );

      // Обновить состояние пользователя
      if (response.state_analysis) {
        setCurrentUserState(response.state_analysis.primary_state);
      }

      // Добавить ответ бота
      addMessage('bot', response.answer, {
        state: response.state_analysis?.primary_state,
        confidence: response.state_analysis?.confidence,
        sources: response.sources,
        concepts: response.concepts,
        processingTime: response.processing_time_seconds,
        path: response.path_recommendation,
        feedbackPrompt: response.feedback_prompt,
      });

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get response';
      setError(errorMessage);
      addMessage('bot', `❌ Ошибка: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  }, [userId, userLevel, addMessage]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
    setCurrentUserState(undefined);
  }, []);

  return {
    messages,
    isLoading,
    error,
    currentUserState,
    sendQuestion,
    clearChat,
    addMessage,
  };
};
```

### Файл: `src/hooks/useAPI.ts`

```typescript
import { useState, useCallback } from 'react';
import { apiService } from '../services/api.service';

export const useAPI = <T,>(asyncFunction: () => Promise<T>) => {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await asyncFunction();
      setData(result);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [asyncFunction]);

  return { data, isLoading, error, execute };
};
```

### Файл: `src/hooks/useTheme.ts`

```typescript
import { useState, useEffect } from 'react';

type Theme = 'light' | 'dark';

export const useTheme = () => {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme') as Theme | null;
    return saved || 'light';
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return { theme, toggleTheme };
};
```

---

## 🎨 Шаг 5: Основные компоненты

### Файл: `src/components/chat/ChatWindow.tsx`

```typescript
import React, { useEffect, useRef } from 'react';
import { Message } from '../../types/chat.types';
import MessageItem from './Message';
import InputBox from './InputBox';
import TypingIndicator from './TypingIndicator';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
  currentUserState?: string;
}

const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  isLoading,
  onSendMessage,
  currentUserState,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-teal-500 to-teal-600 text-white p-4 shadow-md">
        <h1 className="text-2xl font-bold">Bot Psychologist</h1>
        <p className="text-sm opacity-90">Адаптивный QA с состояниями и путями</p>
        {currentUserState && (
          <p className="text-xs mt-2 bg-white bg-opacity-20 px-2 py-1 rounded w-fit">
            Состояние: <span className="font-semibold">{currentUserState}</span>
          </p>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <p className="text-lg font-semibold mb-2">👋 Добро пожаловать!</p>
              <p>Задайте вопрос, и я помогу вам на пути трансформации</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <InputBox onSendMessage={onSendMessage} isLoading={isLoading} />
    </div>
  );
};

export default ChatWindow;
```

### Файл: `src/components/chat/Message.tsx`

```typescript
import React from 'react';
import { Message } from '../../types/chat.types';
import ReactMarkdown from 'react-markdown';
import SourcesList from '../insights/SourcesList';
import StateCard from '../insights/StateCard';

interface MessageItemProps {
  message: Message;
}

const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-2xl rounded-lg p-4 ${
          isUser
            ? 'bg-teal-500 text-white rounded-br-none'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-bl-none'
        }`}
      >
        {/* Message Content */}
        <div className="prose dark:prose-invert max-w-none text-sm">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Processing Time */}
        {message.processingTime && (
          <p className="text-xs opacity-70 mt-2">
            ⏱️ {message.processingTime.toFixed(2)}s
          </p>
        )}

        {/* State Indicator */}
        {message.state && !isUser && (
          <StateCard state={message.state} confidence={message.confidence} />
        )}

        {/* Concepts */}
        {message.concepts && message.concepts.length > 0 && !isUser && (
          <div className="mt-3 flex flex-wrap gap-2">
            {message.concepts.map((concept) => (
              <span
                key={concept}
                className="bg-teal-200 dark:bg-teal-900 text-teal-900 dark:text-teal-100 px-2 py-1 rounded text-xs"
              >
                {concept}
              </span>
            ))}
          </div>
        )}

        {/* Sources */}
        {message.sources && message.sources.length > 0 && !isUser && (
          <SourcesList sources={message.sources} />
        )}

        {/* Path Recommendation */}
        {message.path && !isUser && (
          <div className="mt-4 border-t border-gray-300 dark:border-gray-700 pt-3">
            <h4 className="font-semibold text-xs mb-2">🛤️ Персональный путь:</h4>
            <p className="text-xs mb-1">
              <span className="font-semibold">{message.path.current_state}</span> →{' '}
              <span className="font-semibold">{message.path.target_state}</span>
            </p>
            <p className="text-xs">
              📍 {message.path.steps_count} шагов, {message.path.total_duration_weeks} недель
            </p>
            <p className="text-xs mt-1 italic">💡 {message.path.key_focus}</p>
          </div>
        )}

        {/* Feedback Prompt */}
        {message.feedbackPrompt && !isUser && (
          <p className="text-xs mt-3 italic opacity-80">{message.feedbackPrompt}</p>
        )}
      </div>
    </div>
  );
};

export default MessageItem;
```

### Файл: `src/components/chat/InputBox.tsx`

```typescript
import React, { useState, useRef } from 'react';
import { BiSend } from 'react-icons/bi';

interface InputBoxProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

const InputBox: React.FC<InputBoxProps> = ({ onSendMessage, isLoading }) => {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800">
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Задайте вопрос..."
          disabled={isLoading}
          className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 dark:bg-gray-700 dark:text-white disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className="bg-teal-500 hover:bg-teal-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <BiSend />
        </button>
      </div>
    </div>
  );
};

export default InputBox;
```

### Файл: `src/components/chat/TypingIndicator.tsx`

```typescript
import React from 'react';

const TypingIndicator: React.FC = () => {
  return (
    <div className="flex items-center gap-2 text-gray-400">
      <div className="flex gap-1">
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
      </div>
      <span className="text-sm">Bot печатает...</span>
    </div>
  );
};

export default TypingIndicator;
```

---

## 📊 Шаг 6: Компоненты инсайтов

### Файл: `src/components/insights/StateCard.tsx`

```typescript
import React from 'react';
import { FiTrendingUp } from 'react-icons/fi';

interface StateCardProps {
  state: string;
  confidence?: number;
}

const StateCard: React.FC<StateCardProps> = ({ state, confidence = 0 }) => {
  const getStateColor = (state: string) => {
    const colors: Record<string, string> = {
      curious: 'bg-blue-100 text-blue-900 border-blue-300',
      overwhelmed: 'bg-red-100 text-red-900 border-red-300',
      resistant: 'bg-orange-100 text-orange-900 border-orange-300',
      committed: 'bg-green-100 text-green-900 border-green-300',
      practicing: 'bg-indigo-100 text-indigo-900 border-indigo-300',
      stagnant: 'bg-yellow-100 text-yellow-900 border-yellow-300',
      breakthrough: 'bg-purple-100 text-purple-900 border-purple-300',
      integrated: 'bg-emerald-100 text-emerald-900 border-emerald-300',
      confused: 'bg-gray-100 text-gray-900 border-gray-300',
      unaware: 'bg-slate-100 text-slate-900 border-slate-300',
    };
    return colors[state] || 'bg-gray-100 text-gray-900 border-gray-300';
  };

  const getStateEmoji = (state: string) => {
    const emojis: Record<string, string> = {
      curious: '🤔',
      overwhelmed: '😰',
      resistant: '😤',
      committed: '💪',
      practicing: '🧘',
      stagnant: '🪨',
      breakthrough: '⚡',
      integrated: '🌟',
      confused: '😕',
      unaware: '🙈',
    };
    return emojis[state] || '❓';
  };

  return (
    <div className={`border-2 rounded-lg p-3 mt-3 ${getStateColor(state)}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">{getStateEmoji(state)}</span>
        <span className="font-semibold capitalize">{state}</span>
        <FiTrendingUp className="w-4 h-4 ml-auto" />
      </div>
      {confidence && (
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-white bg-opacity-50 rounded-full h-2 overflow-hidden">
            <div
              className="bg-current h-full transition-all"
              style={{ width: `${confidence * 100}%` }}
            />
          </div>
          <span className="text-xs font-semibold">{(confidence * 100).toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
};

export default StateCard;
```

### Файл: `src/components/insights/SourcesList.tsx`

```typescript
import React, { useState } from 'react';
import { Source } from '../../types/api.types';
import { FiExternalLink, FiChevronDown } from 'react-icons/fi';

interface SourcesListProps {
  sources: Source[];
}

const SourcesList: React.FC<SourcesListProps> = ({ sources }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="mt-3 border-t border-gray-300 dark:border-gray-700 pt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs font-semibold hover:opacity-80 transition-opacity"
      >
        <FiChevronDown
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        />
        📚 Источники ({sources.length})
      </button>

      {isExpanded && (
        <div className="mt-2 space-y-2">
          {sources.map((source) => (
            <div key={source.block_id} className="bg-white dark:bg-gray-700 rounded p-2">
              <a
                href={`${source.youtube_link}&t=${source.start}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1"
              >
                {source.title}
                <FiExternalLink className="w-3 h-3" />
              </a>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                ⏱️ {formatTime(source.start)} - {formatTime(source.end)} | 📊 {source.block_type}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SourcesList;
```

### Файл: `src/components/insights/PathBuilder.tsx`

```typescript
import React from 'react';
import { PathRecommendation } from '../../types/api.types';

interface PathBuilderProps {
  path: PathRecommendation;
}

const PathBuilder: React.FC<PathBuilderProps> = ({ path }) => {
  const progressPercentage = 0; // Начальный прогресс 0%

  return (
    <div className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900 dark:to-purple-900 rounded-lg p-4">
      <h3 className="font-bold text-sm mb-4 flex items-center gap-2">
        🛤️ Ваш путь трансформации
      </h3>

      {/* Current → Target */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-center flex-1">
          <p className="text-xs text-gray-500 dark:text-gray-400">Текущее состояние</p>
          <p className="font-semibold capitalize">{path.current_state}</p>
        </div>

        <div className="flex-1 mx-4">
          <div className="h-1 bg-gradient-to-r from-teal-400 to-indigo-600 rounded-full" />
        </div>

        <div className="text-center flex-1">
          <p className="text-xs text-gray-500 dark:text-gray-400">Целевое состояние</p>
          <p className="font-semibold capitalize">{path.target_state}</p>
        </div>
      </div>

      {/* Progress */}
      <div className="mb-4">
        <div className="flex justify-between text-xs mb-1">
          <span>Прогресс</span>
          <span>{progressPercentage}%</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
          <div
            className="bg-gradient-to-r from-teal-400 to-indigo-600 h-full transition-all"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Details */}
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div>
          <p className="font-semibold">{path.steps_count}</p>
          <p className="text-gray-500 dark:text-gray-400">Шагов</p>
        </div>
        <div>
          <p className="font-semibold">{path.total_duration_weeks}</p>
          <p className="text-gray-500 dark:text-gray-400">Недель</p>
        </div>
        <div>
          <p className="font-semibold">{path.key_focus.split(':')[0]}</p>
          <p className="text-gray-500 dark:text-gray-400">Фокус</p>
        </div>
      </div>

      {/* Key Focus */}
      <p className="text-xs italic mt-3 p-2 bg-white dark:bg-gray-800 rounded">
        💡 {path.key_focus}
      </p>
    </div>
  );
};

export default PathBuilder;
```

---

## 📄 Шаг 7: Главная страница

### Файл: `src/pages/ChatPage.tsx`

```typescript
import React, { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import ChatWindow from '../components/chat/ChatWindow';
import { useChat } from '../hooks/useChat';
import { apiService } from '../services/api.service';

const ChatPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const userId = searchParams.get('user_id') || `user_${Date.now()}`;
  const userLevel = (searchParams.get('level') as any) || 'beginner';

  const {
    messages,
    isLoading,
    error,
    currentUserState,
    sendQuestion,
    clearChat,
  } = useChat(userId, userLevel);

  // Проверить API ключ
  useEffect(() => {
    const apiKey = localStorage.getItem('bot_api_key');
    if (!apiKey) {
      window.location.href = '/settings';
    }
  }, []);

  return (
    <div className="h-screen flex flex-col">
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        onSendMessage={sendQuestion}
        currentUserState={currentUserState}
      />
    </div>
  );
};

export default ChatPage;
```

---

## ⚙️ Шаг 8: Страница настроек

### Файл: `src/pages/SettingsPage.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api.service';

const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const [apiKey, setApiKey] = useState('');
  const [userId, setUserId] = useState('');
  const [userLevel, setUserLevel] = useState<'beginner' | 'intermediate' | 'advanced'>('beginner');
  const [isValidating, setIsValidating] = useState(false);
  const [validationMessage, setValidationMessage] = useState('');

  useEffect(() => {
    const savedKey = localStorage.getItem('bot_api_key');
    const savedUserId = localStorage.getItem('bot_user_id');
    const savedLevel = localStorage.getItem('bot_user_level') as any;

    if (savedKey) setApiKey(savedKey);
    if (savedUserId) setUserId(savedUserId);
    if (savedLevel) setUserLevel(savedLevel);
  }, []);

  const handleValidateAndSave = async () => {
    setIsValidating(true);
    setValidationMessage('');

    try {
      // Установить API ключ
      apiService.setAPIKey(apiKey);

      // Проверить подключение
      await apiService.healthCheck();

      // Сохранить настройки
      localStorage.setItem('bot_api_key', apiKey);
      localStorage.setItem('bot_user_id', userId || `user_${Date.now()}`);
      localStorage.setItem('bot_user_level', userLevel);

      setValidationMessage('✅ Настройки сохранены! Переходим в чат...');
      setTimeout(() => {
        navigate(`/chat?user_id=${userId || `user_${Date.now()}`}&level=${userLevel}`);
      }, 1500);
    } catch (error) {
      setValidationMessage(`❌ Ошибка: ${error instanceof Error ? error.message : 'Unknown error'}`);
      apiService.setAPIKey(''); // Очистить невалиден ключ
    } finally {
      setIsValidating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 to-blue-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="max-w-md mx-auto mt-20">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h1 className="text-3xl font-bold text-center mb-6 text-teal-600">
            Bot Psychologist
          </h1>

          <div className="space-y-4">
            {/* API Key */}
            <div>
              <label className="block text-sm font-semibold mb-2">API Ключ</label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Введите API ключ..."
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 dark:bg-gray-700 dark:text-white"
              />
              <p className="text-xs text-gray-500 mt-1">
                Получить ключ можно у администратора API
              </p>
            </div>

            {/* User ID */}
            <div>
              <label className="block text-sm font-semibold mb-2">ID пользователя</label>
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="user_123 (опционально)"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 dark:bg-gray-700 dark:text-white"
              />
            </div>

            {/* User Level */}
            <div>
              <label className="block text-sm font-semibold mb-2">Уровень</label>
              <select
                value={userLevel}
                onChange={(e) => setUserLevel(e.target.value as any)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="beginner">Beginner (новичок)</option>
                <option value="intermediate">Intermediate (средний)</option>
                <option value="advanced">Advanced (продвинутый)</option>
              </select>
            </div>

            {/* Message */}
            {validationMessage && (
              <div className={`p-3 rounded text-sm ${
                validationMessage.includes('✅')
                  ? 'bg-green-100 text-green-900'
                  : 'bg-red-100 text-red-900'
              }`}>
                {validationMessage}
              </div>
            )}

            {/* Button */}
            <button
              onClick={handleValidateAndSave}
              disabled={!apiKey || isValidating}
              className="w-full bg-teal-500 hover:bg-teal-600 text-white font-semibold py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isValidating ? 'Проверка...' : 'Начать'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
```

---

## 🎯 Шаг 9: Главное приложение

### Файл: `src/App.tsx`

```typescript
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useTheme } from './hooks/useTheme';
import SettingsPage from './pages/SettingsPage';
import ChatPage from './pages/ChatPage';

const App: React.FC = () => {
  const { theme } = useTheme();

  return (
    <div className={theme === 'dark' ? 'dark' : ''}>
      <Router>
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/" element={<Navigate to="/settings" replace />} />
        </Routes>
      </Router>
    </div>
  );
};

export default App;
```

---

## 🔧 Шаг 10: Конфигурация

### Файл: `tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        teal: {
          50: '#f0fdfa',
          100: '#e0f7f4',
          200: '#ccf0f0',
          300: '#99e6e6',
          400: '#66d9d9',
          500: '#33cccc',
          600: '#209999',
          700: '#196666',
          800: '#134d4d',
          900: '#0d3333',
        },
      },
      animation: {
        bounce: 'bounce 1s infinite',
      },
    },
  },
  plugins: [],
}
```

### Файл: `.env.example`

```env
VITE_API_URL=http://localhost:8001/api/v1
VITE_WS_URL=ws://localhost:8001
```

### Файл: `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForModule": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "resolveJsonModule": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

---

## 🚀 Запуск Phase 6

```bash
cd web_ui

# Установить зависимости
npm install

# Создать .env.local
cp .env.example .env.local

# Запустить dev server
npm run dev
```

**Dev server запустится на:**
- 🌐 http://localhost:5173

---

## 📋 Phase 6 Чек-лист

- [ ] Создан проект React + TypeScript + Vite
- [ ] Установлены зависимости (Tailwind, React Router, Axios)
- [ ] Создана структура типов (API, Chat, User)
- [ ] Создан API Service с интеграцией к Phase 5
- [ ] Создано 5+ custom hooks (useChat, useAPI, useTheme)
- [ ] Созданы основные компоненты (ChatWindow, Message, StateCard, PathBuilder)
- [ ] Созданы страницы (SettingsPage, ChatPage)
- [ ] Настроен Tailwind CSS + Dark Mode
- [ ] Реализована валидация API ключа
- [ ] Dev server запущен и работает
- [ ] UI отзывчив на мобильных устройствах

---

## ✨ Возможности Phase 6 UI

### ✅ Chat Interface
- 💬 Красивое диалоговое окно
- 👤 Отличие между сообщениями пользователя и бота
- ⌨️ Удобный ввод с поддержкой Enter
- 🔄 Auto-scroll при новых сообщениях
- ⏳ Typing indicator пока бот отвечает

### ✅ Rich Message Display
- 📝 Markdown rendering для ответов
- 🎯 Показатель состояния пользователя
- ⭐ Confidence score для каждого состояния
- 🏷️ Отображение концептов (tags)
- 📚 Развертываемый список источников
- 🔗 Прямые ссылки на YouTube с временем

### ✅ Personal Path Visualization
- 🛤️ Визуальное представление пути трансформации
- 📊 Progress bar
- 📍 Информация о шагах и длительности
- 💡 Key focus для каждого пути

### ✅ User State Indicator
- 🎨 Цветное обозначение состояний (10 типов)
- 📊 Confidence score в % 
- 🔴 Emoji для каждого состояния
- 📈 Динамическое обновление

### ✅ Settings & Auth
- 🔐 Ввод и валидация API ключа
- 👤 Настройка ID и уровня пользователя
- ✅ Проверка подключения к API
- 💾 Сохранение в localStorage

### ✅ Design
- 🎨 Modern UI с Tailwind CSS
- 🌙 Dark Mode поддержка
- 📱 Полная responsive design
- ⚡ Плавные анимации и переходы
- 🎯 Accessible компоненты

---

## 🎉 ИТОГИ ПРОЕКТА

### ✅ Все 6 Phase готовы

```
Phase 1: Basic QA                    ✅
Phase 2: SAG v2.0 + User Levels      ✅
Phase 3: Knowledge Graph             ✅
Phase 4: State + Memory + Paths      ✅
Phase 5: REST API (FastAPI)          ✅
Phase 6: Web UI (React)              ⭐ (ПРД)
```

### 📊 Полная архитектура

```
React SPA (Phase 6)
    ↓ HTTP/REST
FastAPI Server (Phase 5)
    ↓
Bot Agent v0.4.0 (Phases 1-4)
    ├─ Phase 1: Basic QA (TF-IDF + LLM)
    ├─ Phase 2: SAG-aware (User Level)
    ├─ Phase 3: Graph-powered (Knowledge Graph)
    └─ Phase 4: Adaptive (State + Memory + Paths)
    ↓
Data Layer
    ├─ SAG v2.0 (12 docs, 192 blocks)
    ├─ Knowledge Graph (95 nodes, 2182 edges)
    ├─ Conversation Memory (persisted)
    └─ User Profiles
```

---

**Phase 6 ПРД готов! Следующие фазы (опционально):**
- Phase 7: Unit Tests & Integration Tests
- Phase 8: Deployment (Docker + CI/CD)
- Phase 9: Mobile App (React Native)
- Phase 10: Analytics & Monitoring
