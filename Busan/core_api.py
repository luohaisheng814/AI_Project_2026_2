# -*- coding: utf-8 -*-
# """
#core_api.py —— LLM 接口层（OpenAI 兼容协议）
#--------------------------------------------------
#一处配置通吃多家：

import requests

import config


def is_configured():
    return bool(config.LLM_API_KEY)


def _endpoint():
    return config.LLM_BASE_URL.rstrip("/") + "/chat/completions"


def chat(messages, temperature=None, timeout=None, model=None):
    """成功 -> 返回模型输出字符串；失败 -> 返回 None（由上层降级）。"""
    if not is_configured():
        return None

    payload = {
        "model": model or config.LLM_MODEL,
        "messages": messages,
        "temperature": config.LLM_TEMPERATURE if temperature is None else temperature,
        "stream": False,
    }
    headers = {
        "Authorization": "Bearer " + config.LLM_API_KEY,
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(_endpoint(), headers=headers, json=payload,
                          timeout=timeout or config.LLM_TIMEOUT)
        if r.status_code != 200:
            return None
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:      # noqa: BLE001  网络/解析异常一律降级
        return None


def complete(system, user, **kw):
    """便捷写法：直接给 system / user 两段文本。"""
    return chat([{"role": "system", "content": system},
                 {"role": "user", "content": user}], **kw)


if __name__ == "__main__":
    print("is_configured:", is_configured())
    if is_configured():
        print(complete("你只回答两个字：你好", "打个招呼"))