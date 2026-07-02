/** Centralized non-fatal error logging.
 *
 *  Use for failures we deliberately recover from (a settings save that fails, an
 *  optional fetch that errors) instead of an empty `.catch(() => {})` that hides
 *  the problem. Keeps a single seam so this can later forward to Sentry/PostHog
 *  without touching call sites. Intentionally side-effect-free beyond logging. */
export function logError(context: string, error: unknown): void {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`[kestrel] ${context}:`, message);
}
