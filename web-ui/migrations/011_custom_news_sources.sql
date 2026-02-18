-- Migration 011: Custom news sources (URLs, RSS, Telegram, WhatsApp manual)
-- Run this on existing production databases that were initialized before this migration.

CREATE TABLE IF NOT EXISTS custom_news_sources (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  source_type TEXT NOT NULL
    CHECK (source_type IN ('url', 'rss', 'telegram_public', 'telegram_bot', 'manual')),
  source_url TEXT,
  bot_token TEXT,
  chat_id TEXT,
  language TEXT DEFAULT 'auto',
  is_active BOOLEAN DEFAULT TRUE,
  fetch_interval_hours INTEGER DEFAULT 6,
  last_fetched_at TIMESTAMPTZ,
  telegram_offset BIGINT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS custom_source_articles (
  id SERIAL PRIMARY KEY,
  source_id INTEGER REFERENCES custom_news_sources(id) ON DELETE CASCADE,
  content_text TEXT NOT NULL,
  content_type TEXT NOT NULL DEFAULT 'text'
    CHECK (content_type IN ('text', 'image', 'pdf', 'url_article')),
  original_url TEXT,
  external_id TEXT,
  language TEXT,
  sentiment_score REAL,
  sentiment_label TEXT,
  sentiment_processed BOOLEAN DEFAULT FALSE,
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  message_date TIMESTAMPTZ,
  UNIQUE(source_id, external_id)
);

CREATE INDEX IF NOT EXISTS idx_custom_articles_source
  ON custom_source_articles(source_id, fetched_at DESC);
