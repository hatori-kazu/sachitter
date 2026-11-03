export function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('ja-JP', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

export function renderKeywords(keywords, container) {
  container.innerHTML = '';
  (keywords || []).forEach((kw) => {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = `# ${kw}`;
    container.appendChild(chip);
  });
}

export function createCard(tweet, index) {
  const card = document.createElement('article');
  card.className = 'tweet-card';
  card.style.animationDelay = `${index * 60}ms`;

  const meta = document.createElement('div');
  meta.className = 'tweet-card__meta';

  const date = document.createElement('span');
  date.className = 'tweet-card__date';
  date.textContent = formatDate(tweet.created_at);
  meta.appendChild(date);

  if (tweet.url) {
    const link = document.createElement('a');
    link.className = 'tweet-card__link';
    link.href = tweet.url;
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = 'Xで見る ↗';
    meta.appendChild(link);
  }

  const text = document.createElement('div');
  text.className = 'tweet-card__text';
  text.textContent = tweet.text;

  card.append(meta, text);
  return card;
}

export function observeCards(cards) {
  if (!('IntersectionObserver' in window)) {
    cards.forEach((c) => c.classList.add('is-visible'));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });
  cards.forEach((c) => io.observe(c));
}