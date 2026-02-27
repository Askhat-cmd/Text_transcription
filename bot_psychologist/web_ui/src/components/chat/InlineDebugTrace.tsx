import React from 'react';
import type { InlineTrace, TraceBlock } from '../../types';

interface Props {
  trace: InlineTrace;
}

const SD_COLORS: Record<string, string> = {
  purple: 'text-purple-600 dark:text-purple-400',
  red: 'text-red-600 dark:text-red-400',
  blue: 'text-blue-600 dark:text-blue-400',
  orange: 'text-orange-500 dark:text-orange-400',
  green: 'text-emerald-600 dark:text-emerald-400',
  yellow: 'text-yellow-500 dark:text-yellow-300',
};

const MODE_COLORS: Record<string, string> = {
  PRESENCE: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300',
  CLARIFICATION: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  VALIDATION: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  THINKING: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
  INTERVENTION: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300',
  INTEGRATION: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
};

const ChunkCard: React.FC<{ block: TraceBlock; passed: boolean }> = ({ block, passed }) => (
  <details className="mb-2 rounded-lg border border-slate-200 dark:border-slate-700">
    <summary className="cursor-pointer px-3 py-2 flex items-center gap-2 text-xs select-none hover:bg-slate-50 dark:hover:bg-slate-800/50">
      <span>{passed ? '✓' : '✕'}</span>
      <code className="font-mono font-semibold text-slate-700 dark:text-slate-300">{block.block_id}</code>
      <span className={`ml-auto font-semibold ${passed ? 'text-emerald-600' : 'text-rose-500'}`}>
        {block.score.toFixed(3)}
      </span>
      <span className="text-slate-400 truncate max-w-[160px]">{block.source}</span>
      {!passed && block.filter_reason && (
        <span className="text-rose-400 text-[10px] border border-rose-200 rounded px-1">
          {block.filter_reason}
        </span>
      )}
    </summary>
    <div className="px-3 py-2 border-t border-slate-200 dark:border-slate-700">
      <p className="text-[10px] text-slate-400 mb-2 font-mono">
        📄 {block.source} · stage: {block.stage}
      </p>
      <p className="text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">
        {block.text}
      </p>
    </div>
  </details>
);

export const InlineDebugTrace: React.FC<Props> = ({ trace }) => {
  const passedBlocks = trace.blocks.filter((b) => b.passed);
  const filteredBlocks = trace.blocks.filter((b) => !b.passed);
  const sdColor = trace.sd_level ? (SD_COLORS[trace.sd_level] || '') : '';
  const modeColor = MODE_COLORS[trace.recommended_mode] || 'bg-slate-100 text-slate-700';
  const confColor = trace.confidence_score >= 0.75
    ? 'text-emerald-600'
    : trace.confidence_score >= 0.5
      ? 'text-amber-500'
      : 'text-rose-500';

  return (
    <details className="mt-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 text-xs">
      <summary className="cursor-pointer px-4 py-2 flex items-center gap-2 select-none hover:bg-slate-100 dark:hover:bg-slate-800/50 rounded-xl">
        <span>🔍</span>
        <span className={`px-2 py-0.5 rounded-full font-semibold text-[11px] ${modeColor}`}>
          {trace.recommended_mode}
        </span>
        <span className="text-slate-400">{trace.decision_rule_id}</span>
        <span className={`font-bold ${confColor}`}>conf: {trace.confidence_score.toFixed(2)}</span>
        {trace.sd_level && (
          <span className={`font-semibold uppercase text-[10px] ${sdColor}`}>
            SD: {trace.sd_level}
          </span>
        )}
        <span className="ml-auto text-slate-400">
          ✓{passedBlocks.length} ✕{filteredBlocks.length}
        </span>
      </summary>

      <div className="px-4 pb-4 pt-2 space-y-3 border-t border-slate-200 dark:border-slate-700">
        <details open>
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            📊 Роутинг и оркестрация
          </summary>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Режим</p>
              <p className={`font-bold px-1 rounded ${modeColor}`}>{trace.recommended_mode}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Правило</p>
              <p className="font-mono font-semibold text-slate-700 dark:text-slate-300">{trace.decision_rule_id}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Confidence</p>
              <p className={`font-bold ${confColor}`}>
                {trace.confidence_score.toFixed(3)} ({trace.confidence_level})
              </p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Состояние</p>
              <p className="font-semibold text-slate-700 dark:text-slate-300">{trace.user_state || '—'}</p>
            </div>
            {trace.sd_level && (
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">SD уровень</p>
                <p className={`font-bold uppercase ${sdColor}`}>{trace.sd_level}</p>
              </div>
            )}
            {trace.query_hash && (
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Query hash</p>
                <p className="font-mono text-[10px] text-slate-500 truncate">{trace.query_hash}</p>
              </div>
            )}
          </div>

          {trace.signals && Object.keys(trace.signals).length > 0 && (
            <div className="mt-2 rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Вклад сигналов</p>
              {Object.entries(trace.signals).map(([signal, value]) => (
                <div key={signal} className="flex items-center gap-2 mb-1">
                  <span className="text-slate-500 w-40 truncate">{signal}</span>
                  <div className="flex-1 h-1.5 rounded bg-slate-200 dark:bg-slate-700">
                    <div
                      className="h-1.5 rounded bg-emerald-500"
                      style={{ width: `${Math.min(value * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-slate-600 dark:text-slate-400 w-10 text-right">
                    {value.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </details>

        <details open>
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            ✓ Чанки в ответ ({passedBlocks.length})
          </summary>
          <div className="mt-2">
            {passedBlocks.length === 0
              ? <p className="text-slate-400 px-2">Нет принятых чанков</p>
              : passedBlocks.map((b) => <ChunkCard key={`${b.block_id}-${b.stage}`} block={b} passed={true} />)
            }
          </div>
        </details>

        {filteredBlocks.length > 0 && (
          <details>
            <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
              ✕ Отсеянные чанки ({filteredBlocks.length})
            </summary>
            <div className="mt-2">
              {filteredBlocks.map((b) => <ChunkCard key={`${b.block_id}-${b.stage}`} block={b} passed={false} />)}
            </div>
          </details>
        )}

        <details>
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            🧠 Контекст памяти
          </summary>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Memory turns</p>
              <p className="font-semibold">{trace.memory_turns ?? '—'}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Summary length</p>
              <p className="font-semibold">{trace.summary_length ?? '—'}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Summary last turn</p>
              <p className="font-semibold">{trace.summary_last_turn ?? '—'}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Summary</p>
              <p className="font-semibold">{trace.summary_used ? '✓ использован' : '—'}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Semantic hits</p>
              <p className="font-semibold">{trace.semantic_hits ?? '—'}</p>
            </div>
            {trace.prompt_overlay && (
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2 col-span-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">SD промпт оверлей</p>
                <p className="font-mono text-slate-700 dark:text-slate-300">{trace.prompt_overlay}</p>
              </div>
            )}
          </div>
        </details>
      </div>
    </details>
  );
};
