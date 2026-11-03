const DATA_URL = 'data/tweets.json';

export async function fetchTweets() {
  try {
    // キャッシュ回避のためタイムスタンプを付与
    const res = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Failed to load tweets.json:', err);
    return { updated_at: null, keywords: [], tweets: [] };
  }
}