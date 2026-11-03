import { fetchTweets } from './fetch-tweets.js';
import {
  renderKeywords,
  createCard,
  formatDate,
  observeCards,
} from './render.js';

// ===== 設定 =====
const MIN_LOADER_MS  = 3000;  // ローダー最低表示時間
const REVEAL_DELAY_MS = 350;  // ヒーロー出現後にカードを出し始めるまで
const LOADER_FADE_MS  = 650;  // loader.css の transition と揃える
// =================

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function boot() {
  const loaderEl  = document.getElementById('loader');
  const listEl    = document.getElementById('tweet-list');
  const emptyEl   = document.getElementById('empty-state');
  const updatedEl = document.getElementById('last-updated');
  const chipsEl   = document.getElementById('keyword-chips');

  const startedAt = performance.now();

  // ---- データ取得と最低表示時間を並行で待つ ----
  const [data] = await Promise.all([
    fetchTweets(),
    wait(Math.max(0, MIN_LOADER_MS - (performance.now() - startedAt))),
  ]);

  // ---- ローダーの裏で DOM を構築 ----
  listEl.innerHTML = '';
  renderKeywords(data.keywords, chipsEl);

  updatedEl.textContent = data.updated_at
    ? `最終更新：${formatDate(data.updated_at)}`
    : '最終更新：取得できませんでした';

  const hasTweets = Array.isArray(data.tweets) && data.tweets.length > 0;
  let cards = [];

  if (hasTweets) {
    cards = data.tweets.map((t, i) => createCard(t, i));
    cards.forEach((c) => listEl.appendChild(c));
  } else {
    emptyEl.hidden = false;
  }

  // ---- 1フレーム待ってからローダーを外し、ページを展開 ----
  await new Promise((resolve) => requestAnimationFrame(() => resolve()));

  loaderEl.classList.add('is-hidden');
  document.body.classList.remove('is-loading');
  document.body.classList.add('is-ready');

  // ヒーローのアニメが少し進んでからカードを出現させる
  if (hasTweets) {
    setTimeout(() => observeCards(cards), REVEAL_DELAY_MS);
  }

  // フェード完了後にローダー DOM を削除
  setTimeout(() => loaderEl.remove(), LOADER_FADE_MS + 100);
}

boot().catch((err) => {
  console.error('Boot error:', err);
  // 想定外の失敗時も最低限ページを表示
  setTimeout(() => {
    const loaderEl = document.getElementById('loader');
    if (loaderEl) loaderEl.classList.add('is-hidden');
    document.body.classList.remove('is-loading');
    document.body.classList.add('is-ready');
  }, MIN_LOADER_MS);
});