import React, { useMemo, useState } from 'react';

import type {
  DiagnosticCenterControlUpdateRequest,
  DiagnosticCenterEffectiveResponse,
} from '../../types/admin.types';

type Props = {
  data: DiagnosticCenterEffectiveResponse | null;
  onRefresh: () => Promise<void> | void;
  onSave: (payload: DiagnosticCenterControlUpdateRequest) => Promise<void> | void;
  onReset: () => Promise<void> | void;
  isSaving: boolean;
};

function normalizeAllowlist(text: string): string[] {
  const rows = text.replaceAll(',', '\n').split('\n').map((row) => row.trim()).filter(Boolean);
  const uniq = Array.from(new Set(rows));
  return uniq.slice(0, 128);
}

export const DiagnosticCenterTab: React.FC<Props> = ({ data, onRefresh, onSave, onReset, isSaving }) => {
  const [mode, setMode] = useState<string>('creator_only');
  const [forceDisabled, setForceDisabled] = useState<boolean>(false);
  const [allowlistText, setAllowlistText] = useState<string>('');
  const [reason, setReason] = useState<string>('manual_admin_update');

  React.useEffect(() => {
    if (!data) return;
    setMode(data.control_state.mode || data.current_mode);
    setForceDisabled(Boolean(data.control_state.force_disabled));
    setAllowlistText((data.control_state.allowlist_user_ids || []).join('\n'));
  }, [data]);

  const boundary = data?.boundary_flags;
  const isDeveloperAllUsers = mode === 'developer_local_all_users';
  const savePayload = useMemo<DiagnosticCenterControlUpdateRequest>(
    () => ({
      mode,
      force_disabled: forceDisabled,
      allowlist_user_ids: normalizeAllowlist(allowlistText),
      reason,
    }),
    [allowlistText, forceDisabled, mode, reason]
  );

  return (
    <div className="mt-4 space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold text-slate-800">Diagnostic Center Control</h3>
          <button
            type="button"
            onClick={() => void onRefresh()}
            className="ml-auto rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
          >
            Refresh
          </button>
        </div>
        {data ? (
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4 text-sm">
            <div className="rounded border border-slate-200 p-3">
              <div className="text-xs text-slate-500">Status</div>
              <div className="font-medium text-slate-800">{data.status}</div>
            </div>
            <div className="rounded border border-slate-200 p-3">
              <div className="text-xs text-slate-500">Current mode</div>
              <div className="font-medium text-slate-800">{data.current_mode}</div>
            </div>
            <div className="rounded border border-slate-200 p-3">
              <div className="text-xs text-slate-500">Effective active</div>
              <div className="font-medium text-slate-800">{data.effective_active ? 'true' : 'false'}</div>
            </div>
            <div className="rounded border border-slate-200 p-3">
              <div className="text-xs text-slate-500">Last PRD / timeout</div>
              <div className="font-medium text-slate-800">
                {data.last_evidence?.last_prd ?? 'n/a'} / {data.last_evidence?.recommended_runner_timeout_sec ?? 0}s
              </div>
            </div>
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">No data loaded.</p>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h4 className="text-sm font-semibold text-slate-800">Runtime Mode</h4>
        <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
          {(data?.available_modes || ['disabled', 'shadow', 'developer', 'creator_only', 'allowlist', 'developer_local_all_users']).map((value) => (
            <label key={value} className="flex items-center gap-2 rounded border border-slate-200 px-3 py-2 text-sm">
              <input
                type="radio"
                name="dc_mode"
                checked={mode === value}
                onChange={() => setMode(value)}
              />
              <span>{value}</span>
            </label>
          ))}
        </div>
        {isDeveloperAllUsers && (
          <div className="mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            Этот режим доступен для single-developer local testing и не означает production-ready broad rollout.
          </div>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h4 className="text-sm font-semibold text-slate-800">Kill Switch</h4>
        <label className="mt-2 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={forceDisabled} onChange={(e) => setForceDisabled(e.target.checked)} />
          <span>force_disabled</span>
        </label>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h4 className="text-sm font-semibold text-slate-800">Allowlist</h4>
        <textarea
          value={allowlistText}
          onChange={(e) => setAllowlistText(e.target.value)}
          placeholder="creator&#10;pilot_runtime_operator_001"
          className="mt-2 min-h-28 w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="reason"
          className="mt-2 w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h4 className="text-sm font-semibold text-slate-800">Boundary Flags</h4>
        <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2 text-sm">
          <div className="rounded border border-slate-200 px-3 py-2">production_ready={String(Boolean(boundary?.production_ready))}</div>
          <div className="rounded border border-slate-200 px-3 py-2">broad_rollout_allowed={String(Boolean(boundary?.broad_rollout_allowed))}</div>
          <div className="rounded border border-slate-200 px-3 py-2">normal_user_activation_allowed={String(Boolean(boundary?.normal_user_activation_allowed))}</div>
          <div className="rounded border border-slate-200 px-3 py-2">external_users_allowed={String(Boolean(boundary?.external_users_allowed))}</div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={isSaving}
            onClick={() => void onSave(savePayload)}
            className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-900 disabled:opacity-50"
          >
            Save
          </button>
          <button
            type="button"
            disabled={isSaving}
            onClick={() => void onReset()}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Reset safe default
          </button>
        </div>
      </section>
    </div>
  );
};
