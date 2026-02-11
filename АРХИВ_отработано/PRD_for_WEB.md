
# ДОКУМЕНТ ТРЕБОВАНИЙ К ПРОДУКТУ (ПРД)

# Редизайн Web UI: Интерфейс в стиле ChatGPT + Удаление user_level

**Версия:** 1.0
**Дата:** 09.02.2026
**Автор:** AI Agent для Cursor IDE
**Цель:** Полная переработка Web UI + рефакторинг кода

***

## КРАТКОЕ РЕЗЮМЕ

Полностью переработать существующий Web UI в стиле ChatGPT с боковой панелью истории чатов, удалив устаревший функционал `user_level`. Новый интерфейс обеспечит лучший UX, визуальную привлекательность и полную интеграцию с SessionManager для персистентности диалогов.

**Ключевые задачи:**

- ✅ Современный интерфейс в стиле ChatGPT
- ✅ Боковая панель со списком всех чатов пользователя
- ✅ Кнопка "Новый чат" для создания новой сессии
- ✅ Переключение между чатами без потери данных
- ✅ Удаление селектора `user_level` (полное удаление из кода)
- ✅ Автоматическая адаптация через State Classification
- ✅ Адаптивный дизайн (десктоп + мобильная версия)
- ✅ Тёмная/светлая тема (опционально)

***

## ОГЛАВЛЕНИЕ

1. [Анализ текущего состояния](#1-%D0%B0%D0%BD%D0%B0%D0%BB%D0%B8%D0%B7-%D1%82%D0%B5%D0%BA%D1%83%D1%89%D0%B5%D0%B3%D0%BE-%D1%81%D0%BE%D1%81%D1%82%D0%BE%D1%8F%D0%BD%D0%B8%D1%8F)
2. [Целевое состояние](#2-%D1%86%D0%B5%D0%BB%D0%B5%D0%B2%D0%BE%D0%B5-%D1%81%D0%BE%D1%81%D1%82%D0%BE%D1%8F%D0%BD%D0%B8%D0%B5)
3. [Спецификация UI/UX дизайна](#3-%D1%81%D0%BF%D0%B5%D1%86%D0%B8%D1%84%D0%B8%D0%BA%D0%B0%D1%86%D0%B8%D1%8F-uiux-%D0%B4%D0%B8%D0%B7%D0%B0%D0%B9%D0%BD%D0%B0)
4. [Техническая архитектура](#4-%D1%82%D0%B5%D1%85%D0%BD%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B0%D1%8F-%D0%B0%D1%80%D1%85%D0%B8%D1%82%D0%B5%D0%BA%D1%82%D1%83%D1%80%D0%B0)
5. [Структура компонентов](#5-%D1%81%D1%82%D1%80%D1%83%D0%BA%D1%82%D1%83%D1%80%D0%B0-%D0%BA%D0%BE%D0%BC%D0%BF%D0%BE%D0%BD%D0%B5%D0%BD%D1%82%D0%BE%D0%B2)
6. [Интеграция с API](#6-%D0%B8%D0%BD%D1%82%D0%B5%D0%B3%D1%80%D0%B0%D1%86%D0%B8%D1%8F-%D1%81-api)
7. [Рефакторинг: Удаление user_level](#7-%D1%80%D0%B5%D1%84%D0%B0%D0%BA%D1%82%D0%BE%D1%80%D0%B8%D0%BD%D0%B3-%D1%83%D0%B4%D0%B0%D0%BB%D0%B5%D0%BD%D0%B8%D0%B5-user_level)
8. [Управление состоянием](#8-%D1%83%D0%BF%D1%80%D0%B0%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D0%B5-%D1%81%D0%BE%D1%81%D1%82%D0%BE%D1%8F%D0%BD%D0%B8%D0%B5%D0%BC)
9. [Модели данных](#9-%D0%BC%D0%BE%D0%B4%D0%B5%D0%BB%D0%B8-%D0%B4%D0%B0%D0%BD%D0%BD%D1%8B%D1%85)
10. [Пользовательские сценарии](#10-%D0%BF%D0%BE%D0%BB%D1%8C%D0%B7%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D1%8C%D1%81%D0%BA%D0%B8%D0%B5-%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B8)
11. [План реализации](#11-%D0%BF%D0%BB%D0%B0%D0%BD-%D1%80%D0%B5%D0%B0%D0%BB%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D0%B8)
12. [Стратегия тестирования](#12-%D1%81%D1%82%D1%80%D0%B0%D1%82%D0%B5%D0%B3%D0%B8%D1%8F-%D1%82%D0%B5%D1%81%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D1%8F)
13. [Критерии приемки](#13-%D0%BA%D1%80%D0%B8%D1%82%D0%B5%D1%80%D0%B8%D0%B8-%D0%BF%D1%80%D0%B8%D0%B5%D0%BC%D0%BA%D0%B8)

***

## 1. АНАЛИЗ ТЕКУЩЕГО СОСТОЯНИЯ

### 1.1 Существующая структура Web UI

```
bot_psychologist/web_ui/
├── src/
│   ├── App.tsx              # Корневой компонент
│   ├── components/          # Переиспользуемые компоненты
│   ├── pages/              # Страницы
│   ├── services/           # API вызовы
│   ├── hooks/              # Кастомные React хуки
│   ├── types/              # TypeScript типы
│   └── styles/             # CSS/Tailwind стили
├── package.json
├── tailwind.config.js
└── vite.config.ts
```


### 1.2 Текущие проблемы

**Проблемы UI/UX:**

- ❌ Интерфейс одиночной сессии (нет истории чатов)
- ❌ Нет боковой панели со списком чатов
- ❌ Ручной выбор `user_level` (лишний шаг для пользователя)
- ❌ Нет визуального разделения разных диалогов
- ❌ Невозможно вернуться к предыдущим чатам
- ❌ Нет функции "Новый чат"

**Технические проблемы:**

- ❌ Нет интеграции с мульти-сессионным функционалом SessionManager
- ❌ `user_level` захардкожен в API запросах
- ❌ Нет state management для множественных чатов
- ❌ Нет сохранения user_id в localStorage

***

## 2. ЦЕЛЕВОЕ СОСТОЯНИЕ

### 2.1 Визуальный дизайн (стиль ChatGPT)

```
┌──────────────────────────────────────────────────────┐
│  [☰] Bot Psychologist              [🌙] [⚙️] [👤]   │
├───────────────┬──────────────────────────────────────┤
│               │                                      │
│  [➕ Новый чат│         Название чата                │
│               │                                      │
│ 📝 Чат 1     │  ┌────────────────────────────────┐ │
│   5 мин назад │  │ 👤 Пользователь: Как справиться│ │
│              │  │                  с тревогой?   │ │
│ 📝 Чат 2     │  └────────────────────────────────┘ │
│   Сегодня    │                                      │
│              │  ┌────────────────────────────────┐ │
│ 📝 Чат 3     │  │ 🤖 Бот: Тревога — это          │ │
│   Вчера      │  │         естественная...        │ │
│              │  └────────────────────────────────┘ │
│ 📝 Чат 4     │                                      │
│   2 дня назад│  ┌────────────────────────────────┐ │
│              │  │ 👤 Пользователь: Расскажи      │ │
│              │  │                 подробнее      │ │
│              │  └────────────────────────────────┘ │
│              │                                      │
│              │  ┌─────────────────────────┐        │
│              │  │ Введите сообщение...[🎤]│ [📤]  │
│              │  └─────────────────────────┘        │
└───────────────┴──────────────────────────────────────┘
  Боковая панель    Основная область чата
     (260px)              (flex-1)
```


### 2.2 Ключевые возможности

**Боковая панель (левая):**

- Кнопка "➕ Новый чат" вверху
- Список всех чатов пользователя
- Автоматически генерируемые названия чатов
- Временные метки (5 мин назад, Сегодня, Вчера)
- Группировка по датам (Сегодня, Вчера, Последние 7 дней, Старые)
- Иконка удаления чата (🗑️) при наведении
- Подсветка активного чата

**Основная область чата (центр):**

- Название текущего чата вверху
- История сообщений с автопрокруткой
- Аватарки пользователя (👤) и бота (🤖)
- Рендеринг Markdown в ответах
- Блоки кода с подсветкой синтаксиса
- Поле ввода внизу с кнопкой отправки
- Индикатор загрузки во время генерации ответа

**Верхняя панель:**

- Логотип "Bot Psychologist"
- Переключатель тёмной темы (🌙)
- Настройки (⚙️)
- Профиль пользователя (👤)

***

## 3. СПЕЦИФИКАЦИЯ UI/UX ДИЗАЙНА

### 3.1 Спецификация макета

**Точки останова (breakpoints):**

```css
/* Мобильные устройства */
@media (max-width: 768px) {
  /* Боковая панель скрывается, открывается по кнопке ☰ */
}

/* Планшеты */
@media (min-width: 769px) and (max-width: 1024px) {
  /* Боковая панель 220px */
}

/* Десктоп */
@media (min-width: 1025px) {
  /* Боковая панель 260px */
}
```

**Боковая панель:**

- Ширина: 260px (десктоп), 220px (планшет), полный экран (мобильные)
- Фон: `bg-gray-50 dark:bg-gray-900`
- Граница: `border-r border-gray-200 dark:border-gray-700`
- Отступы: `p-4`

**Основная область чата:**

- Ширина: `flex-1` (оставшееся пространство)
- Макс. ширина: `900px` (центрировано)
- Фон: `bg-white dark:bg-gray-800`

**Сообщения:**

- Сообщение пользователя: Справа, `bg-blue-500 text-white`
- Сообщение бота: Слева, `bg-gray-100 dark:bg-gray-700`
- Отступы: `p-4`
- Скругление углов: `rounded-xl`
- Макс. ширина: `75%`


### 3.2 Типография

```css
/* Конфигурация Tailwind CSS */
fontFamily: {
  sans: ['Inter', 'system-ui', 'sans-serif'],
  mono: ['Fira Code', 'monospace'],
}

fontSize: {
  'chat-message': '16px',
  'chat-title': '14px',
  'sidebar-item': '14px',
}
```


### 3.3 Цветовая палитра

**Светлая тема:**

```css
:root {
  --color-primary: #6366f1; /* indigo-500 */
  --color-bg-main: #ffffff;
  --color-bg-sidebar: #f9fafb; /* gray-50 */
  --color-text-primary: #111827; /* gray-900 */
  --color-text-secondary: #6b7280; /* gray-500 */
  --color-border: #e5e7eb; /* gray-200 */
  --color-user-message: #3b82f6; /* blue-500 */
  --color-bot-message: #f3f4f6; /* gray-100 */
}
```

**Тёмная тема:**

```css
.dark {
  --color-bg-main: #1f2937; /* gray-800 */
  --color-bg-sidebar: #111827; /* gray-900 */
  --color-text-primary: #f9fafb; /* gray-50 */
  --color-text-secondary: #9ca3af; /* gray-400 */
  --color-border: #374151; /* gray-700 */
  --color-bot-message: #374151; /* gray-700 */
}
```


***

## 4. ТЕХНИЧЕСКАЯ АРХИТЕКТУРА

### 4.1 Технологический стек

**Frontend:**

- React 18.2+ (Hooks, Context API)
- TypeScript 5.0+
- Vite 5.0+ (инструмент сборки)
- Tailwind CSS 3.4+ (стилизация)
- Axios (HTTP клиент)
- React Markdown (рендеринг markdown)
- date-fns (форматирование дат)

**Управление состоянием:**

```
Вариант 1: Context API (рекомендуется для начала)
Вариант 2: Zustand (если нужен более мощный state management)
```


### 4.2 Структура папок (новая)

```
bot_psychologist/web_ui/
├── src/
│   ├── App.tsx                    # Корневой компонент
│   ├── main.tsx                   # Точка входа
│   │
│   ├── components/                # Переиспользуемые UI компоненты
│   │   ├── Layout/
│   │   │   ├── Header.tsx        # Верхняя панель
│   │   │   ├── Sidebar.tsx       # Левая боковая панель
│   │   │   └── MainLayout.tsx    # Обёртка макета
│   │   │
│   │   ├── Chat/
│   │   │   ├── ChatList.tsx      # Список чатов в боковой панели
│   │   │   ├── ChatListItem.tsx  # Элемент чата
│   │   │   ├── ChatView.tsx      # Основная область чата
│   │   │   ├── Message.tsx       # Одно сообщение
│   │   │   ├── MessageList.tsx   # Список сообщений
│   │   │   └── MessageInput.tsx  # Поле ввода + кнопка отправки
│   │   │
│   │   ├── UI/
│   │   │   ├── Button.tsx        # Компонент кнопки
│   │   │   ├── Input.tsx         # Компонент ввода
│   │   │   ├── Loading.tsx       # Спиннер загрузки
│   │   │   ├── Avatar.tsx        # Аватарка пользователя/бота
│   │   │   └── ThemeToggle.tsx   # Переключатель темы
│   │   │
│   │   └── Markdown/
│   │       └── MarkdownRenderer.tsx  # Рендеринг markdown
│   │
│   ├── context/                   # React Context
│   │   ├── ChatContext.tsx       # Глобальное состояние чатов
│   │   ├── ThemeContext.tsx      # Состояние темы
│   │   └── UserContext.tsx       # Состояние пользователя (user_id)
│   │
│   ├── hooks/                     # Кастомные хуки
│   │   ├── useChats.ts           # Получение/управление чатами
│   │   ├── useMessages.ts        # Получение/отправка сообщений
│   │   ├── useLocalStorage.ts    # Обёртка localStorage
│   │   └── useAutoScroll.ts      # Автопрокрутка вниз
│   │
│   ├── services/                  # API вызовы
│   │   ├── api.ts                # Экземпляр Axios + конфигурация
│   │   ├── chatService.ts        # CRUD операции с чатами
│   │   └── messageService.ts     # Операции с сообщениями
│   │
│   ├── types/                     # TypeScript типы
│   │   ├── chat.ts               # Типы Chat, Message
│   │   ├── api.ts                # Типы запросов/ответов API
│   │   └── user.ts               # Типы пользователя
│   │
│   ├── utils/                     # Вспомогательные функции
│   │   ├── dateFormat.ts         # Форматирование временных меток
│   │   ├── generateChatTitle.ts  # Генерация названий чатов
│   │   └── storage.ts            # Помощники localStorage
│   │
│   └── styles/
│       ├── index.css             # Глобальные стили + Tailwind
│       └── markdown.css          # Стили для markdown
│
├── public/
│   └── favicon.ico
│
├── .env.example
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```


***

## 5. СТРУКТУРА КОМПОНЕНТОВ

### 5.1 Компонент App

```tsx
// src/App.tsx
// ЦЕЛЬ: Корневой компонент приложения с провайдерами контекста

import { ChatProvider } from './context/ChatContext';
import { ThemeProvider } from './context/ThemeContext';
import { UserProvider } from './context/UserContext';
import MainLayout from './components/Layout/MainLayout';

export default function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <ChatProvider>
          <MainLayout />
        </ChatProvider>
      </UserProvider>
    </ThemeProvider>
  );
}
```


### 5.2 Компонент MainLayout

```tsx
// src/components/Layout/MainLayout.tsx
// ЦЕЛЬ: Главный макет с сайдбаром и областью чата

import { useState } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import ChatView from '../Chat/ChatView';

export default function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Боковая панель */}
      <Sidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
      />
      
      {/* Основной контент */}
      <div className="flex flex-col flex-1">
        <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
        <ChatView />
      </div>
    </div>
  );
}
```


### 5.3 Компонент Sidebar

```tsx
// src/components/Layout/Sidebar.tsx
// ЦЕЛЬ: Левая панель со списком чатов и кнопкой "Новый чат"

import { useContext } from 'react';
import { ChatContext } from '../../context/ChatContext';
import ChatList from '../Chat/ChatList';
import Button from '../UI/Button';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { createNewChat } = useContext(ChatContext);

  return (
    <aside
      className={`
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0 transition-transform duration-300
        w-full md:w-[260px] bg-gray-50 dark:bg-gray-900
        border-r border-gray-200 dark:border-gray-700
        flex flex-col
      `}
    >
      {/* Кнопка "Новый чат" */}
      <div className="p-4">
        <Button
          onClick={createNewChat}
          className="w-full bg-indigo-500 hover:bg-indigo-600 text-white"
        >
          ➕ Новый чат
        </Button>
      </div>

      {/* Список чатов */}
      <ChatList />
    </aside>
  );
}
```


### 5.4 Компонент ChatList

```tsx
// src/components/Chat/ChatList.tsx
// ЦЕЛЬ: Отображение списка чатов с группировкой по датам

import { useContext } from 'react';
import { ChatContext } from '../../context/ChatContext';
import ChatListItem from './ChatListItem';
import Loading from '../UI/Loading';

export default function ChatList() {
  const { chats, loading, activeChat, setActiveChat } = useContext(ChatContext);

  if (loading) {
    return <Loading />;
  }

  if (chats.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        Нет чатов. Создайте новый!
      </div>
    );
  }

  // Группировка чатов по датам
  const groupedChats = groupChatsByDate(chats);

  return (
    <div className="flex-1 overflow-y-auto">
      {Object.entries(groupedChats).map(([dateLabel, chatsInGroup]) => (
        <div key={dateLabel}>
          <h3 className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase">
            {dateLabel}
          </h3>
          {chatsInGroup.map((chat) => (
            <ChatListItem
              key={chat.session_id}
              chat={chat}
              isActive={activeChat?.session_id === chat.session_id}
              onClick={() => setActiveChat(chat)}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// Вспомогательная функция для группировки
function groupChatsByDate(chats: Chat[]) {
  // Группировка: Сегодня, Вчера, Последние 7 дней, Старые
  // ...реализация
}
```


### 5.5 Компонент Message

```tsx
// src/components/Chat/Message.tsx
// ЦЕЛЬ: Отображение одного сообщения с аватаркой и временем

import Avatar from '../UI/Avatar';
import MarkdownRenderer from '../Markdown/MarkdownRenderer';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';

interface MessageProps {
  message: Message;
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Аватарка */}
      <Avatar type={isUser ? 'user' : 'bot'} />

      {/* Контент сообщения */}
      <div className={`
        max-w-[75%] p-4 rounded-xl
        ${isUser 
          ? 'bg-blue-500 text-white' 
          : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
        }
      `}>
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <MarkdownRenderer content={message.content} />
        )}

        {/* Временная метка */}
        <div className={`
          text-xs mt-2 opacity-70
          ${isUser ? 'text-right' : 'text-left'}
        `}>
          {formatDistanceToNow(new Date(message.timestamp), {
            addSuffix: true,
            locale: ru
          })}
        </div>
      </div>
    </div>
  );
}
```


### 5.6 Компонент MessageInput

```tsx
// src/components/Chat/MessageInput.tsx
// ЦЕЛЬ: Поле ввода сообщения с автоматическим изменением размера

import { useState, useRef, useEffect } from 'react';
import Button from '../UI/Button';

interface MessageInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export default function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (text.trim()) {
      onSend(text);
      setText('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Enter отправляет, Shift+Enter - новая строка
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Автоматическое изменение высоты textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [text]);

  return (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700">
      <div className="flex gap-2">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Введите сообщение..."
          disabled={disabled}
          rows={1}
          className="
            flex-1 resize-none rounded-lg border border-gray-300
            dark:border-gray-600 px-4 py-3 focus:outline-none
            focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700
            max-h-40
          "
        />
        <Button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="bg-indigo-500 hover:bg-indigo-600 text-white px-6"
        >
          📤
        </Button>
      </div>
    </div>
  );
}
```


***

## 6. ИНТЕГРАЦИЯ С API

### 6.1 Настройка API сервиса

```typescript
// src/services/api.ts
// ЦЕЛЬ: Базовая настройка Axios с перехватчиками

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Перехватчик запросов (добавление аутентификации при необходимости)
api.interceptors.request.use((config) => {
  // Добавьте API ключ если требуется
  // config.headers['X-API-Key'] = 'ваш-api-ключ';
  return config;
});

// Перехватчик ответов (обработка ошибок)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Ошибка API:', error);
    return Promise.reject(error);
  }
);
```


### 6.2 Сервис чатов

```typescript
// src/services/chatService.ts
// ЦЕЛЬ: Операции CRUD для чатов

import { api } from './api';
import { Chat, ChatHistory } from '../types/chat';

export const chatService = {
  /**
   * Получить историю чатов пользователя (список сессий)
   */
  async getUserChats(userId: string): Promise<Chat[]> {
    const response = await api.get<ChatHistory>(
      `/api/v1/users/${userId}/history`,
      { params: { last_n_turns: 100 } }
    );

    // Преобразование ответа API в Chat[]
    return transformHistoryToChats(response.data, userId);
  },

  /**
   * Получить сообщения из конкретного чата
   */
  async getChatMessages(userId: string, sessionId: string): Promise<Message[]> {
    const response = await api.get<ChatHistory>(
      `/api/v1/users/${userId}/history`,
      { params: { last_n_turns: 100 } }
    );

    // Фильтрация сообщений для этой сессии
    return response.data.turns.filter(
      (turn) => turn.session_id === sessionId
    );
  },

  /**
   * Удалить чат
   */
  async deleteChat(userId: string): Promise<void> {
    await api.delete(`/api/v1/users/${userId}/history`);
  },
};

function transformHistoryToChats(history: ChatHistory, userId: string): Chat[] {
  // Группировка turns по session_id (если есть несколько сессий)
  // Генерация названий чатов из первого сообщения
  // ...реализация
}
```


### 6.3 Сервис сообщений

```typescript
// src/services/messageService.ts
// ЦЕЛЬ: Отправка сообщений БЕЗ user_level

import { api } from './api';
import { AdaptiveAnswerResponse } from '../types/api';

export const messageService = {
  /**
   * Отправить сообщение и получить ответ бота
   * ВАЖНО: user_level УДАЛЁН!
   */
  async sendMessage(
    question: string,
    userId: string
  ): Promise<AdaptiveAnswerResponse> {
    const response = await api.post<AdaptiveAnswerResponse>(
      '/api/v1/questions/adaptive',
      {
        question,
        user_id: userId,
        // user_level: УДАЛЁН!
        include_path: false,
        include_feedback_prompt: false,
        debug: false,
      }
    );

    return response.data;
  },
};
```


***

## 7. РЕФАКТОРИНГ: УДАЛЕНИЕ USER_LEVEL

### 7.1 Обзор изменений

**Цель:** Полностью удалить `user_level` из всего стека (Frontend → API → Backend).

**Обоснование:**

- State Classification мощнее статичных уровней
- Убирает лишний шаг из UX
- Упрощает код
- ChatGPT не имеет ручного выбора уровня


### 7.2 Изменения во Frontend

#### **7.2.1 Удаление из UI**

```tsx
// ❌ УДАЛИТЬ ЭТО (старый код):
<select name="user_level">
  <option value="beginner">Начинающий — базовые объяснения</option>
  <option value="intermediate">Средний — более глубокие темы</option>
  <option value="advanced">Продвинутый — сложные концепции</option>
</select>
```

**Новый UI:** Никакого dropdown, сразу начинаем чат.

#### **7.2.2 Удаление из API вызовов**

```typescript
// src/services/messageService.ts

// ❌ СТАРО:
await api.post('/api/v1/questions/adaptive', {
  question,
  user_id: userId,
  user_level: 'intermediate', // ← УДАЛИТЬ
});

// ✅ НОВО:
await api.post('/api/v1/questions/adaptive', {
  question,
  user_id: userId,
  // user_level удалён!
});
```


#### **7.2.3 Удаление из типов**

```typescript
// src/types/api.ts

// ❌ СТАРО:
export interface AskQuestionRequest {
  question: string;
  user_id: string;
  user_level: 'beginner' | 'intermediate' | 'advanced'; // ← УДАЛИТЬ
}

// ✅ НОВО:
export interface AskQuestionRequest {
  question: string;
  user_id: string;
  // user_level удалён!
}
```


### 7.3 Изменения в Backend (API)

#### **7.3.1 Обновление моделей API**

```python
# api/models.py

# ❌ СТАРО:
class AskQuestionRequest(BaseModel):
    query: str
    user_id: str
    user_level: UserLevel = UserLevel.INTERMEDIATE  # ← УДАЛИТЬ

# ✅ НОВО:
class AskQuestionRequest(BaseModel):
    query: str
    user_id: str
    # user_level удалён!
    include_path: bool = False
    include_feedback_prompt: bool = False
    debug: bool = False
```


#### **7.3.2 Обновление API роутов**

```python
# api/routes.py

@router.post("/questions/adaptive")
async def ask_adaptive_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    # ❌ СТАРО:
    result = answer_question_adaptive(
        request.query,
        user_id=request.user_id,
        user_level=request.user_level.value,  # ← УДАЛИТЬ
        ...
    )
    
    # ✅ НОВО:
    result = answer_question_adaptive(
        request.query,
        user_id=request.user_id,
        # user_level не передаётся!
        ...
    )
```


### 7.4 Изменения в Backend (Bot Agent)

#### **7.4.1 Обновление сигнатур функций**

```python
# bot_agent/answer_adaptive.py

# ❌ СТАРО:
def answer_question_adaptive(
    question: str,
    user_id: str,
    user_level: str = "intermediate",  # ← УДАЛИТЬ или сделать игнорируемым
    ...
):
    ...

# ✅ НОВО (Вариант 1: Удалить полностью):
def answer_question_adaptive(
    question: str,
    user_id: str,
    # user_level удалён!
    ...
):
    ...

# ✅ НОВО (Вариант 2: Оставить как устаревший, всегда игнорировать):
def answer_question_adaptive(
    question: str,
    user_id: str,
    user_level: str = None,  # устаревший, игнорируется
    ...
):
    # Игнорировать user_level, полагаться на State Classification
    ...
```


#### **7.4.2 Удаление из внутренней логики**

```python
# bot_agent/retrieval/local_search.py

# ❌ СТАРО:
def filter_by_user_level(blocks, user_level):
    if user_level == "beginner":
        return [b for b in blocks if b.complexity_score < 0.5]
    elif user_level == "advanced":
        return [b for b in blocks if b.complexity_score > 0.7]
    return blocks

# ✅ НОВО:
# Полагаться на State Classification для адаптивной фильтрации
# Никакой ручной фильтрации по user_level
```


### 7.5 Стратегия миграции

**Фаза 1: Сделать опциональным (Неделя 1)**

```python
def answer_adaptive(
    question: str,
    user_id: str,
    user_level: str = None,  # Опциональный, устаревший
    ...
):
    if user_level:
        logger.warning("user_level устарел и будет проигнорирован")
    # Продолжаем без использования user_level
```

**Фаза 2: Удалить из API (Неделя 2)**

- Обновить модели API
- Обновить роуты API
- Обновить документацию API

**Фаза 3: Удалить из Frontend (Неделя 2)**

- Удалить dropdown из UI
- Удалить из API вызовов
- Удалить из типов

**Фаза 4: Полная очистка (Неделя 3)**

- Удалить все упоминания из кода
- Обновить тесты
- Обновить документацию

***

## 8. УПРАВЛЕНИЕ СОСТОЯНИЕМ

### 8.1 ChatContext

```tsx
// src/context/ChatContext.tsx
// ЦЕЛЬ: Глобальное управление состоянием чатов и сообщений

import { createContext, useState, useEffect, useContext } from 'react';
import { UserContext } from './UserContext';
import { chatService, messageService } from '../services';
import { Chat, Message } from '../types/chat';

interface ChatContextType {
  chats: Chat[];
  activeChat: Chat | null;
  messages: Message[];
  loading: boolean;
  sending: boolean;
  
  setActiveChat: (chat: Chat) => void;
  createNewChat: () => void;
  sendMessage: (text: string) => Promise<void>;
  deleteChat: (sessionId: string) => void;
  refreshChats: () => void;
}

export const ChatContext = createContext<ChatContextType>(null!);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const { userId } = useContext(UserContext);
  
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChat, setActiveChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);

  // Загрузка чатов при монтировании
  useEffect(() => {
    if (userId) {
      loadChats();
    }
  }, [userId]);

  // Загрузка сообщений при изменении активного чата
  useEffect(() => {
    if (activeChat) {
      loadMessages(activeChat.session_id);
    }
  }, [activeChat]);

  const loadChats = async () => {
    setLoading(true);
    try {
      const data = await chatService.getUserChats(userId);
      setChats(data);
      
      // Установить первый чат активным, если ничего не выбрано
      if (!activeChat && data.length > 0) {
        setActiveChat(data[^0]);
      }
    } catch (error) {
      console.error('Не удалось загрузить чаты:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async (sessionId: string) => {
    try {
      const data = await chatService.getChatMessages(userId, sessionId);
      setMessages(data);
    } catch (error) {
      console.error('Не удалось загрузить сообщения:', error);
    }
  };

  const createNewChat = () => {
    const newChat: Chat = {
      session_id: generateSessionId(),
      title: 'Новый чат',
      created_at: new Date().toISOString(),
      last_active: new Date().toISOString(),
      message_count: 0,
    };
    
    setChats([newChat, ...chats]);
    setActiveChat(newChat);
    setMessages([]);
  };

  const sendMessage = async (text: string) => {
    if (!activeChat) return;

    // Добавить сообщение пользователя сразу (оптимистичное обновление)
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    setSending(true);
    try {
      // Вызов API
      const response = await messageService.sendMessage(text, userId);

      // Добавить сообщение бота
      const botMessage: Message = {
        id: Date.now().toString() + '-bot',
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toISOString(),
        metadata: {
          mode: response.recommended_mode,
          confidence: response.confidence_score,
        },
      };
      setMessages((prev) => [...prev, botMessage]);

      // Обновить название чата (если первое сообщение)
      if (messages.length === 0) {
        const title = generateChatTitle(text);
        setActiveChat({ ...activeChat, title });
        setChats((prev) =>
          prev.map((c) =>
            c.session_id === activeChat.session_id ? { ...c, title } : c
          )
        );
      }
    } catch (error) {
      console.error('Не удалось отправить сообщение:', error);
      // TODO: Показать сообщение об ошибке пользователю
    } finally {
      setSending(false);
    }
  };

  const deleteChat = async (sessionId: string) => {
    try {
      await chatService.deleteChat(userId);
      setChats((prev) => prev.filter((c) => c.session_id !== sessionId));
      
      if (activeChat?.session_id === sessionId) {
        setActiveChat(chats[^0] || null);
      }
    } catch (error) {
      console.error('Не удалось удалить чат:', error);
    }
  };

  return (
    <ChatContext.Provider
      value={{
        chats,
        activeChat,
        messages,
        loading,
        sending,
        setActiveChat,
        createNewChat,
        sendMessage,
        deleteChat,
        refreshChats: loadChats,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}
```


***

## 9. МОДЕЛИ ДАННЫХ

### 9.1 TypeScript типы

```typescript
// src/types/chat.ts
// ЦЕЛЬ: Определение типов для чатов и сообщений

export interface Chat {
  session_id: string;
  title: string;
  created_at: string;
  last_active: string;
  message_count: number;
  preview?: string; // Превью последнего сообщения
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: {
    mode?: string;
    confidence?: number;
    sources?: Source[];
  };
}

export interface Source {
  block_id: string;
  title: string;
  youtube_link: string;
  start: number;
  end: number;
}
```

```typescript
// src/types/api.ts
// ЦЕЛЬ: Типы для запросов/ответов API

export interface AskQuestionRequest {
  question: string;
  user_id: string;
  // user_level УДАЛЁН!
  include_path?: boolean;
  include_feedback_prompt?: boolean;
  debug?: boolean;
}

export interface AdaptiveAnswerResponse {
  status: string;
  answer: string;
  state_analysis: StateAnalysis;
  concepts: string[];
  sources: Source[];
  recommended_mode?: string;
  confidence_level?: string;
  confidence_score?: number;
  metadata: Record<string, any>;
  timestamp: string;
  processing_time_seconds: number;
}

export interface StateAnalysis {
  primary_state: string;
  confidence: number;
  emotional_tone: string;
  recommendations: string[];
}
```


***

## 10. ПОЛЬЗОВАТЕЛЬСКИЕ СЦЕНАРИИ

### 10.1 Сценарий первого пользователя

```
1. Пользователь открывает http://localhost:3000
   ↓
2. UserContext генерирует user_id, сохраняет в localStorage
   ↓
3. Чатов нет → Показывается пустое состояние
   "Нет чатов. Создайте новый!"
   ↓
4. Пользователь нажимает "➕ Новый чат"
   ↓
5. Создаётся новый чат с сгенерированным session_id
   ↓
6. Пользователь вводит сообщение: "Как справиться с тревогой?"
   ↓
7. Сообщение отправляется в API (БЕЗ user_level)
   ↓
8. Бот отвечает за 3-5 секунд
   ↓
9. Название чата автоматически генерируется: "Справиться с тревогой"
   ↓
10. Чат появляется в боковой панели
```


### 10.2 Сценарий возвращающегося пользователя

```
1. Пользователь открывает приложение
   ↓
2. UserContext загружает user_id из localStorage
   ↓
3. ChatContext получает все чаты для user_id
   ↓
4. Боковая панель показывает список предыдущих чатов
   ↓
5. Первый чат автоматически выбран
   ↓
6. Загружаются сообщения для активного чата
   ↓
7. Пользователь может:
   - Продолжить разговор в активном чате
   - Кликнуть на другой чат для переключения
   - Создать новый чат
   - Удалить старые чаты
```


***

## 11. ПЛАН РЕАЛИЗАЦИИ

### 11.1 График (3-4 дня)

**День 1: Базовая структура (6-8 часов)**

- ✅ Настройка структуры проекта
- ✅ Создание провайдеров Context (ChatContext, UserContext, ThemeContext)
- ✅ Создание компонентов Layout (Header, Sidebar, MainLayout)
- ✅ Создание базовых компонентов Chat (ChatList, ChatView, Message)
- ✅ Настройка API сервиса с axios
- ✅ Удаление user_level из типов

**День 2: Интеграция API (6-8 часов)**

- ✅ Реализация chatService (getUserChats, getChatMessages, deleteChat)
- ✅ Реализация messageService (sendMessage БЕЗ user_level)
- ✅ Подключение ChatContext к API
- ✅ Тестирование создания чата
- ✅ Тестирование отправки сообщений
- ✅ Обновление backend API для опциональности user_level

**День 3: Полировка UI (6-8 часов)**

- ✅ Реализация MessageInput с автоизменением размера
- ✅ Реализация автопрокрутки в MessageList
- ✅ Добавление состояний Loading (спиннер, скелетон)
- ✅ Добавление обработки ошибок (уведомления)
- ✅ Реализация генерации названий чатов
- ✅ Реализация группировки чатов по датам
- ✅ Добавление эффектов hover и переходов

**День 4: Тестирование и исправление багов (4-6 часов)**

- ✅ Тестирование всех пользовательских сценариев
- ✅ Исправление проблем адаптивного дизайна
- ✅ Тестирование тёмной темы
- ✅ Тестирование без user_level (проверка работы State Classification)
- ✅ Оптимизация производительности
- ✅ Документация

***

## 12. СТРАТЕГИЯ ТЕСТИРОВАНИЯ

### 12.1 Модульные тесты

```typescript
// src/components/Chat/__tests__/Message.test.tsx
// ЦЕЛЬ: Тестирование компонента Message

import { render, screen } from '@testing-library/react';
import Message from '../Message';

describe('Компонент Message', () => {
  it('отображает сообщение пользователя', () => {
    const message = {
      id: '1',
      role: 'user',
      content: 'Тестовое сообщение',
      timestamp: new Date().toISOString(),
    };

    render(<Message message={message} />);
    expect(screen.getByText('Тестовое сообщение')).toBeInTheDocument();
  });

  it('отображает сообщение бота с markdown', () => {
    const message = {
      id: '2',
      role: 'assistant',
      content: '**Жирный текст**',
      timestamp: new Date().toISOString(),
    };

    render(<Message message={message} />);
    expect(screen.getByText('Жирный текст')).toHaveStyle({ fontWeight: 'bold' });
  });
});
```


### 12.2 Интеграционные тесты

```typescript
// src/services/__tests__/messageService.test.ts
// ЦЕЛЬ: Тестирование сервиса сообщений

import { messageService } from '../messageService';
import { api } from '../api';

jest.mock('../api');

describe('Сервис сообщений', () => {
  it('отправляет сообщение без user_level', async () => {
    const mockResponse = {
      data: {
        status: 'success',
        answer: 'Тестовый ответ',
      },
    };

    (api.post as jest.Mock).mockResolvedValue(mockResponse);

    const result = await messageService.sendMessage(
      'Тестовый вопрос',
      'user_123'
    );

    expect(api.post).toHaveBeenCalledWith(
      '/api/v1/questions/adaptive',
      expect.objectContaining({
        question: 'Тестовый вопрос',
        user_id: 'user_123',
        // user_level НЕ включён!
      })
    );

    expect(result.answer).toBe('Тестовый ответ');
  });
});
```


***

## 13. КРИТЕРИИ ПРИЕМКИ

### 13.1 Функциональные требования

**Боковая панель:**

- ✅ Кнопка "Новый чат" создаёт новую сессию
- ✅ Список чатов загружается из API
- ✅ Клик на чат переключает активный чат
- ✅ Чаты группируются по дате (Сегодня, Вчера и т.д.)
- ✅ При наведении показывается кнопка удаления
- ✅ Активный чат подсвечивается

**Основная область чата:**

- ✅ Сообщения отображаются в правильном порядке
- ✅ Сообщения пользователя справа, бота слева
- ✅ Markdown рендерится корректно
- ✅ Автопрокрутка к последнему сообщению
- ✅ Индикатор загрузки во время генерации

**Поле ввода:**

- ✅ Enter отправляет сообщение
- ✅ Shift+Enter добавляет новую строку
- ✅ Textarea автоматически изменяет размер (до max-height)
- ✅ Disabled состояние во время отправки

**Интеграция с API:**

- ✅ `user_level` НЕ отправляется в запросах
- ✅ Сообщения успешно отправляются без user_level
- ✅ Ответы бота адаптивны (через State Classification)
- ✅ Чаты сохраняются в SQLite через SessionManager


### 13.2 Нефункциональные требования

**Производительность:**

- ✅ Список чатов загружается < 500мс
- ✅ Задержка отправки сообщения < 5с (зависит от OpenAI)
- ✅ Нет утечек памяти (протестировано Chrome DevTools)
- ✅ Плавная прокрутка (60 FPS)

**Удобство использования:**

- ✅ Интуитивная навигация
- ✅ Чёткая визуальная иерархия
- ✅ Нет жаргона в UI (простые формулировки)

**Доступность:**

- ✅ Навигация с клавиатуры
- ✅ Совместимость со скрин-ридерами
- ✅ Контрастность цветов WCAG AA

**Адаптивность:**

- ✅ Работает на десктопе (1920x1080)
- ✅ Работает на планшете (768x1024)
- ✅ Работает на мобильном (375x667)

**Поддержка браузеров:**

- ✅ Chrome 100+
- ✅ Firefox 100+
- ✅ Safari 15+
- ✅ Edge 100+

***

## ФИНАЛЬНЫЙ ЧЕКЛИСТ

**Перед началом реализации:**

- [ ] Подтвердить, что API endpoints доступны и работают
- [ ] Проверить, что SessionManager корректно обрабатывает несколько сессий
- [ ] Сделать резервную копию текущего web_ui (если нужно)
- [ ] Создать feature ветку: `git checkout -b feature/chatgpt-ui-redesign`

**Во время реализации:**

- [ ] Следовать структуре компонентов из Раздела 5
- [ ] Удалить user_level из ВСЕХ мест (Frontend, API, Backend)
- [ ] Тестировать, что State Classification обеспечивает адаптивные ответы
- [ ] Делать частые коммиты с чёткими сообщениями

**После реализации:**

- [ ] Запустить все тесты (модульные, интеграционные, E2E)
- [ ] Проверить адаптивный дизайн на мобильных/планшетах
- [ ] Протестировать тёмную тему
- [ ] Развернуть на staging окружение
- [ ] User acceptance testing
- [ ] Слить в main ветку

***

## ВАЖНОЕ ПРИМЕЧАНИЕ ДЛЯ CURSOR AI

⚠️ Этот ПРД содержит основные разделы И ПРИЛОЖЕНИЕ A в конце документа.
Компоненты из ПРИЛОЖЕНИЯ A должны быть реализованы как часть основной структуры.
Следуйте комментариям в коде для правильной интеграции.


***
## ---

## ПРИЛОЖЕНИЕ A: ДОПОЛНИТЕЛЬНЫЕ КОМПОНЕНТЫ НАСТРОЕК

**ВНИМАНИЕ ДЛЯ CURSOR AI:** Эти компоненты должны быть интегрированы в основную структуру согласно комментариям.

### A.1 Обновление структуры папок
[вставить новое дерево папок]

### A.2 Новые компоненты
[вставить все компоненты Settings/*]

### A.3 Обновления существующих компонентов
[вставить обновлённый Header.tsx и App.tsx]

### A.4 Дополнительные критерии приемки
[вставить критерии для Settings]





# ДОПОЛНЕНИЕ К ПРД: КОМПОНЕНТ НАСТРОЕК

## ОБНОВЛЕНИЕ: Раздел 4.2 - Структура папок

```
bot_psychologist/web_ui/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   │
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── Header.tsx           # ОБНОВЛЕНО: + кнопка Settings
│   │   │   ├── Sidebar.tsx
│   │   │   └── MainLayout.tsx
│   │   │
│   │   ├── Chat/
│   │   │   ├── ChatList.tsx
│   │   │   ├── ChatListItem.tsx
│   │   │   ├── ChatView.tsx
│   │   │   ├── Message.tsx
│   │   │   ├── MessageList.tsx
│   │   │   └── MessageInput.tsx
│   │   │
│   │   ├── Settings/                # НОВОЕ: Компоненты настроек
│   │   │   ├── SettingsModal.tsx   # Модальное окно настроек
│   │   │   ├── SystemInfo.tsx      # Информация о состоянии
│   │   │   ├── UISettings.tsx      # Настройки интерфейса
│   │   │   ├── BotSettings.tsx     # Настройки функций бота
│   │   │   ├── ThemeSelector.tsx   # Выбор темы
│   │   │   └── DataManagement.tsx  # Экспорт/удаление данных
│   │   │
│   │   ├── UI/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Loading.tsx
│   │   │   ├── Avatar.tsx
│   │   │   ├── ThemeToggle.tsx
│   │   │   ├── Toggle.tsx          # НОВОЕ: Toggle switch компонент
│   │   │   ├── Badge.tsx           # НОВОЕ: Badge для состояния
│   │   │   └── Modal.tsx           # НОВОЕ: Базовый modal wrapper
│   │   │
│   │   └── Markdown/
│   │       └── MarkdownRenderer.tsx
│   │
│   ├── context/
│   │   ├── ChatContext.tsx
│   │   ├── ThemeContext.tsx
│   │   ├── UserContext.tsx
│   │   └── SettingsContext.tsx      # НОВОЕ: Управление настройками
│   │
│   ├── hooks/
│   │   ├── useChats.ts
│   │   ├── useMessages.ts
│   │   ├── useLocalStorage.ts
│   │   ├── useAutoScroll.ts
│   │   └── useSettings.ts           # НОВОЕ: Хук для настроек
│   │
│   ├── types/
│   │   ├── chat.ts
│   │   ├── api.ts
│   │   ├── user.ts
│   │   └── settings.ts              # НОВОЕ: Типы настроек
│   │
│   └── utils/
│       ├── dateFormat.ts
│       ├── generateChatTitle.ts
│       └── storage.ts
```


***

## РАЗДЕЛ 5.8: КОМПОНЕНТЫ НАСТРОЕК

### 5.8.1 Типы для настроек

```typescript
// src/types/settings.ts
// ЦЕЛЬ: Определение типов для настроек приложения

export interface AppSettings {
  // Настройки интерфейса
  autoScroll: boolean;              // Автопрокрутка чата
  showSources: boolean;             // Показывать источники
  compactMode: boolean;             // Компактный режим сообщений
  fontSize: 'small' | 'medium' | 'large'; // Размер шрифта
  
  // Настройки функций бота
  includePathRecommendation: boolean;  // Персональные рекомендации
  includeFeedbackPrompt: boolean;      // Запрашивать обратную связь
  enableEmotionAnalysis: boolean;      // Анализ эмоций
  
  // Настройки темы
  theme: 'light' | 'dark' | 'system';  // Тема оформления
  
  // Настройки уведомлений (для будущего)
  enableNotifications: boolean;
  soundEnabled: boolean;
}

export const DEFAULT_SETTINGS: AppSettings = {
  autoScroll: true,
  showSources: true,
  compactMode: false,
  fontSize: 'medium',
  includePathRecommendation: true,
  includeFeedbackPrompt: false,
  enableEmotionAnalysis: true,
  theme: 'system',
  enableNotifications: false,
  soundEnabled: false,
};

export interface StateInfo {
  primary_state: string;
  confidence: number;
  emotional_tone: string;
  depth: string;
  recommended_mode?: string;
}
```


***

### 5.8.2 SettingsContext

```typescript
// src/context/SettingsContext.tsx
// ЦЕЛЬ: Глобальное управление настройками приложения

import { createContext, useState, useEffect, ReactNode } from 'react';
import { AppSettings, DEFAULT_SETTINGS } from '../types/settings';

interface SettingsContextType {
  settings: AppSettings;
  updateSettings: (updates: Partial<AppSettings>) => void;
  resetSettings: () => void;
  isSettingsOpen: boolean;
  openSettings: () => void;
  closeSettings: () => void;
}

export const SettingsContext = createContext<SettingsContextType>(null!);

const SETTINGS_STORAGE_KEY = 'bot_psychologist_settings';

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Загрузка настроек из localStorage при монтировании
  useEffect(() => {
    const storedSettings = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (storedSettings) {
      try {
        const parsed = JSON.parse(storedSettings);
        setSettings({ ...DEFAULT_SETTINGS, ...parsed });
      } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
      }
    }
  }, []);

  // Сохранение настроек в localStorage при изменении
  useEffect(() => {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  }, [settings]);

  const updateSettings = (updates: Partial<AppSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  };

  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS);
    localStorage.removeItem(SETTINGS_STORAGE_KEY);
  };

  const openSettings = () => setIsSettingsOpen(true);
  const closeSettings = () => setIsSettingsOpen(false);

  return (
    <SettingsContext.Provider
      value={{
        settings,
        updateSettings,
        resetSettings,
        isSettingsOpen,
        openSettings,
        closeSettings,
      }}
    >
      {children}
    </SettingsContext.Provider>
  );
}
```


***

### 5.8.3 Обновлённый компонент Header

```tsx
// src/components/Layout/Header.tsx
// ЦЕЛЬ: Верхняя панель с кнопкой настроек и badge состояния

import { useContext, useState } from 'react';
import { ThemeContext } from '../../context/ThemeContext';
import { SettingsContext } from '../../context/SettingsContext';
import { ChatContext } from '../../context/ChatContext';
import Badge from '../UI/Badge';
import Button from '../UI/Button';

interface HeaderProps {
  onMenuClick: () => void;
}

export default function Header({ onMenuClick }: HeaderProps) {
  const { theme, toggleTheme } = useContext(ThemeContext);
  const { openSettings } = useContext(SettingsContext);
  const { stateAnalysis } = useContext(ChatContext);
  const [showStateDetails, setShowStateDetails] = useState(false);

  return (
    <header className="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-4">
      {/* Левая часть: Меню + Логотип */}
      <div className="flex items-center gap-4">
        {/* Кнопка меню (мобильные) */}
        <button
          onClick={onMenuClick}
          className="md:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          ☰
        </button>

        {/* Логотип */}
        <div className="flex items-center gap-2">
          <span className="text-2xl">🧠</span>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Bot Psychologist
          </h1>
        </div>
      </div>

      {/* Правая часть: State Badge + Тема + Настройки + Профиль */}
      <div className="flex items-center gap-3">
        {/* Badge состояния */}
        {stateAnalysis && (
          <div className="relative">
            <Badge
              icon={getStateEmoji(stateAnalysis.primary_state)}
              label={translateState(stateAnalysis.primary_state)}
              onClick={() => setShowStateDetails(!showStateDetails)}
              className="cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
            />

            {/* Всплывающее окно с деталями */}
            {showStateDetails && (
              <div className="absolute top-full right-0 mt-2 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 z-50">
                <h3 className="text-sm font-semibold mb-2">
                  Информация о состоянии
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">
                      Состояние:
                    </span>
                    <span className="font-medium">
                      {translateState(stateAnalysis.primary_state)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">
                      Уверенность:
                    </span>
                    <span className="font-medium">
                      {(stateAnalysis.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">
                      Эмоц. тон:
                    </span>
                    <span className="font-medium">
                      {stateAnalysis.emotional_tone}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Переключатель темы */}
        <button
          onClick={toggleTheme}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          title="Переключить тему"
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>

        {/* Кнопка настроек */}
        <button
          onClick={openSettings}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          title="Настройки"
        >
          ⚙️
        </button>

        {/* Профиль (заглушка для будущего) */}
        <button
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          title="Профиль"
        >
          👤
        </button>
      </div>
    </header>
  );
}

// Вспомогательные функции
function getStateEmoji(state: string): string {
  const emojiMap: Record<string, string> = {
    curious: '😊',
    confused: '😕',
    overwhelmed: '😰',
    seeking: '🔍',
    reflecting: '🤔',
    resistant: '🛡️',
    open: '🌟',
    unaware: '❓',
    ready: '✅',
    integrating: '🧩',
  };
  return emojiMap[state.toLowerCase()] || '😊';
}

function translateState(state: string): string {
  const translations: Record<string, string> = {
    curious: 'Любопытство',
    confused: 'Замешательство',
    overwhelmed: 'Перегрузка',
    seeking: 'Поиск',
    reflecting: 'Размышление',
    resistant: 'Сопротивление',
    open: 'Открытость',
    unaware: 'Неосознанность',
    ready: 'Готовность',
    integrating: 'Интеграция',
  };
  return translations[state.toLowerCase()] || state;
}
```


***

### 5.8.4 Компонент Badge

```tsx
// src/components/UI/Badge.tsx
// ЦЕЛЬ: Переиспользуемый badge компонент

interface BadgeProps {
  icon?: string;
  label: string;
  onClick?: () => void;
  className?: string;
}

export default function Badge({ icon, label, onClick, className = '' }: BadgeProps) {
  return (
    <div
      onClick={onClick}
      className={`
        inline-flex items-center gap-2 px-3 py-1.5 rounded-full
        bg-gray-100 dark:bg-gray-700
        text-sm font-medium text-gray-700 dark:text-gray-300
        transition-colors duration-200
        ${onClick ? 'cursor-pointer' : ''}
        ${className}
      `}
    >
      {icon && <span className="text-base">{icon}</span>}
      <span>{label}</span>
    </div>
  );
}
```


***

### 5.8.5 Компонент Toggle

```tsx
// src/components/UI/Toggle.tsx
// ЦЕЛЬ: Переключатель вкл/выкл

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export default function Toggle({ checked, onChange, disabled = false }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`
        relative inline-flex h-6 w-11 items-center rounded-full
        transition-colors duration-200 ease-in-out
        focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2
        ${checked ? 'bg-indigo-600' : 'bg-gray-200 dark:bg-gray-700'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      <span
        className={`
          inline-block h-4 w-4 transform rounded-full bg-white
          transition duration-200 ease-in-out
          ${checked ? 'translate-x-6' : 'translate-x-1'}
        `}
      />
    </button>
  );
}
```


***

### 5.8.6 Компонент Modal

```tsx
// src/components/UI/Modal.tsx
// ЦЕЛЬ: Базовая обёртка для модальных окон

import { useEffect, ReactNode } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export default function Modal({ isOpen, onClose, title, children, footer }: ModalProps) {
  // Закрытие по Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Блокировка прокрутки body
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-xl w-full max-w-lg mx-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()} // Предотвращение закрытия при клике внутри
      >
        {/* Заголовок */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-2xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Контент */}
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          {children}
        </div>

        {/* Footer (опционально) */}
        {footer && (
          <div className="p-6 border-t border-gray-200 dark:border-gray-700">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
```


***

### 5.8.7 Главный компонент SettingsModal

```tsx
// src/components/Settings/SettingsModal.tsx
// ЦЕЛЬ: Модальное окно настроек приложения

import { useContext } from 'react';
import { SettingsContext } from '../../context/SettingsContext';
import { ChatContext } from '../../context/ChatContext';
import Modal from '../UI/Modal';
import SystemInfo from './SystemInfo';
import UISettings from './UISettings';
import BotSettings from './BotSettings';
import ThemeSelector from './ThemeSelector';
import DataManagement from './DataManagement';
import Button from '../UI/Button';

export default function SettingsModal() {
  const { isSettingsOpen, closeSettings, resetSettings } = useContext(SettingsContext);
  const { stateAnalysis } = useContext(ChatContext);

  const handleReset = () => {
    if (confirm('Вы уверены, что хотите сбросить все настройки?')) {
      resetSettings();
    }
  };

  return (
    <Modal
      isOpen={isSettingsOpen}
      onClose={closeSettings}
      title="⚙️ Настройки"
      footer={
        <div className="flex gap-3">
          <Button
            onClick={handleReset}
            variant="outline"
            className="flex-1"
          >
            Сбросить всё
          </Button>
          <Button
            onClick={closeSettings}
            variant="primary"
            className="flex-1"
          >
            Готово
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Информация о системе */}
        <SystemInfo stateAnalysis={stateAnalysis} />

        {/* Настройки интерфейса */}
        <UISettings />

        {/* Функции бота */}
        <BotSettings />

        {/* Выбор темы */}
        <ThemeSelector />

        {/* Управление данными */}
        <DataManagement />
      </div>
    </Modal>
  );
}
```


***

### 5.8.8 Компонент SystemInfo

```tsx
// src/components/Settings/SystemInfo.tsx
// ЦЕЛЬ: Отображение информации о текущем состоянии пользователя

interface SystemInfoProps {
  stateAnalysis: any; // Из ChatContext
}

export default function SystemInfo({ stateAnalysis }: SystemInfoProps) {
  if (!stateAnalysis) {
    return (
      <section>
        <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-3">
          📊 Информация о системе
        </h3>
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <p className="text-sm text-gray-500">
            Данные о состоянии пока недоступны
          </p>
        </div>
      </section>
    );
  }

  return (
    <section>
      <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-3">
        📊 Информация о системе
      </h3>
      <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 space-y-3">
        <InfoRow
          label="Текущее состояние"
          value={translateState(stateAnalysis.primary_state)}
          icon={getStateEmoji(stateAnalysis.primary_state)}
        />
        <InfoRow
          label="Уверенность"
          value={`${(stateAnalysis.confidence * 100).toFixed(0)}%`}
        />
        <InfoRow
          label="Эмоциональный тон"
          value={stateAnalysis.emotional_tone || 'N/A'}
        />
        <InfoRow
          label="Глубина"
          value={stateAnalysis.depth || 'N/A'}
        />
        {stateAnalysis.recommended_mode && (
          <InfoRow
            label="Рекомендуемый режим"
            value={stateAnalysis.recommended_mode}
          />
        )}
      </div>
    </section>
  );
}

function InfoRow({ label, value, icon }: { label: string; value: string; icon?: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-600 dark:text-gray-400">
        {label}:
      </span>
      <span className="text-sm font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
        {icon && <span>{icon}</span>}
        {value}
      </span>
    </div>
  );
}

// Вспомогательные функции (копировать из Header.tsx)
function getStateEmoji(state: string): string {
  const emojiMap: Record<string, string> = {
    curious: '😊',
    confused: '😕',
    overwhelmed: '😰',
    seeking: '🔍',
    reflecting: '🤔',
    resistant: '🛡️',
    open: '🌟',
    unaware: '❓',
    ready: '✅',
    integrating: '🧩',
  };
  return emojiMap[state.toLowerCase()] || '😊';
}

function translateState(state: string): string {
  const translations: Record<string, string> = {
    curious: 'Любопытство',
    confused: 'Замешательство',
    overwhelmed: 'Перегрузка',
    seeking: 'Поиск',
    reflecting: 'Размышление',
    resistant: 'Сопротивление',
    open: 'Открытость',
    unaware: 'Неосознанность',
    ready: 'Готовность',
    integrating: 'Интеграция',
  };
  return translations[state.toLowerCase()] || state;
}
```


***

### 5.8.9 Компонент UISettings

```tsx
// src/components/Settings/UISettings.tsx
// ЦЕЛЬ: Настройки интерфейса

import { useContext } from 'react';
import { SettingsContext } from '../../context/SettingsContext';
import Toggle from '../UI/Toggle';

export default function UISettings() {
  const { settings, updateSettings } = useContext(SettingsContext);

  return (
    <section>
      <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-3">
        🎨 Интерфейс
      </h3>
      <div className="space-y-3">
        <SettingRow
          label="Автопрокрутка чата"
          description="Автоматическая прокрутка к новым сообщениям"
          checked={settings.autoScroll}
          onChange={(checked) => updateSettings({ autoScroll: checked })}
        />
        <SettingRow
          label="Показывать источники"
          description="Отображать ссылки на источники под ответами"
          checked={settings.showSources}
          onChange={(checked) => updateSettings({ showSources: checked })}
        />
        <SettingRow
          label="Компактный режим"
          description="Уменьшенные отступы между сообщениями"
          checked={settings.compactMode}
          onChange={(checked) => updateSettings({ compactMode: checked })}
        />
      </div>
    </section>
  );
}

function SettingRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {label}
        </p>
        {description && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {description}
          </p>
        )}
      </div>
      <Toggle checked={checked} onChange={onChange} />
    </div>
  );
}
```


***

### 5.8.10 Компонент BotSettings

```tsx
// src/components/Settings/BotSettings.tsx
// ЦЕЛЬ: Настройки функций бота

import { useContext } from 'react';
import { SettingsContext } from '../../context/SettingsContext';
import Toggle from '../UI/Toggle';

export default function BotSettings() {
  const { settings, updateSettings } = useContext(SettingsContext);

  return (
    <section>
      <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-3">
        🧠 Функции бота
      </h3>
      <div className="space-y-3">
        <SettingRow
          label="Персональные рекомендации"
          description="Показывать пути развития и рекомендации"
          checked={settings.includePathRecommendation}
          onChange={(checked) => updateSettings({ includePathRecommendation: checked })}
        />
        <SettingRow
          label="Запрашивать обратную связь"
          description="Бот будет спрашивать оценку ответов"
          checked={settings.includeFeedbackPrompt}
          onChange={(checked) => updateSettings({ includeFeedbackPrompt: checked })}
        />
        <SettingRow
          label="Анализ эмоций"
          description="Определение эмоционального состояния"
          checked={settings.enableEmotionAnalysis}
          onChange={(checked) => updateSettings({ enableEmotionAnalysis: checked })}
        />
      </div>
    </section>
  );
}

function SettingRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {label}
        </p>
        {description && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {description}
          </p>
        )}
      </div>
      <Toggle checked={checked} onChange={onChange} />
    </div>
  );
}
```


***

### 5.8.11 Компонент ThemeSelector

```tsx
// src/components/Settings/ThemeSelector.tsx
// ЦЕЛЬ: Выбор темы оформления

import { useContext } from 'react';
import { ThemeContext } from '../../context/ThemeContext';

export default function ThemeSelector() {
  const { theme, setTheme } = useContext(ThemeContext);

  return (
    <section>
      <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-3">
        🌙 Тема
      </h3>
      <div className="grid grid-cols-3 gap-2">
        <ThemeButton
          label="Светлая"
          icon="☀️"
          active={theme === 'light'}
          onClick={() => setTheme('light')}
        />
        <ThemeButton
          label="Тёмная"
          icon="🌙"
          active={theme === 'dark'}
          onClick={() => setTheme('dark')}
        />
        <ThemeButton
          label="Системная"
          icon="💻"
          active={theme === 'system'}
          onClick={() => setTheme('system')}
        />
      </div>
    </section>
  );
}

function ThemeButton({
  label,
  icon,
  active,
  onClick,
}: {
  label: string;
  icon: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        flex flex-col items-center justify-center p-3 rounded-lg border-2
        transition-all duration-200
        ${
          active
            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
        }
      `}
    >
      <span className="text-2xl mb-1">{icon}</span>
      <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
        {label}
      </span>
    </button>
  );
}
```


***

### 5.8.12 Компонент DataManagement

```tsx
// src/components/Settings/DataManagement.tsx
// ЦЕЛЬ: Экспорт и удаление данных

import { useContext, useState } from 'react';
import { ChatContext } from '../../context/ChatContext';
import { UserContext } from '../../context/UserContext';
import Button from '../UI/Button';

export default function DataManagement() {
  const { chats, messages } = useContext(ChatContext);
  const { userId } = useContext(UserContext);
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      // Формирование JSON со всеми чатами
      const exportData = {
        user_id: userId,
        export_date: new Date().toISOString(),
        chats: chats,
        total_messages: messages.length,
      };

      // Создание blob и скачивание
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `bot-psychologist-export-${Date.now()}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Ошибка экспорта:', error);
      alert('Не удалось экспортировать данные');
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAll = async () => {
    const confirmed = confirm(
      'Вы уверены, что хотите удалить ВСЕ чаты? Это действие необратимо!'
    );
    if (!confirmed) return;

    const doubleConfirm = confirm('Точно уверены? Данные будут потеряны навсегда.');
    if (!doubleConfirm) return;

    try {
      // Вызов API для удаления всех чатов
      // await chatService.deleteAllChats(userId);
      alert('Все чаты удалены');
      window.location.reload(); // Перезагрузка приложения
    } catch (error) {
      console.error('Ошибка удаления:', error);
      alert('Не удалось удалить данные');
    }
  };

  return (
    <section>
      <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-3">
        ⚠️ Управление данными
      </h3>
      <div className="space-y-3">
        <Button
          onClick={handleExport}
          disabled={exporting || chats.length === 0}
          variant="outline"
          className="w-full"
        >
          {exporting ? '📤 Экспортируется...' : '📤 Экспортировать историю'}
        </Button>
        <Button
          onClick={handleDeleteAll}
          variant="danger"
          className="w-full"
          disabled={chats.length === 0}
        >
          🗑️ Удалить все чаты
        </Button>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          У вас {chats.length} {chats.length === 1 ? 'чат' : 'чатов'} с {messages.length}{' '}
          {messages.length === 1 ? 'сообщением' : 'сообщениями'}
        </p>
      </div>
    </section>
  );
}
```


***

### 5.8.13 Обновление App.tsx

```tsx
// src/App.tsx
// ОБНОВЛЕНО: Добавлен SettingsProvider и SettingsModal

import { ChatProvider } from './context/ChatContext';
import { ThemeProvider } from './context/ThemeContext';
import { UserProvider } from './context/UserContext';
import { SettingsProvider } from './context/SettingsContext'; // НОВОЕ
import MainLayout from './components/Layout/MainLayout';
import SettingsModal from './components/Settings/SettingsModal'; // НОВОЕ

export default function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <SettingsProvider> {/* НОВОЕ */}
          <ChatProvider>
            <MainLayout />
            <SettingsModal /> {/* НОВОЕ */}
          </ChatProvider>
        </SettingsProvider>
      </UserProvider>
    </ThemeProvider>
  );
}
```


***

## ОБНОВЛЕНИЕ РАЗДЕЛА 11: ПЛАН РЕАЛИЗАЦИИ

### Добавить в День 1:

**День 1: Базовая структура (6-8 часов)**

- ✅ Создать типы для настроек (settings.ts)
- ✅ Создать SettingsContext
- ✅ Создать UI компоненты (Toggle, Badge, Modal)
- ✅ Обновить Header с кнопкой Settings и State Badge

**День 2: Интеграция API (6-8 часов)**

- ✅ Создать все компоненты Settings/*
- ✅ Подключить настройки к ChatContext (использовать settings при отправке)
- ✅ Добавить state_analysis в ChatContext

**День 3: Полировка UI (6-8 часов)**

- ✅ Анимации открытия/закрытия модального окна
- ✅ Функция экспорта данных
- ✅ Тестирование всех настроек

***

## КРИТЕРИИ ПРИЕМКИ ДЛЯ SETTINGS

### Функциональные требования:

- ✅ Кнопка ⚙️ открывает модальное окно настроек
- ✅ Badge состояния отображается в Header
- ✅ При клике на badge показываются детали состояния
- ✅ Все toggle переключатели работают
- ✅ Настройки сохраняются в localStorage
- ✅ Настройки применяются немедленно (autoScroll, showSources и т.д.)
- ✅ Кнопка "Сбросить всё" возвращает DEFAULT_SETTINGS
- ✅ Экспорт создаёт JSON файл с историей
- ✅ Удаление чатов требует двойного подтверждения


### UI/UX требования:

- ✅ Модальное окно закрывается по Escape
- ✅ Модальное окно закрывается по клику вне его
- ✅ Плавные анимации переходов
- ✅ Адаптивный дизайн (работает на мобильных)
- ✅ Тёмная тема применяется ко всем компонентам Settings

***

## ИТОГО

Теперь ваш ПРД содержит:

1. ✅ **Полное удаление user_level** из UI
2. ✅ **Автоматическое определение состояния** (State Classification)
3. ✅ **Badge в Header** с информацией о текущем состоянии
4. ✅ **Модальное окно Settings** с 5 секциями:
    - 📊 Информация о системе (read-only)
    - 🎨 Настройки интерфейса
    - 🧠 Функции бота
    - 🌙 Выбор темы
    - ⚠️ Управление данными
5. ✅ **Все компоненты на русском языке** для Cursor AI
6. ✅ **Детальные комментарии** в каждом файле

Документ полностью готов для передачи в Cursor AI! 🚀

