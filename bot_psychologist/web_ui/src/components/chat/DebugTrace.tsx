import { useState, type ReactNode } from 'react';
import type { ChunkTraceItem, DebugTrace as DebugTraceData } from '../../types';

const SD_COLORS: Record<string, string> = {
  BEIGE: '#FEF9C3',
  PURPLE: '#F3E8FF',
  RED: '#FFE4E6',
  BLUE: '#DBEAFE',
  ORANGE: '#FFEDD5',
  GREEN: '#DCFCE7',
  YELLOW: '#FEF9C3',
  TURQUOISE: '#CCFBF1',
};

interface ChunkBadgeProps {
  chunk: ChunkTraceItem;
}

function ChunkBadge({ chunk }: ChunkBadgeProps) {
  const cardBg = chunk.passed_sd_filter ? '#DCFCE7' : '#FFE4E6';
  const sdBg = SD_COLORS[chunk.sd_level] || '#F4F4F5';

  return (
    <div style={{ background: cardBg, borderRadius: 8, padding: '6px 10px', marginBottom: 6 }}>
      <div>
        <span style={{ background: sdBg, borderRadius: 4, padding: '1px 6px', fontSize: 11, marginRight: 6 }}>
          {chunk.sd_level}
        </span>
        <b>{chunk.title}</b>
      </div>
      <div style={{ color: '#71717A', fontSize: 11, marginTop: 2 }}>
        score: {chunk.score_initial.toFixed(3)} -&gt; {chunk.score_final.toFixed(3)}
        {chunk.sd_secondary && <span style={{ marginLeft: 8 }}>2°: {chunk.sd_secondary}</span>}
        {chunk.emotional_tone && <span style={{ marginLeft: 8 }}>tone: {chunk.emotional_tone}</span>}
        {!chunk.passed_sd_filter && (
          <span style={{ color: '#EF4444', marginLeft: 8 }}>
            x {chunk.filter_reason}
          </span>
        )}
      </div>
      <div style={{ color: '#A1A1AA', fontSize: 11, marginTop: 2 }}>
        {chunk.preview}
      </div>
    </div>
  );
}

interface SectionProps {
  label: string;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}

function Section({ label, open, onToggle, children }: SectionProps) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div
        onClick={onToggle}
        style={{
          cursor: 'pointer',
          padding: '6px 0',
          fontWeight: 600,
          fontSize: 12,
          color: '#3F3F46',
          borderBottom: '1px solid #E4E4E7',
          userSelect: 'none',
        }}
      >
        {open ? '▾' : '▸'} {label}
      </div>
      {open && <div style={{ paddingTop: 8 }}>{children}</div>}
    </div>
  );
}

interface DebugTraceProps {
  trace: DebugTraceData;
}

export function DebugTrace({ trace }: DebugTraceProps) {
  const [open, setOpen] = useState({
    sd: true,
    chunks: true,
    filtered: false,
    llm: false,
    memory: false,
  });

  const toggle = (key: keyof typeof open) => setOpen((prev) => ({ ...prev, [key]: !prev[key] }));
  const sd = trace.sd_classification;

  return (
    <div
      style={{
        width: 420,
        flexShrink: 0,
        borderLeft: '1px solid #E4E4E7',
        overflowY: 'auto',
        background: '#FAFAFA',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12,
        padding: 12,
      }}
    >
      <div
        style={{
          fontWeight: 700,
          fontSize: 13,
          marginBottom: 12,
          borderBottom: '1px solid #E4E4E7',
          paddingBottom: 8,
          color: '#18181B',
        }}
      >
        Debug Trace
        <span style={{ color: '#71717A', fontWeight: 400, marginLeft: 8 }}>
          {trace.total_duration_ms}ms
        </span>
      </div>

      <Section label="A - SD-классификация" open={open.sd} onToggle={() => toggle('sd')}>
        <div style={{ lineHeight: 1.8 }}>
          <div>
            <b>Уровень:</b>{' '}
            <span style={{ background: SD_COLORS[sd.primary] || '#F4F4F5', borderRadius: 4, padding: '1px 8px' }}>
              {sd.primary}
            </span>
            {sd.secondary && <span style={{ color: '#71717A' }}> / {sd.secondary}</span>}
          </div>
          <div><b>Метод:</b> {sd.method}</div>
          <div><b>Confidence:</b> {(sd.confidence * 100).toFixed(0)}%</div>
          <div><b>Маркер:</b> {sd.indicator}</div>
          <div><b>Разрешены:</b> {sd.allowed_levels.join(', ')}</div>
        </div>
      </Section>

      <Section
        label={`B - Чанки из ChromaDB (${trace.chunks_retrieved.length})`}
        open={open.chunks}
        onToggle={() => toggle('chunks')}
      >
        {trace.chunks_retrieved.map((chunk) => (
          <ChunkBadge key={`retrieved-${chunk.block_id}`} chunk={chunk} />
        ))}
      </Section>

      <Section
        label={`C - После SD-фильтра (${trace.chunks_after_sd_filter.length})`}
        open={open.filtered}
        onToggle={() => toggle('filtered')}
      >
        {trace.chunks_after_sd_filter.map((chunk) => (
          <ChunkBadge key={`filtered-${chunk.block_id}`} chunk={chunk} />
        ))}
      </Section>

      <Section
        label={`D - LLM вызовы (${trace.llm_calls.length})`}
        open={open.llm}
        onToggle={() => toggle('llm')}
      >
        {trace.llm_calls.map((call, index) => (
          <div key={index} style={{ marginBottom: 10, padding: 8, background: '#F4F4F5', borderRadius: 8 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {call.step} - {call.model}
              {call.duration_ms ? (
                <span style={{ color: '#71717A', fontWeight: 400 }}> · {call.duration_ms}ms</span>
              ) : null}
              {call.tokens_used ? (
                <span style={{ color: '#71717A', fontWeight: 400 }}> · {call.tokens_used} tok</span>
              ) : null}
            </div>
            <details>
              <summary style={{ color: '#6366F1', cursor: 'pointer' }}>System prompt</summary>
              <pre style={{ whiteSpace: 'pre-wrap', color: '#3F3F46', fontSize: 11, marginTop: 4 }}>
                {call.system_prompt_preview}
              </pre>
            </details>
            <details>
              <summary style={{ color: '#6366F1', cursor: 'pointer' }}>User prompt</summary>
              <pre style={{ whiteSpace: 'pre-wrap', color: '#3F3F46', fontSize: 11, marginTop: 4 }}>
                {call.user_prompt_preview}
              </pre>
            </details>
            <details>
              <summary style={{ color: '#059669', cursor: 'pointer' }}>Ответ LLM</summary>
              <pre style={{ whiteSpace: 'pre-wrap', color: '#3F3F46', fontSize: 11, marginTop: 4 }}>
                {call.response_preview}
              </pre>
            </details>
          </div>
        ))}
      </Section>

      <Section label="E - Записано в память" open={open.memory} onToggle={() => toggle('memory')}>
        <pre style={{ whiteSpace: 'pre-wrap', color: '#3F3F46', fontSize: 11 }}>
          {trace.context_written_to_memory || '-'}
        </pre>
      </Section>
    </div>
  );
}
