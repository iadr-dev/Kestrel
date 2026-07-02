/** Run an async mapper over `items` with at most `limit` in flight at once.
 *
 *  Replaces unbounded `Promise.all(items.map(fetch))`, which fires every request
 *  simultaneously — fine for a handful of ids, but a 40-stock watchlist would
 *  open 40 parallel connections and can overwhelm the browser's per-host socket
 *  pool and the backend. Order of results matches input order; a rejected item
 *  rejects the whole batch (mirror `Promise.all`), so callers that want
 *  graceful degradation should catch inside `fn`. */
export async function mapLimit<T, R>(
  items: readonly T[],
  limit: number,
  fn: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  if (items.length === 0) return [];
  const size = Math.max(1, Math.min(limit, items.length));
  const results = new Array<R>(items.length);
  let cursor = 0;

  async function worker(): Promise<void> {
    while (cursor < items.length) {
      const i = cursor++;
      results[i] = await fn(items[i], i);
    }
  }

  await Promise.all(Array.from({ length: size }, worker));
  return results;
}
