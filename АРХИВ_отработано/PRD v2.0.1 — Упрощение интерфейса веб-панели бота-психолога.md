
# PRD v2.0.1 — Упрощение интерфейса веб-панели бота-психолога

**Проект:** bot_psychologist / web_ui  
**Версия:** 2.0.1  
**Дата:** 2026-03-03  
**Статус:** Ready for implementation  
**Приоритет:** High  

---

## 1. КОНТЕКСТ И ЦЕЛЬ

### 1.1 Предыстория
Веб-панель развивалась итеративно: сначала были добавлены
расширенные блоки аналитики для отладки и наблюдения за работой
агента. Затем были созданы два входа — для обычного пользователя
и для разработчика (dev-режим по API-ключу).

### 1.2 Выявленная проблема
Блоки аналитики (#4–#7), изначально добавленные для отладки,
остались видимыми в пользовательском интерфейсе. Для конечного
пользователя они создают когнитивную перегрузку и разрушают
ощущение живого диалога. В dev-режиме эти же данные дублируют
информацию, которая уже есть в InlineDebugTrace.

### 1.3 Цель задачи
Убрать блоки #4–#7 из рендера сообщений для ОБОИХ режимов
(user и dev), сохранив их данные только внутри InlineDebugTrace
для dev-режима. Пользователь видит чистый чат.

---

## 2. SCOPE ИЗМЕНЕНИЙ

### 2.1 Файлы для изменения

| Файл | Тип изменения |
|------|--------------|
| `src/components/chat/Message.tsx` | Основное изменение — убрать рендер блоков #4–#7 |
| `src/pages/ChatPage.tsx` | Проверить пропсы showSources / showPath / dev-флаг |
| `src/types/index.ts` (или аналог) | Только проверка — типы не менять |

### 2.2 Файлы НЕ трогать

- `InlineDebugTrace.tsx` — не изменять, он остаётся как есть
- `api.service.ts` — бэкенд-логику не менять
- `websocket.service.ts` — не трогать
- `storage.service.ts` — не трогать
- Страницы `ProfilePage`, `SettingsPage`, `HomePage` — не трогать
- `Sidebar.tsx`, `Header.tsx`, `Footer.tsx` — не трогать

---

## 3. ДЕТАЛЬНЫЕ ТРЕБОВАНИЯ

### 3.1 Блоки для УДАЛЕНИЯ из `Message.tsx`

Удалить следующие 4 блока из рендера бот-сообщения (секция
`{!isUser && (...)}`):

**Блок #4 — Эмоциональное состояние:**
```tsx
{/* State Indicator */}
{message.state && (
  <StateCardCompact
    state={message.state}
    confidence={message.confidence}
    className="mt-3"
  />
)}
```

→ **Удалить полностью**

**Блок \#5 — Теги концептов:**

```tsx
{/* Concepts Tags */}
{message.concepts && message.concepts.length > 0 && (
  <div className="mt-3 flex flex-wrap gap-1">
    {message.concepts.slice(0, 5).map((concept, idx) => (
      <span key={idx} className="bg-purple-100 ...">
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
```

→ **Удалить полностью**

**Блок \#6 — Источники:**

```tsx
{/* Sources */}
{showSources && message.sources && message.sources.length > 0 && (
  <SourcesList sources={message.sources} />
)}
```

→ **Удалить полностью** (вместе с пропсом `showSources`)

**Блок \#7 — Персональный путь:**

```tsx
{/* Path Recommendation */}
{showPath && message.path && (
  <div className="mt-3 border-t border-gray-200 ...">
    <h4 className="font-semibold text-sm mb-2 ...">
      🛤️ Персональный путь
    </h4>
    <PathBuilderCompact path={message.path} />
  </div>
)}
```

→ **Удалить полностью** (вместе с пропсом `showPath`)

### 3.2 Блок feedbackPrompt — СОХРАНИТЬ

```tsx
{/* Feedback Prompt */}
{message.feedbackPrompt && (
  <p className="text-xs mt-3 italic text-gray-500 dark:text-gray-400">
    {message.feedbackPrompt}
  </p>
)}
```

→ **Оставить без изменений.** Это не аналитика —
это вопрос для продолжения диалога, полезен для пользователя.

### 3.3 InlineDebugTrace — ЛОГИКА ОСТАЁТСЯ

```tsx
{message.trace && (
  <InlineDebugTrace trace={message.trace} />
)}
```

→ **Не трогать.** Трейс приходит только в dev-режиме
(бэкенд не присылает `trace` для обычного пользователя).

### 3.4 Импорты для удаления из `Message.tsx`

После удаления блоков убрать неиспользуемые импорты:

```tsx
// УДАЛИТЬ:
import { StateCardCompact } from '../insights/StateCard';
import { SourcesList } from '../insights/SourcesList';
import { PathBuilderCompact } from '../insights/PathBuilder';
```

Компонент `InlineDebugTrace` оставить в импортах.

### 3.5 Пропсы интерфейса `MessageItemProps`

Убрать из интерфейса устаревшие пропсы:

```tsx
// БЫЛО:
interface MessageItemProps {
  message: Message;
  showSources?: boolean;  // ← УДАЛИТЬ
  showPath?: boolean;     // ← УДАЛИТЬ
  compactMode?: boolean;
}

// СТАЛО:
interface MessageItemProps {
  message: Message;
  compactMode?: boolean;
}
```


### 3.6 Сигнатура функции компонента

```tsx
// БЫЛО:
export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  showSources = true,  // ← УДАЛИТЬ
  showPath = true,     // ← УДАЛИТЬ
  compactMode = false,
}) => {

// СТАЛО:
export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  compactMode = false,
}) => {
```


### 3.7 Обновить вызовы `MessageItem` в `ChatPage.tsx`

Найти все места в `ChatPage.tsx` где используется `MessageItem`
(или `<MessageItem ...>`) и убрать пропсы `showSources`
и `showPath`, если они там передаются явно:

```tsx
// БЫЛО (возможный вариант):
<MessageItem
  message={msg}
  showSources={isDev}
  showPath={isDev}
/>

// СТАЛО:
<MessageItem
  message={msg}
/>
```


---

## 4. ИТОГОВЫЙ РЕЗУЛЬТАТ `Message.tsx`

После всех изменений секция `{!isUser && (...)}` должна
выглядеть следующим образом:

```tsx
{/* Bot-specific content */}
{!isUser && (
  <>
    {/* Debug Trace — только если пришёл с бэкенда (dev mode) */}
    {message.trace && (
      <InlineDebugTrace trace={message.trace} />
    )}

    {/* Processing Time */}
    {message.processingTime !== undefined && (
      <div className="flex items-center gap-1 text-xs
                       text-gray-500 dark:text-gray-400 mt-2">
        <FiClock size={12} />
        {formatterService.formatProcessingTime(message.processingTime)}
      </div>
    )}

    {/* Feedback Prompt */}
    {message.feedbackPrompt && (
      <p className="text-xs mt-3 italic
                    text-gray-500 dark:text-gray-400">
        {message.feedbackPrompt}
      </p>
    )}
  </>
)}
```


---

## 5. ЧЕГО НЕ ТРОГАТЬ (важно)

1. Типы `Message` в `types/` — поля `state`, `concepts`,
`sources`, `path` можно оставить в типе, они просто
перестанут рендериться. Удалять из типа не нужно —
данные всё ещё приходят с бэкенда и используются
в InlineDebugTrace для dev-режима.
2. `InlineDebugTrace.tsx` — файл не изменять вообще.
3. Компоненты `StateCard`, `SourcesList`, `PathBuilder` в
папке `insights/` — файлы не удалять, просто убрать
импорты из `Message.tsx`. Они могут использоваться
в других местах (`ProfilePage`, будущие страницы).
4. Логику `ChatPage.tsx` не переписывать — только убрать
устаревшие пропсы при вызове `MessageItem`, если они есть.

---

## 6. ТЕСТИРОВАНИЕ

После внесения изменений выполнить следующие проверки:

### 6.1 Компиляция и линтинг

```bash
cd bot_psychologist/web_ui
npm run lint        # Должен пройти без ошибок TypeScript
npm run build       # Должна собраться без ошибок
```


### 6.2 Функциональные проверки в браузере (`npm run dev`)

**Тест 1 — Обычный пользователь (user mode):**

- [ ] Открыть чат, отправить сообщение
- [ ] Убедиться что ответ бота отображается (текст Markdown)
- [ ] Убедиться что `Confused (60%)` НЕ отображается
- [ ] Убедиться что теги (`оптимизм`, `страх` ...) НЕ отображаются
- [ ] Убедиться что блок `Источники` НЕ отображается
- [ ] Убедиться что блок `Персональный путь` НЕ отображается
- [ ] Убедиться что `InlineDebugTrace` (🔍) НЕ отображается
- [ ] Убедиться что `feedbackPrompt` (курсив внизу) ОТОБРАЖАЕТСЯ
- [ ] Убедиться что время обработки (`⏱ 10.97s`) ОТОБРАЖАЕТСЯ
- [ ] Убедиться что время отправки (`14:33`) ОТОБРАЖАЕТСЯ
- [ ] История чатов в sidebar работает корректно
- [ ] Создание нового чата работает

**Тест 2 — Dev-режим:**

- [ ] Войти через dev-ключ
- [ ] Отправить сообщение
- [ ] Убедиться что `InlineDebugTrace` (🔍) ОТОБРАЖАЕТСЯ
- [ ] Убедиться что трейс раскрывается при клике
- [ ] Убедиться что `Confused (60%)` НЕ отображается
(уже есть внутри трейса)
- [ ] Убедиться что теги НЕ отображаются
- [ ] Убедиться что `Источники` НЕ отображаются
- [ ] Убедиться что `Персональный путь` НЕ отображается

**Тест 3 — Общие:**

- [ ] Тёмная тема работает корректно
- [ ] Светлая тема работает корректно
- [ ] Страница `/profile` открывается без ошибок
- [ ] Страница `/settings` открывается без ошибок
- [ ] Страница `/*` (404) открывается без ошибок
- [ ] Console в браузере: нет ошибок React, нет warnings
о неиспользуемых пропсах


### 6.3 Регрессия TypeScript

```bash
npm run lint
```

Ожидаемый результат: **0 errors, 0 warnings**

---

## 7. DEFINITION OF DONE

- [ ] `Message.tsx` не содержит блоков \#4–\#7
- [ ] Неиспользуемые импорты (`StateCardCompact`,
`SourcesList`, `PathBuilderCompact`) удалены
- [ ] Пропсы `showSources` и `showPath` удалены из интерфейса
и сигнатуры компонента
- [ ] `ChatPage.tsx` обновлён — устаревшие пропсы убраны
- [ ] `npm run lint` — 0 ошибок
- [ ] `npm run build` — успешная сборка
- [ ] Все тесты из раздела 6.2 пройдены
- [ ] В browser console нет новых ошибок

```
```

