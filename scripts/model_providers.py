#!/usr/bin/env python3
"""Explicitly selected news-desk AI provider; never spend on a hidden fallback.

Default remains Gemini. OpenAI/Anthropic cannot be called unless a repository
variable selects that provider AND its separate secret is configured.
"""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
from ai_newsroom import fetch_gemini, MODEL as GEMINI_MODEL

PROVIDER=os.getenv("BRIEF_AI_PROVIDER","gemini").strip().lower()
MODELS={
    "gemini":GEMINI_MODEL,
    "openai":os.getenv("OPENAI_MODEL","gpt-6-luna"),
    "anthropic":os.getenv("ANTHROPIC_MODEL","claude-haiku-5-5"),
}
if PROVIDER != "gemini":
    raise RuntimeError("Only Gemini is authorised. Paid providers require an explicit reviewed code change.")
if PROVIDER not in MODELS:
    raise RuntimeError("Unknown BRIEF_AI_PROVIDER (must be gemini, openai or anthropic)")
ACTIVE_MODEL=PROVIDER+":"+MODELS[PROVIDER]

def parse_object(raw):
    if isinstance(raw,dict):
        return raw
    if not isinstance(raw,str) or not raw.strip():
        raise RuntimeError("AI provider returned empty JSON")
    try:
        result=json.loads(raw)
    except json.JSONDecodeError:
        from json_repair import loads as repair_loads
        result=repair_loads(raw)
    if not isinstance(result,dict):
        raise RuntimeError("AI provider did not return the required JSON object")
    return result

def post_json(url,payload,headers):
    request=urllib.request.Request(url,
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type":"application/json","User-Agent":"TheBriefEditorialResearch/0.5",**headers},
        method="POST")
    try:
        with urllib.request.urlopen(request,timeout=90) as response:
            return json.loads(response.read(600_000))
    except urllib.error.HTTPError as err:
        detail=err.read(450).decode("utf-8",errors="replace")
        # Do not leak secrets, detailed prompts or private content in workflow logs.
        if err.code==429:
            raise RuntimeError("Provider request quota exceeded: HTTP 429") from None
        raise RuntimeError(f"Provider returned HTTP {err.code}: {detail[:100]}") from None

def fetch_ai(prompt, model_override=None):
    if PROVIDER=="gemini":
        return fetch_gemini(prompt, model_override=model_override)
    if PROVIDER=="openai":
        key=os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not configured for explicitly selected OpenAI provider")
        raw=post_json("https://api.openai.com/v1/chat/completions",{
            "model":MODELS[PROVIDER],
            "messages":[
                {"role":"system","content":"Return one valid JSON object only. Cite no fabricated facts; follow the user's source-bound instructions."},
                {"role":"user","content":prompt}
            ],
            "max_completion_tokens":6000,
            "response_format":{"type":"json_object"}
        },{"Authorization":"Bearer "+key})
        choices=raw.get("choices",[])
        if not choices:
            raise RuntimeError("OpenAI returned no candidate")
        return parse_object(choices[0].get("message",{}).get("content"))
    key=os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured for explicitly selected Anthropic provider")
    raw=post_json("https://api.anthropic.com/v1/messages",{
        "model":MODELS[PROVIDER],
        "max_tokens":6000,
        "messages":[{"role":"user","content":prompt+"\nReturn exactly one JSON object and no surrounding markdown."}]
    },{"x-api-key":key,"anthropic-version":"2023-06-01"})
    return parse_object("".join(x.get("text","") for x in raw.get("content",[]) if x.get("type")=="text"))

def self_test():
    assert parse_object('{"headline":"Primary source confirmed"}')["headline"]=="Primary source confirmed"
    try:
        parse_object("[]")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Non-object responses must be blocked")
    assert set(MODELS)=={"gemini","openai","anthropic"}
    print("PASS: explicit provider choice, source-bound JSON validation and default Gemini")

if __name__=="__main__":
    self_test()

