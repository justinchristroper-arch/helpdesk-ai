"""One model-catalog read plus one minimal MindRouter chat request.

This diagnostic deliberately excludes structured output, tools, sampling,
reasoning and provider extensions. It never prints the API key or raw headers.
"""
import json
import os
import re

import httpx

from app.config import get_settings

if os.getenv("RUN_MINDROUTER_DIAGNOSTIC") != "1":
    raise SystemExit("Set RUN_MINDROUTER_DIAGNOSTIC=1 to authorize one model-list read and one smoke request.")

settings = get_settings()
key = settings.mindrouter_api_key.get_secret_value() if settings.mindrouter_api_key else ""
if not key:
    raise SystemExit("MindRouter key is absent; no external request made.")

base_url = settings.mindrouter_base_url.rstrip("/")
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
request_counts = {"models": 0, "chat_completions": 0}


def safe_message(value):
    if not isinstance(value, str):
        return None
    value = value.replace(key, "[REDACTED]")
    value = re.sub(r"sk_[A-Za-z0-9_-]{10,}", "[REDACTED]", value)
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", value)
    return value[:500]


def safe_error(response):
    try:
        data = response.json()
    except ValueError:
        return {"body_type": "non_json", "body_length": len(response.content)}
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        return {"body_type": "json", "root_keys": sorted(data), "error_keys": sorted(error),
                "type": error.get("type"), "code": error.get("code"),
                "message": safe_message(error.get("message"))}
    return {"body_type": "json", "root_keys": sorted(data) if isinstance(data, dict) else [],
            "error_type": type(error).__name__}


report = {
    "endpoint": base_url,
    "configured_model": settings.mindrouter_model,
    "model_catalog": None,
    "minimal_request": {
        "field_names": ["model", "messages", "max_tokens"],
        "model": settings.mindrouter_model,
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "max_tokens": 16,
        "excluded_fields": ["temperature", "stream", "response_format", "json_schema", "reasoning_effort",
                            "thinking", "tools", "tool_choice", "provider_extensions"],
    },
}

with httpx.Client(timeout=httpx.Timeout(25, connect=5), trust_env=False) as client:
    request_counts["models"] += 1
    models_response = client.get(base_url + "/models", headers=headers)
    if models_response.is_success:
        models_data = models_response.json()
        rows = models_data.get("data") if isinstance(models_data, dict) else None
        ids = sorted(item["id"] for item in rows
                     if isinstance(item, dict) and isinstance(item.get("id"), str)) if isinstance(rows, list) else []
        deepseek_ids = [model_id for model_id in ids if "deepseek" in model_id.lower()]
        report["model_catalog"] = {"http_status": models_response.status_code, "total_models": len(ids),
                                   "deepseek_model_ids": deepseek_ids,
                                   "configured_model_exact_match": settings.mindrouter_model in ids}
    else:
        report["model_catalog"] = {"http_status": models_response.status_code,
                                   "error": safe_error(models_response)}

    payload = {"model": settings.mindrouter_model,
               "messages": [{"role": "user", "content": "Reply with OK."}],
               "max_tokens": 16}
    request_counts["chat_completions"] += 1
    response = client.post(base_url + "/chat/completions", headers=headers, json=payload)
    if response.is_success:
        data = response.json()
        usage = data.get("usage") if isinstance(data, dict) else None
        choices = data.get("choices") if isinstance(data, dict) else None
        choice = choices[0] if isinstance(choices, list) and choices else None
        message = choice.get("message") if isinstance(choice, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        report["smoke_response"] = {
            "http_status": response.status_code, "success": True,
            "reported_model": data.get("model") if isinstance(data, dict) else None,
            "input_tokens": usage.get("prompt_tokens") if isinstance(usage, dict) else None,
            "output_tokens": usage.get("completion_tokens") if isinstance(usage, dict) else None,
            "finish_reason": choice.get("finish_reason") if isinstance(choice, dict) else None,
            "content_type": type(content).__name__,
            "content_length": len(content) if isinstance(content, str) else None,
            "content_nonempty": bool(content) if isinstance(content, str) else False,
        }
    else:
        report["smoke_response"] = {"http_status": response.status_code, "success": False,
                                    "error": safe_error(response)}

report["external_requests"] = request_counts
print(json.dumps(report, indent=2))
