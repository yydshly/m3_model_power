/**
 * runnerSession.ts — lightweight session persistence for CapabilityRunner.
 *
 * Saves:
 * - Last used input values per capability (form state)
 * - Result summary after successful invoke (URL, file_id, text excerpt)
 * - Handoff values
 *
 * Does NOT save: base64 audio/images, large payloads, raw API responses.
 *
 * Storage: sessionStorage (survives page refresh, not cross-tab).
 */

export type RunnerSession = {
  capabilityId: string
  createdAt: string
  inputValues: Record<string, string>
  resultSummary?: {
    ok: boolean
    outputType?: string
    textPreview?: string
    imageUrl?: string
    audioUrl?: string
    fileId?: string
    filename?: string
    mimeType?: string
  }
  handoff?: Record<string, string>
}

const PREFIX = 'runner_session:'

function _key(capId: string) {
  return `${PREFIX}${capId}`
}

export function saveRunnerSession(session: RunnerSession): void {
  try {
    // Only save small data — never large base64 or binary
    const toSave: RunnerSession = {
      ...session,
      // Ensure we don't save huge strings
      createdAt: session.createdAt,
      inputValues: session.inputValues,
      resultSummary: session.resultSummary,
      handoff: session.handoff,
    }
    sessionStorage.setItem(_key(session.capabilityId), JSON.stringify(toSave))
  } catch {
    // Storage full or unavailable — skip silently
  }
}

export function loadRunnerSession(capId: string): RunnerSession | null {
  try {
    const raw = sessionStorage.getItem(_key(capId))
    if (!raw) return null
    return JSON.parse(raw) as RunnerSession
  } catch {
    return null
  }
}

export function clearRunnerSession(capId: string): void {
  sessionStorage.removeItem(_key(capId))
}
