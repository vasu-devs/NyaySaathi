from typing import Iterable, List, Dict
from app.core.config import settings

# OpenAI
from openai import OpenAI

# Google Gemini
import google.generativeai as genai

RoleMsg = Dict[str, str]  # {"role": "system|user|assistant", "content": "..."}

class LLMClient:
    def __init__(self):
        desired = (settings.llm_provider or "").lower().strip()
        # Prefer Gemini 2.0 Flash by default if not explicitly set
        self.model = settings.llm_model or "models/gemini-2.0-flash"

        # Attempt to satisfy desired provider; if key missing, fall back to the other if available
        def _init_openai():
            if not settings.openai_api_key:
                return False
            self.provider = "openai"
            self._openai = OpenAI(api_key=settings.openai_api_key)
            return True

        def _init_google():
            if not settings.google_api_key:
                return False
            self.provider = "google"
            genai.configure(api_key=settings.google_api_key)
            # Defer model creation to call-time so we can apply robust model fallbacks
            self._gemini = None
            return True

        ok = False
        if desired == "openai":
            ok = _init_openai() or _init_google()
        elif desired == "google":
            ok = _init_google() or _init_openai()
        else:
            # Unknown desired value: try google then openai
            ok = _init_google() or _init_openai()

        if not ok:
            raise RuntimeError("No usable LLM provider configured (missing API keys for both OpenAI and Google).")

    def _norm_ids(self, model_id: str) -> List[str]:
        mid = (model_id or "").strip()
        if not mid:
            return []
        ids: List[str] = []
        if not mid.startswith("models/"):
            ids.append(f"models/{mid}")
        ids.append(mid)
        return ids

    def _google_candidates(self) -> List[str]:
        """Return a strict list of Gemini 2.0 Flash model IDs to try.

        We intentionally avoid 1.5 and non-Flash fallbacks to guarantee we always
        use 2.0 Flash when available. IDs are provided in both prefixed and
        unprefixed forms for compatibility.
        """
        cands: List[str] = []
        for m in [
            "models/gemini-2.0-flash",
            "gemini-2.0-flash",
            # Experimental variant kept as a secondary option in case Google
            # temporarily routes availability via -exp.
            "models/gemini-2.0-flash-exp",
            "gemini-2.0-flash-exp",
        ]:
            cands.extend(self._norm_ids(m))

        # Deduplicate preserving order
        seen = set()
        out: List[str] = []
        for m in cands:
            if m and m not in seen:
                out.append(m)
                seen.add(m)
        return out

    def generate(self, messages: List[RoleMsg], temperature: float = 0.2, top_p: float | None = None, max_tokens: int | None = None) -> str:
        if self.provider == "openai":
            resp = self._openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=False,
            )
            return resp.choices[0].message.content or ""
        else:
            # Gemini: move system prompts into system_instruction; map assistant->model
            sys_text = "\n\n".join([m["content"] for m in messages if m.get("role") == "system"]).strip()
            chat_msgs = [m for m in messages if m.get("role") != "system"]
            def _map_role(r: str) -> str:
                return "model" if r == "assistant" else "user"
            contents = [{"role": _map_role(m["role"]), "parts": [m["content"]]} for m in chat_msgs]
            gen_cfg = {"temperature": temperature}
            if top_p is not None:
                gen_cfg["top_p"] = top_p
            if max_tokens is not None:
                gen_cfg["max_output_tokens"] = max_tokens
            last_err = None
            for candidate in self._google_candidates():
                try:
                    model = genai.GenerativeModel(candidate, system_instruction=sys_text) if sys_text else genai.GenerativeModel(candidate)
                    resp = model.generate_content(contents, generation_config=gen_cfg)
                    # Cache the working model for subsequent calls
                    self.model = candidate
                    self._gemini = model
                    return resp.text or ""
                except Exception as e:
                    last_err = e
                    continue
            # If all candidates fail, raise the last error
            raise last_err

    def stream_generate(self, messages: List[RoleMsg], temperature: float = 0.2, top_p: float | None = None, max_tokens: int | None = None) -> Iterable[str]:
        if self.provider == "openai":
            stream = self._openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        else:
            # Gemini: move system into system_instruction; map assistant->model
            sys_text = "\n\n".join([m["content"] for m in messages if m.get("role") == "system"]).strip()
            chat_msgs = [m for m in messages if m.get("role") != "system"]
            def _map_role(r: str) -> str:
                return "model" if r == "assistant" else "user"
            contents = [{"role": _map_role(m["role"]), "parts": [m["content"]]} for m in chat_msgs]
            gen_cfg = {"temperature": temperature}
            if top_p is not None:
                gen_cfg["top_p"] = top_p
            if max_tokens is not None:
                gen_cfg["max_output_tokens"] = max_tokens
            # Iterate candidate models until one streams successfully
            last_err = None
            for candidate in self._google_candidates():
                try:
                    model = genai.GenerativeModel(candidate, system_instruction=sys_text) if sys_text else genai.GenerativeModel(candidate)
                    for ev in model.generate_content(contents, generation_config=gen_cfg, stream=True):
                        if getattr(ev, "text", None):
                            yield ev.text
                    # Cache working model
                    self.model = candidate
                    self._gemini = model
                    return
                except Exception as e:
                    last_err = e
                    continue
            # If all failed, re-raise the last error
            raise last_err
