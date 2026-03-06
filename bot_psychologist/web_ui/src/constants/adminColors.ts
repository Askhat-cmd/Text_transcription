// bot_psychologist/web_ui/src/constants/adminColors.ts
// Все цветовые константы Admin Panel — единая точка правды
// Импортировать в AdminPanel.tsx и ConfigGroupPanel.tsx

export const GROUP_COLORS: Record<string, string> = {
  llm: 'violet',
  retrieval: 'blue',
  memory: 'emerald',
  storage: 'amber',
  runtime: 'slate',
};

export const ACCENT_CLASSES = {
  violet: {
    border: 'border-l-violet-500',
    icon: 'bg-violet-100 text-violet-700',
    saveBtn: 'bg-violet-600 hover:bg-violet-700 text-white',
    checkBtn: 'bg-violet-600 hover:bg-violet-700 text-white',
    badge: 'bg-violet-100 text-violet-700',
    override: 'border-violet-300 bg-violet-50',
    ring: 'focus:ring-violet-300',
  },
  blue: {
    border: 'border-l-blue-500',
    icon: 'bg-blue-100 text-blue-700',
    saveBtn: 'bg-blue-600 hover:bg-blue-700 text-white',
    checkBtn: 'bg-blue-600 hover:bg-blue-700 text-white',
    badge: 'bg-blue-100 text-blue-700',
    override: 'border-blue-300 bg-blue-50',
    ring: 'focus:ring-blue-300',
  },
  emerald: {
    border: 'border-l-emerald-500',
    icon: 'bg-emerald-100 text-emerald-700',
    saveBtn: 'bg-emerald-600 hover:bg-emerald-700 text-white',
    checkBtn: 'bg-emerald-600 hover:bg-emerald-700 text-white',
    badge: 'bg-emerald-100 text-emerald-700',
    override: 'border-emerald-300 bg-emerald-50',
    ring: 'focus:ring-emerald-300',
  },
  amber: {
    border: 'border-l-amber-500',
    icon: 'bg-amber-100 text-amber-700',
    saveBtn: 'bg-amber-500 hover:bg-amber-600 text-white',
    checkBtn: 'bg-amber-500 hover:bg-amber-600 text-white',
    badge: 'bg-amber-100 text-amber-700',
    override: 'border-amber-300 bg-amber-50',
    ring: 'focus:ring-amber-300',
  },
  slate: {
    border: 'border-l-slate-500',
    icon: 'bg-slate-100 text-slate-700',
    saveBtn: 'bg-slate-600 hover:bg-slate-700 text-white',
    checkBtn: 'bg-slate-600 hover:bg-slate-700 text-white',
    badge: 'bg-slate-100 text-slate-700',
    override: 'border-slate-300 bg-slate-50',
    ring: 'focus:ring-slate-300',
  },
  rose: {
    border: 'border-l-rose-500',
    icon: 'bg-rose-100 text-rose-700',
    saveBtn: 'bg-rose-600 hover:bg-rose-700 text-white',
    checkBtn: 'bg-rose-600 hover:bg-rose-700 text-white',
    badge: 'bg-rose-100 text-rose-700',
    override: 'border-rose-300 bg-rose-50',
    ring: 'focus:ring-rose-300',
  },
  indigo: {
    border: 'border-l-indigo-500',
    icon: 'bg-indigo-100 text-indigo-700',
    saveBtn: 'bg-indigo-600 hover:bg-indigo-700 text-white',
    checkBtn: 'bg-indigo-600 hover:bg-indigo-700 text-white',
    badge: 'bg-indigo-100 text-indigo-700',
    override: 'border-indigo-300 bg-indigo-50',
    ring: 'focus:ring-indigo-300',
  },
} as const;

export type AccentKey = keyof typeof ACCENT_CLASSES;
