"""
scraper.py
- ソース1: @sachisuke_i の最新ツイート30件（get_user_tweets）
- ソース2: from:sachisuke_i で「【交換】」を最新順検索して50件（search_tweet）
- 2つをマージ・ID重複排除・日時降順ソート
- リポスト・返信を除外し、キーワードフィルター
- data/tweets.json と差分比較して新規分のみ追記
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

from twikit import Client  # twifork パッケージが提供する twikit 互換 Client

# ============ 設定 ============
TARGET_USER_ID   = "1637280719633534978"
TARGET_SCREEN    = "sachisuke_i"       # 検索演算子 from: 用
KEYWORDS         = ["【交換】", "【ゆる募・交換】"]
TIMELINE_COUNT   = 30                  # ソース1: 最新タイムライン
SEARCH_COUNT     = 50                  # ソース2: 検索結果
SEARCH_QUERY     = f'from:{TARGET_SCREEN} 【交換】'
DATA_FILE        = "data/tweets.json"
MAX_KEEP         = 300
# ==============================


def parse_cookies(cookie_str: str) -> dict:
    cookies = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        cookies[k.strip()] = v.strip()
    return cookies


def to_iso(dt) -> str:
    if isinstance(dt, str):
        try:
            d = datetime.strptime(dt, "%a %b %d %H:%M:%S %z %Y")
            return d.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            return dt
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(dt)


def load_existing() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"updated_at": None, "keywords": KEYWORDS, "tweets": []}


def save_data(data: dict) -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def serialize(tweet) -> dict:
    tid = str(tweet.id)
    return {
        "id": tid,
        "text": tweet.text,
        "created_at": to_iso(tweet.created_at),
        "url": f"https://twitter.com/{TARGET_SCREEN}/status/{tid}",
    }


async def fetch_timeline(client, user_id: str, limit: int) -> list:
    """get_user_tweets をページネーションして limit 件集める"""
    collected = []
    result = await client.get_user_tweets(user_id, "Tweets")

    while len(collected) < limit:
        for tweet in result:
            collected.append(tweet)
            if len(collected) >= limit:
                return collected

        if not getattr(result, "next_cursor", None):
            break

        try:
            result = await result.next()
        except Exception as e:
            print(f"タイムラインのページネーションでエラー: {type(e).__name__}: {e}", file=sys.stderr)
            break

        await asyncio.sleep(0.5)

    return collected


async def fetch_search(client, query: str, limit: int) -> list:
    """search_tweet をページネーションして limit 件集める（Latest順）"""
    collected = []
    result = await client.search_tweet(query, "Latest")

    while len(collected) < limit:
        for tweet in result:
            collected.append(tweet)
            if len(collected) >= limit:
                return collected

        if not getattr(result, "next_cursor", None):
            break

        try:
            result = await result.next()
        except Exception as e:
            print(f"検索のページネーションでエラー: {type(e).__name__}: {e}", file=sys.stderr)
            break

        await asyncio.sleep(0.5)

    return collected


async def main() -> None:
    # ---- 1. Cookie ----
    cookie_str = os.environ.get("X_COOKIES", "")
    if not cookie_str:
        print("ERROR: 環境変数 X_COOKIES が未設定です", file=sys.stderr)
        sys.exit(1)

    cookies = parse_cookies(cookie_str)
    if "auth_token" not in cookies or "ct0" not in cookies:
        print("ERROR: X_COOKIES に auth_token / ct0 が含まれていません", file=sys.stderr)
        sys.exit(1)

    # ---- 2. クライアント ----
    client = Client("ja")
    client.set_cookies(cookies)

    # ---- 3. 2ソースから取得 ----
    try:
        timeline_tweets = await fetch_timeline(client, TARGET_USER_ID, TIMELINE_COUNT)
        print(f"タイムライン取得: {len(timeline_tweets)} 件")
    except Exception as e:
        print(f"ERROR: タイムライン取得に失敗: {type(e).__name__}: {e}", file=sys.stderr)
        timeline_tweets = []

    try:
        search_tweets = await fetch_search(client, SEARCH_QUERY, SEARCH_COUNT)
        print(f"検索取得: {len(search_tweets)} 件（クエリ: {SEARCH_QUERY}）")
    except Exception as e:
        print(f"ERROR: 検索取得に失敗: {type(e).__name__}: {e}", file=sys.stderr)
        search_tweets = []

    # ---- 4. マージ & ID重複排除 ----
    by_id = {}
    for t in timeline_tweets + search_tweets:
        by_id[str(t.id)] = t

    merged_tweets = list(by_id.values())
    print(f"マージ後（重複排除済み）: {len(merged_tweets)} 件")

    if not merged_tweets:
        print("取得結果が0件でした。")
        return

    # ---- 5. フィルター（リポスト・返信除外 + キーワード） ----
    filtered = []
    for t in merged_tweets:
        if getattr(t, "retweeted_tweet", None) is not None:
            continue  # リポスト除外
        if getattr(t, "in_reply_to", None) is not None:
            continue  # 返信除外
        if any(kw in t.text for kw in KEYWORDS):
            filtered.append(t)

    print(f"フィルタ後: {len(filtered)} 件（リポスト・返信除外済み）")

    # ---- 6. 日時降順ソート ----
    filtered.sort(key=lambda t: to_iso(t.created_at), reverse=True)

    # ---- 7. 差分比較 ----
    existing = load_existing()
    existing_ids = {tw["id"] for tw in existing.get("tweets", [])}

    new_items = [
        serialize(t) for t in filtered
        if str(t.id) not in existing_ids
    ]

    if not new_items:
        print("新規ツイートはありません。")
        return

    print(f"新規 {len(new_items)} 件を検出")

    # ---- 8. マージ & 保存 ----
    merged_data = new_items + existing.get("tweets", [])
    seen = set()
    deduped = []
    for tw in merged_data:
        if tw["id"] in seen:
            continue
        seen.add(tw["id"])
        deduped.append(tw)
        if len(deduped) >= MAX_KEEP:
            break

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "keywords": KEYWORDS,
        "tweets": deduped,
    }
    save_data(data)
    print(f"{DATA_FILE} を更新しました（総 {len(deduped)} 件）")


if __name__ == "__main__":
    asyncio.run(main())