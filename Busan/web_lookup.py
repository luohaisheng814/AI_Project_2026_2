# -*- coding: utf-8 -*-


import re

import requests
from bs4 import BeautifulSoup

import config

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def extract_urls(text):
    """从文本抽取所有 http(s) 链接，去重保序。"""
    urls = re.findall(r"https?://[^\s，,；;）)\]】\"']+", text or "")
    out = []
    for u in urls:
        u = u.rstrip("、。.,;)）]】")
        if u not in out:
            out.append(u)
    return out


def _clean(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    return re.sub(r"\s{2,}", " ", soup.get_text(" ", strip=True))


def _best_snippet(text, keywords, max_chars):
    """找包含关键词的窗口，找不到则返回开头部分。"""
    if not text:
        return ""
    for k in (keywords or []):
        if k and len(k) >= 2:
            pos = text.find(k)
            if pos >= 0:
                return text[max(0, pos - 400):max(0, pos - 400) + max_chars]
    return text[:max_chars]


def fetch_url(url, max_chars=2500, keywords=None):
    """抓取一个 URL，返回 {"url","title","snippet"} 或 None。"""
    try:
        r = requests.get(url, headers={"User-Agent": UA,
                                       "Accept-Language": "zh-CN,zh;q=0.9,ko;q=0.8,en;q=0.7"},
                         timeout=config.WEB_TIMEOUT)
        if r.status_code != 200:
            return None
        try:
            html = r.content.decode(r.encoding or "utf-8", errors="ignore")
        except Exception:
            html = r.text
        if "<html" not in html.lower() and len(html) < 200:
            return None

        title = ""
        try:
            soup = BeautifulSoup(html, "html.parser")
            title = (soup.title.string or "").strip() if soup.title else ""
        except Exception:
            pass

        snippet = _best_snippet(_clean(html), keywords, max_chars)
        if not snippet:
            return None
        return {"url": url, "title": title[:120], "snippet": snippet}
    except Exception:
        return None


def lookup(urls, keywords=None, max_pages=3):
    """批量查询；ENABLE_WEB_LOOKUP=False 时直接返回空列表。"""
    if not config.ENABLE_WEB_LOOKUP or not urls:
        return []
    results = []
    for u in urls[:max_pages]:
        r = fetch_url(u, keywords=keywords)
        if r:
            results.append(r)
    return results