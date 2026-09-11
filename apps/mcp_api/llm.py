import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_MCP = (
    "Eres el asistente de gestión del negocio del usuario. "
    "Usa las herramientas disponibles para responder con datos reales del tenant. "
    "Responde de forma breve, clara y útil, en español. "
    "Si el usuario saluda o pregunta algo general, responde con un saludo y ofrece ayuda."
)


def _resolve_provider():
    provider = getattr(settings, 'LLM_PROVIDER', '') or ''
    model = getattr(settings, 'LLM_MODEL', '') or ''
    base = getattr(settings, 'LLM_BASE_URL', '') or ''
    api_key = getattr(settings, 'LLM_API_KEY', '') or ''

    if not provider:
        deepseek = getattr(settings, 'DEEPSEEK_API_KEY', '') or ''
        openai_key = getattr(settings, 'OPENAI_API_KEY', '') or ''
        gemini_key = getattr(settings, 'GEMINI_API_KEY', '') or ''
        if deepseek:
            provider = 'deepseek'
        elif openai_key:
            provider = 'openai'
        elif gemini_key:
            provider = 'gemini'
        else:
            return None

    if not base:
        base = {
            'deepseek': 'https://api.deepseek.com',
            'openai': 'https://api.openai.com/v1',
            'gemini': 'https://generativelanguage.googleapis.com/v1beta/openai',
        }.get(provider, 'https://api.deepseek.com')

    if not model:
        model = {
            'deepseek': getattr(settings, 'DEEPSEEK_MODEL', '') or 'deepseek-chat',
            'openai': getattr(settings, 'OPENAI_MODEL', '') or 'gpt-4o-mini',
            'gemini': getattr(settings, 'GEMINI_MODEL', '') or 'gemini-2.0-flash',
        }.get(provider, 'deepseek-chat')

    if not api_key:
        api_key = getattr(settings, 'DEEPSEEK_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '') or getattr(settings, 'GEMINI_API_KEY', '') or ''
    if not api_key:
        return None

    return {'base': base.rstrip('/'), 'model': model, 'key': api_key}


def _chat_completions(messages, tools=None):
    cfg = _resolve_provider()
    if not cfg:
        raise RuntimeError("No hay clave LLM configurada.")

    url = f"{cfg['base']}/chat/completions"
    payload = {
        "model": cfg['model'],
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 800,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    headers = {"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, timeout=60)

    if r.status_code >= 500:
        logger.error("LLM server error %s: %s", r.status_code, r.text[:300])
        raise RuntimeError("LLM server error")
    if r.status_code != 200:
        logger.warning("LLM bad request %s: %s", r.status_code, r.text[:500])
        raise RuntimeError("LLM request failed")

    data = r.json()
    choice = data.get('choices', [{}])[0]
    msg = choice.get('message', {})
    tool_calls = msg.get('tool_calls') or []
    return {"content": msg.get('content') or "", "tool_calls_raw": tool_calls}


def run_tool_chat(tenant, history, user_message, tools, tool_map, system=None):
    if system is None:
        system = SYSTEM_PROMPT_MCP

    messages = [{"role": "system", "content": system}]
    for h in history[-20:]:
        role = h.get('role')
        if role in ('user', 'assistant') and h.get('text'):
            messages.append({"role": role, "content": h['text']})
    messages.append({"role": "user", "content": user_message})

    tool_names_called = []
    last_tool_data = None

    for _ in range(3):
        try:
            res = _chat_completions(messages, tools=tools)
        except Exception:
            if not tool_names_called:
                raise
            return None, tool_names_called, last_tool_data

        if not res["tool_calls_raw"]:
            return res["content"], tool_names_called, last_tool_data

        assistant_msg = {
            "role": "assistant",
            "content": res["content"] or None,
            "tool_calls": res["tool_calls_raw"],
        }
        messages.append(assistant_msg)

        for tc in res["tool_calls_raw"]:
            fn = tc.get("function", {})
            name = fn.get("name")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            tool_names_called.append(name)
            try:
                result = tool_map[name](tenant=tenant, **args)
                last_tool_data = result
                content = json.dumps(result, ensure_ascii=False, default=str)[:2000]
            except Exception as e:
                content = f"Error al ejecutar {name}: {e}"
                logger.exception("LLM tool execution error: %s", name)
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": content})

    try:
        res = _chat_completions(messages)
        return res["content"], tool_names_called, last_tool_data
    except Exception:
        return None, tool_names_called, last_tool_data


def ask_llm_simple(prompt, system=None):
    cfg = _resolve_provider()
    if not cfg:
        return None

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        res = _chat_completions(messages)
        return res["content"] or ""
    except Exception as e:
        logger.error("LLM simple error: %s", e)
        return None
