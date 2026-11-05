# -*- coding: utf-8 -*-


import re

import requests
from bs4 import BeautifulSoup

import config

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 韩国政府/区厅站点对「无 Cookie 直连」会返回 403，用一个常驻会话先访问站点首页预热
_SESSION = requests.Session()
_WARMED = set()

# 实测抓不到的站点：visitbusan.net 正文由前端渲染，服务端只能拿到 6KB 的 JS 壳，抓了也没意义
_SKIP_HOSTS = ("visitbusan.net",)


def _root_of(url):
    try:
        return "https://" + url.split("://", 1)[1].split("/", 1)[0] + "/"
    except Exception:
        return ""


def _get(url, timeout=None):
    """带会话与站点预热的 GET：403 时补 Referer 并先访问一次站点首页拿 Cookie。"""
    headers = {"User-Agent": UA,
               # 注意：韩国区厅官网的防火墙会把 Accept-Language: zh-CN 判为异常请求直接 403，
               # 这里固定用韩文语种头（实测 ko-KR / en-US 均 200，zh-CN 必 403）
               "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}
    timeout = timeout or config.WEB_TIMEOUT
    r = _SESSION.get(url, headers=headers, timeout=timeout)
    if r.status_code in (401, 403):
        root = _root_of(url)
        if root and root not in _WARMED:
            try:
                _SESSION.get(root, headers=headers, timeout=timeout)
            except Exception:
                pass
            _WARMED.add(root)
        if root:
            headers["Referer"] = root
        r = _SESSION.get(url, headers=headers, timeout=timeout)
    return r



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


def _body_text(soup, prefer_ids=()):
    """优先取正文容器（如沙下区官网的 #conts / #contents），避免抓到导航菜单。"""
    if prefer_ids:
        for pid in prefer_ids:
            box = soup.find(id=pid)
            if box is not None:
                txt = re.sub(r"\s{2,}", " ", box.get_text(" ", strip=True))
                if len(txt) >= 80:
                    return txt
    return _clean(str(soup))


def fetch_url(url, max_chars=2500, keywords=None, prefer_ids=()):
    """抓取一个 URL，返回 {"url","title","snippet"} 或 None。"""
    if any(h in (url or "") for h in _SKIP_HOSTS):
        return None
    try:
        r = _get(url)
        if r.status_code != 200:
            return None
        try:
            html = r.content.decode(r.encoding or "utf-8", errors="ignore")
        except Exception:
            html = r.text
        if "<html" not in html.lower() and len(html) < 200:
            return None

        soup = BeautifulSoup(html, "html.parser")
        title = ""
        try:
            title = (soup.title.string or "").strip() if soup.title else ""
        except Exception:
            pass

        snippet = _best_snippet(_body_text(soup, prefer_ids), keywords, max_chars)
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