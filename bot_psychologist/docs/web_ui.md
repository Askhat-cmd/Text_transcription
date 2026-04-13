# Web UI (Phase 6)

## Навигация

- [Назад к README](../README.md)
- [Обзор проекта](./overview.md)
- [Архитектура](./architecture.md)
- [REST API](./api.md)
- [Trace Runtime Guide](./trace_runtime.md)

---

## Описание и назначение

**Назначение документа**: Описание Web UI приложения Bot Psychologist, его компонентов, структуры и интеграции с API.

**Для кого**: Frontend разработчики, UI/UX дизайнеры.

**Что содержит**:
- Обзор Web UI
- Структура проекта
- Компоненты
- Интеграция с API
- Развёртывание

---

## Обзор Web UI

**Web UI** — React SPA приложение для взаимодействия с Bot Psychologist через REST API.

### Технологический стек

- **React 19** — UI библиотека
- **TypeScript** — типизация
- **Vite** — сборщик
- **Tailwind CSS** — стилизация
- **React Router** — маршрутизация
- **Axios** — HTTP клиент
- **Zustand** — управление состоянием

### Возможности

- 💬 **Chat Interface** — диалоговое окно с ботом
- 👤 **User Profile** — профиль пользователя, история, статистика
- 🛤️ **Path Visualization** — визуализация персонального пути трансформации
- 🎯 **State Indicator** — индикатор текущего состояния пользователя
- ⭐ **Feedback Widget** — оценка ответов (1-5 звёзд)
- 📱 **Responsive Design** — работает на любых устройствах
- 🎨 **Modern UI/UX** — Tailwind CSS + Custom Components

---

## Структура проекта

```
web_ui/
├── public/
│   ├── index.html
│   └── vite.svg
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
│   │   ├── index.css
│   │   └── animations.css
│   ├── utils/
│   │   ├── constants.ts
│   │   ├── helpers.ts
│   │   └── validators.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

---

## Компоненты

### Pages

#### HomePage
Главная страница приложения.

**Функции**:
- Приветствие
- Краткое описание возможностей
- Ссылки на основные разделы

#### ChatPage
Основной интерфейс чата с ботом.

**Компоненты**:
- `ChatWindow` — диалоговое окно
- `MessageList` — список сообщений
- `InputBox` — поле ввода вопроса
- `StateCard` — индикатор состояния
- `PathBuilder` — визуализация пути
- `SourcesList` — список источников
- `FeedbackWidget` — оценка ответов

#### ProfilePage
Профиль пользователя.

**Компоненты**:
- `UserProfile` — основная информация
- `InterestsCard` — интересы пользователя
- `StatisticsCard` — статистика взаимодействий

#### SettingsPage
Настройки приложения.

**Функции**:
- Настройка API ключа
- Выбор уровня пользователя
- Настройки темы (dark/light)

---

### Chat Components

#### ChatWindow
Главный компонент чата.

**Функции**:
- Отображение истории диалога
- Отправка вопросов
- Отображение ответов бота
- Интеграция с StateCard, PathBuilder, SourcesList

#### MessageList
Список сообщений диалога.

**Функции**:
- Отображение сообщений пользователя и бота
- Прокрутка к последнему сообщению
- Анимации появления сообщений

#### Message
Одно сообщение в диалоге.

**Типы**:
- `user` — сообщение пользователя
- `bot` — ответ бота
- `system` — системное сообщение

**Функции**:
- Отображение текста
- Форматирование markdown (для ответов бота)
- Отображение источников (для ответов бота)

#### InputBox
Поле ввода вопроса.

**Функции**:
- Ввод текста вопроса
- Отправка вопроса (Enter или кнопка)
- Индикатор загрузки
- Валидация ввода

#### TypingIndicator
Индикатор печати бота.

**Функции**:
- Анимация "бот печатает..."
- Отображение во время обработки запроса

---

### Insights Components

#### StateCard
Индикатор текущего состояния пользователя.

**Функции**:
- Отображение состояния (10 состояний)
- Уровень уверенности
- Эмоциональный тон
- Рекомендации для состояния

#### PathBuilder
Визуализация персонального пути трансформации.

**Функции**:
- Отображение шагов пути
- Прогресс по пути
- Практики для каждого шага
- Концепты для каждого шага

#### PathStep
Один шаг пути трансформации.

**Функции**:
- Отображение номера шага
- Название шага
- Длительность (недели)
- Практики и концепты

#### SourcesList
Список источников ответа.

**Функции**:
- Отображение блоков, использованных в ответе
- Ссылки на YouTube с таймкодами
- Тип блока и сложность

---

### Feedback Components

#### FeedbackWidget
Виджет оценки ответа.

**Функции**:
- Оценка ответа (1-5 звёзд)
- Тип обратной связи (positive/negative/neutral)
- Комментарий (опционально)
- Отправка обратной связи через API

#### RatingStars
Компонент звёздного рейтинга.

**Функции**:
- Отображение 5 звёзд
- Выбор рейтинга (1-5)
- Анимация при наведении

---

### Profile Components

#### UserProfile
Основная информация профиля.

**Функции**:
- ID пользователя
- Уровень пользователя
- Дата регистрации
- Последнее взаимодействие

#### InterestsCard
Интересы пользователя.

**Функции**:
- Основные интересы (из истории диалога)
- Визуализация интересов (теги, облако тегов)

#### StatisticsCard
Статистика взаимодействий.

**Функции**:
- Всего вопросов
- Средний рейтинг
- Топ состояний
- Прогресс по пути

---

## Hooks

### useChat
Управление состоянием чата.

**Функции**:
- История сообщений
- Отправка вопросов
- Обработка ответов
- Сохранение истории в localStorage

### useAPI
Интеграция с REST API.

**Функции**:
- Отправка запросов к API
- Обработка ошибок
- Управление API ключом
- Rate limiting handling

### useWebSocket
WebSocket для real-time обновлений (опционально).

**Функции**:
- Подключение к WebSocket
- Получение real-time обновлений
- Обработка событий

### useTheme
Управление темой (dark/light).

**Функции**:
- Переключение темы
- Сохранение темы в localStorage
- Применение темы к компонентам

### useLocalStorage
Работа с localStorage.

**Функции**:
- Сохранение данных
- Загрузка данных
- Удаление данных

---

## Services

### api.service.ts
HTTP клиент для работы с API.

**Функции**:
- `askQuestion()` — отправка вопроса
- `getUserHistory()` — получение истории
- `submitFeedback()` — отправка обратной связи
- `getStats()` — получение статистики

### storage.service.ts
Работа с localStorage.

**Функции**:
- Сохранение истории чата
- Сохранение настроек
- Загрузка данных

### websocket.service.ts
WebSocket клиент (опционально).

**Функции**:
- Подключение к WebSocket
- Отправка сообщений
- Получение обновлений

### formatter.service.ts
Форматирование данных.

**Функции**:
- Форматирование дат
- Форматирование таймкодов
- Форматирование текста (markdown)

---

## Интеграция с API

### Базовый URL

```typescript
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
```

### API Key

```typescript
const API_KEY = import.meta.env.VITE_API_KEY || "test-key-001";
```

### Пример использования

```typescript
// Отправка вопроса
const response = await apiService.askQuestion({
  query: "Что такое осознавание?",
  user_id: userId,
  include_path: true,
  include_feedback_prompt: true
});

// Обработка ответа
if (response.status === "success") {
  addMessage({
    type: "bot",
    text: response.answer,
    sources: response.sources,
    stateAnalysis: response.state_analysis,
    pathRecommendation: response.path_recommendation
  });
}
```

---

## Развёртывание

### Development

```bash
cd web_ui
npm install
npm run dev
```

Приложение доступно по адресу `http://localhost:5173`.

### Production Build

```bash
npm run build
```

Собранные файлы находятся в `dist/`.

### Preview Production Build

```bash
npm run preview
```

---

## Переменные окружения

Создайте файл `.env.local`:

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_API_KEY=test-key-001
```

---

## Навигация

- [Обзор проекта](./overview.md)
- [Архитектура](./architecture.md)
- [REST API](./api.md)
- [Развёртывание](./deployment.md)
