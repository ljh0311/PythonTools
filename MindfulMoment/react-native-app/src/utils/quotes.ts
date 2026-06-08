/**
 * Fetch a random quote from Quotable.io (free, no API key).
 * Returns null on network error or non-2xx so caller can use local fallback.
 */
const QUOTABLE_URL = 'https://api.quotable.io/random';

export interface QuoteResult {
  text: string;
  author: string | null;
}

export async function fetchRandomQuote(): Promise<QuoteResult | null> {
  try {
    const res = await fetch(QUOTABLE_URL);
    if (!res.ok) return null;
    const data = (await res.json()) as { content?: string; author?: string };
    const text = data?.content?.trim();
    if (!text) return null;
    return {
      text,
      author: data?.author?.trim() || null,
    };
  } catch {
    return null;
  }
}

export const FALLBACK_QUOTES: string[] = [
  'Every moment of awareness is a step toward mindfulness.',
  'Your phone is a tool, not your life.',
  'The present moment is the only moment available to us.',
  'Small mindful moments add up to a mindful life.',
  'Disconnect to reconnect with what matters most.',
];
