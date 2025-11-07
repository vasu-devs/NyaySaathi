from typing import List, Dict, Iterable, Tuple
import logging
import re
import os
import json
from functools import lru_cache
from app.services.llm_client import LLMClient
from app.core.config import settings
from app.services.embedding import embed_query, get_embedder
from app.services.vector_store import QdrantStore
from app.services.metadata_store import list_documents as meta_list

MIN_SCORE = 0.35  # minimum similarity score to consider a context relevant

_SMALLTALK = {
    "hi", "hello", "hey", "yo", "sup", "hola", "namaste",
    "hi!", "hello!", "hey!", "hi there", "hello there",
}

def _is_smalltalk(query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return False
    # very short or greeting-like
    if q in _SMALLTALK:
        return True
    if len(q) <= 4 and q in {"hi", "hey"}:
        return True
    # up to 3 tokens and no punctuation – treat as greeting/small talk
    if len(q.split()) <= 3 and all(ch.isalnum() or ch.isspace() for ch in q):
        if any(word in q for word in ["hi", "hello", "hey", "namaste", "hola"]):
            return True
    return False

_LANG_NAMES = {
    "en": "English", "hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
    "mr": "Marathi", "kn": "Kannada", "ml": "Malayalam", "gu": "Gujarati", "pa": "Punjabi",
    "ur": "Urdu", "or": "Odia", "as": "Assamese",
}


def _detect_lang(query: str) -> str:
    """Very lightweight language detection based on script. Defaults to 'en'."""
    q = query or ""
    ql = q.lower()
    # Heuristic: romanized Hindi ("Hinglish") common tokens
    rom_hi_markers = [
        "mool adhikar", "adhikar", "kaunse", "kaun si", "kya hai", "kya hain", "kya h",
        "mere", "mera", "hain", "hai", "nyay", "kanun", "adhiniyam", "dhara", "anuchhed",
    ]
    if any(tok in ql for tok in rom_hi_markers) and ql.isascii():
        return "hi"
    for ch in q:
        code = ord(ch)
        # Devanagari → Hindi/Marathi
        if 0x0900 <= code <= 0x097F:
            return "hi"
        # Bengali/Assamese
        if 0x0980 <= code <= 0x09FF:
            return "bn"
        # Gurmukhi → Punjabi
        if 0x0A00 <= code <= 0x0A7F:
            return "pa"
        # Gujarati
        if 0x0A80 <= code <= 0x0AFF:
            return "gu"
        # Oriya (Odia)
        if 0x0B00 <= code <= 0x0B7F:
            return "or"
        # Tamil
        if 0x0B80 <= code <= 0x0BFF:
            return "ta"
        # Telugu
        if 0x0C00 <= code <= 0x0C7F:
            return "te"
        # Kannada
        if 0x0C80 <= code <= 0x0CFF:
            return "kn"
        # Malayalam
        if 0x0D00 <= code <= 0x0D7F:
            return "ml"
        # Arabic script → treat as Urdu
        if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F or 0x08A0 <= code <= 0x08FF:
            return "ur"
    return "en"


def _lang_system_line(lang: str) -> str:
    name = _LANG_NAMES.get(lang, "English")
    return (
        f"Respond in {name}. Use clear, simple sentences. "
        "Keep statute and case names in English with section numbers (e.g., Section 10, Indian Contract Act, 1872). "
        "Translate explanations and examples to the target language. "
        "Do not use Markdown characters like #, *, **, _, or code fences."
    )


def _greeting_response(lang: str) -> str:
    if lang == "hi":
        return (
            "नमस्ते! मैं न्यायसाथी हूँ. भारतीय कानून से जुड़े प्रश्न पूछें — अनुच्छेद, धाराएँ, मामले या प्रक्रिया। "
            "उदाहरण: 'अनुच्छेद 21 क्या है?', 'ग़ैरक़ानूनी हिरासत का उपाय?', या 'सीआरपीसी में ज़मानत प्रक्रिया'."
        )
    if lang == "bn":
        return (
            "নমস্কার! আমি ন্যায়সাথী। ভারতীয় আইন নিয়ে প্রশ্ন করুন — অনুচ্ছেদ, ধারা, মামলা বা প্রক্রিয়া। "
            "উদাহরণ: 'অনুচ্ছেদ ২১ কী?', 'অবৈধ আটক হলে প্রতিকার?', বা 'CrPC অনুযায়ী জামিনের প্রক্রিয়া'."
        )
    if lang == "ta":
        return (
            "வணக்கம்! நான் ந்யாயஸாதி. இந்திய சட்டம் குறித்து கேளுங்கள் — அரசியல் சட்டப் பிரிவுகள், சட்டப் பிரிவுகள், வழக்குகள், நடைமுறை. "
            "உதா: 'அருச்சு சட்டம் பிரிவு 21?', 'தவறான காவலில் நிவாரணம்?', 'CrPC இல் ஜாமின் நடைமுறை'."
        )
    if lang == "te":
        return (
            "నమస్కారం! నేను న్యాయసాథి. భారతీయ చట్టాలపై ప్రశ్నలు అడగండి — ఆర్టికల్స్, సెక్షన్లు, కేసులు లేదా ప్రక్రియ. "
            "ఉదా: 'ఆర్టికల్ 21 ఏమిటి?', 'అక్రమ నిర్బంధానికి పరిహారం?', లేదా 'CrPC లో బెయిల్ ప్రక్రియ'."
        )
    if lang == "mr":
        return (
            "नमस्कार! मी न्यायसाथी. भारतीय कायद्यासंबंधी प्रश्न विचारा — कलमे, तरतुदी, खटले किंवा प्रक्रिया. "
            "उदा: 'कलम 21 काय आहे?', 'बेकायदेशीर ताब्यास उपाय?', किंवा 'CrPC मधील जामीन प्रक्रिया'."
        )
    if lang == "kn":
        return (
            "ನಮಸ್ಕಾರ! ನಾನು ನ್ಯಾಯಸಾಥಿ. ಭಾರತೀಯ ಕಾನೂನಿನ ಬಗ್ಗೆ ಕೇಳಿ — ಸಂವಿಧಾನ ವಿಧಿಗಳು, ಸೆಕ್ಷನ್‌ಗಳು, ಪ್ರಕರಣಗಳು, ಕ್ರಮಗಳು. "
            "ಉದಾ: 'ಆರ್ಟಿಕಲ್ 21 ಎಂದರೆ?', 'ಬೇಧಕ ಬಂಧನಕ್ಕೆ ಪರಿಹಾರ?', ಅಥವಾ 'CrPC ನಲ್ಲಿ ಜಾಮೀನು ಪ್ರಕ್ರಿಯೆ'."
        )
    if lang == "ml":
        return (
            "നമസ്കാരം! ഞാൻ നിയമസാഥി. ഇന്ത്യൻ നിയമത്തെക്കുറിച്ച് ചോദിക്കൂ — അനുച്ഛേദങ്ങൾ, വകുപ്പ്, കേസുകൾ, നടപടിക്രമം. "
            "ഉദാ: 'അനുച്ഛേദം 21 എന്താണ്?', 'അന്യായ തടങ്കലിന് പരിഹാരം?', 'CrPC പ്രകാരം ജാമ്യാപേക്ഷ പ്രക്രിയ'."
        )
    if lang == "gu":
        return (
            "નમસ્તે! હું ન્યાયસાથી. ભારતીય કાયદા વિશે પૂછો — કલમો, વિભાગો, કેસો કે પ્રક્રિયા. "
            "ઉદાહરણ: 'કલમ 21 શું છે?', 'ગેરકાયદે કસ્ટડીમાં ઉપાય?', અથવા 'CrPCમાં જામીન પ્રક્રિયા'."
        )
    if lang == "pa":
        return (
            "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਨਿਆਂਸਾਥੀ ਹਾਂ। ਭਾਰਤੀ ਕਾਨੂੰਨ ਬਾਰੇ ਪੁੱਛੋ — ਆਰਟਿਕਲ, ਧਾਰਾਵਾਂ, ਮਾਮਲੇ, ਜ਼ਰੀਏ। "
            "ਉਦਾਹਰਨ: 'ਆਰਟਿਕਲ 21 ਕੀ ਹੈ?', 'ਗੈਰਕਾਨੂੰਨੀ ਹਿਰਾਸਤ ਦਾ ਉਪਚਾਰ?', ਜਾਂ 'CrPC ਵਿਚ ਜ਼ਮਾਨਤ ਪ੍ਰਕਿਰਿਆ'."
        )
    if lang == "ur":
        return (
            "سلام! میں نیاے ساتھی ہوں۔ بھارتی قانون سے متعلق سوال پوچھیں — دفعات، شقیں، مقدمات یا طریقہ کار۔ "
            "مثال: 'آرٹیکل 21 کیا ہے؟'، 'غیر قانونی حراست کا علاج؟' یا 'CrPC میں ضمانت کا طریقہ'."
        )
    if lang == "or":
        return (
            "ନମସ୍କାର! ମୁଁ ନ୍ୟାୟସାଥୀ। ଭାରତୀୟ କାନୁନ ସମ୍ବନ୍ଧୀୟ ପ୍ରଶ୍ନ ପଚାରନ୍ତୁ — ଅନୁଛେଦ, ଧାରା, ମାମଲା, ପ୍ରକ୍ରିୟା। "
            "ଉଦାହରଣ: 'ଅନୁଛେଦ 21 କ'ଣ?', 'ବେଆଇନ ହିରାସତରେ ଉପାୟ?', କିମ୍ବା 'CrPC ରେ ଜାମିନ ପ୍ରକ୍ରିୟା'."
        )
    # Default English
    return (
        "Hello! I’m NyaySaathi. Ask me about Indian law – articles, sections, cases, or procedures. "
        "For example: ‘What is Article 21?’, ‘Remedy for wrongful detention?’, or ‘Bail process under CrPC’."
    )

# Placeholder retrieval to be replaced by Qdrant

def retrieve_context(query: str, top_k: int = 10) -> List[Dict]:
    """Adaptive retrieval with query expansion and hybrid reranking."""
    dim = get_embedder().get_sentence_embedding_dimension()
    store = QdrantStore()
    store.ensure_collection(dim)

    def _search(q: str, k: int) -> List[Dict]:
        qvec = embed_query(q)
        return store.search(qvec, top_k=k)

    # Domain-aware query expansion for better recall on common intents
    intent = _detect_intent(query)
    q0 = query
    if intent.get("fundamental_rights_all"):
        # Targeted retrieval per category and article for full coverage
        categories = [
            ("Right to Equality", [14, 15, 16, 17, 18]),
            ("Right to Freedom", [19, 20, 21, "21A", 22]),
            ("Right against Exploitation", [23, 24]),
            ("Right to Freedom of Religion", [25, 26, 27, 28]),
            ("Cultural and Educational Rights", [29, 30]),
            ("Right to Constitutional Remedies", [32]),
        ]
        gathered: List[Dict] = []
        seen = set()
        def _add_matches(q: str, k: int = 4):
            for m in _search(q, k):
                key = (m.get("doc_id"), m.get("chunk_id"))
                if key in seen:
                    continue
                seen.add(key)
                gathered.append(m)
        for cat, arts in categories:
            _add_matches(f"{cat} Part III Constitution of India fundamental rights", 3)
            for a in arts:
                _add_matches(f"Article {a} Constitution of India Part III fundamental rights", 3)
        # If still thin, add a combined query
        if len(gathered) < 12:
            _add_matches("Fundamental Rights Part III list all: Equality (14-18), Freedom (19-22 incl 21 & 21A), Exploitation (23-24), Religion (25-28), Cultural/Educational (29-30), Remedies (32).", 12)
        # Sort by score and return
        gathered.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return gathered[: max(top_k, 24)]

    # Adaptive query expansion using legal links
    links = _load_legal_links()
    det_refs = _detect_legal_refs(q0)
    expanded_q, kw_q = _expand_query(q0, det_refs, links)
    adaptive_k = 5 if det_refs.get("has_ref") else 10

    # Multi-query semantic search and merge
    base_res = _search(expanded_q or q0, max(top_k, adaptive_k))
    alt_res = _search(q0, adaptive_k)
    kw_res = _search(kw_q or q0, adaptive_k)
    merged: Dict[Tuple[str, int], Dict] = {}
    for lst in (base_res, alt_res, kw_res):
        for m in lst or []:
            key = (m.get("doc_id"), m.get("chunk_id"))
            # keep the best score per unique chunk
            if key not in merged or m.get("score", 0.0) > merged[key].get("score", 0.0):
                merged[key] = m
    results = list(merged.values())
    if not results:
        results = _search(q0, top_k)

    # Light hybrid reranking: prefer matches that align with explicit legal references and keyword overlap
    def _extract_refs(q: str) -> Dict[str, List[str]]:
        ql = q.lower()
        arts = re.findall(r"article\s+(\d+[a-z]?)", ql)
        secs = re.findall(r"section\s+(\d+[a-z]?)", ql)
        parts = re.findall(r"part\s+([ivxlcdm]+|\d+)", ql)
        chaps = re.findall(r"chapter\s+([ivxlcdm]+|\d+)", ql)
        return {"article": arts, "section": secs, "part": parts, "chapter": chaps}

    def _keyword_overlap(a: str, b: str) -> float:
        ta = {w for w in re.findall(r"[a-zA-Z]{3,}", (a or "").lower())}
        tb = {w for w in re.findall(r"[a-zA-Z]{3,}", (b or "").lower())}
        if not ta or not tb:
            return 0.0
        inter = ta & tb
        base = min(len(ta), len(tb)) or 1
        return min(1.0, len(inter) / base)

    refs = _extract_refs(q0)
    # Right-aware proximity targets and restriction-sensitive reranking
    def _invoked_articles(q: str, refs_map: Dict[str, List[str]]) -> List[int]:
        ql = (q or "").lower()
        nums: List[int] = []
        for a in refs_map.get("article", []) or []:
            try:
                nums.append(int(re.sub(r"[^0-9]", "", a)))
            except Exception:
                pass
        # Public order / speech / assembly / association cues => Article 19 proximity
        if any(k in ql for k in ["public order", "decency", "morality", "sovereignty", "security of the state", "free speech", "freedom of speech", "article 19"]):
            nums.append(19)
        if "right to equality" in ql or "equality before law" in ql:
            nums.extend([14, 15, 16, 17, 18])
        if "right to freedom" in ql:
            nums.extend([19, 20, 21, 22])
        if "right against exploitation" in ql:
            nums.extend([23, 24])
        if "freedom of religion" in ql:
            nums.extend([25, 26, 27, 28])
        if "cultural" in ql and "educational" in ql:
            nums.extend([29, 30])
        if "constitutional remedies" in ql:
            nums.extend([32])
        return nums

    target_articles = _invoked_articles(q0, refs)
    restriction_terms = [
        "reasonable restriction", "subject to", "notwithstanding", "restriction", "exception", "reservation",
        "classification", "intelligible differentia", "rational nexus", "public order", "morality", "security of state",
    ]
    procedural_terms = [
        "procedure", "safeguard", "reasons to be recorded in writing", "by order", "subject to the provisions of sub-section",
        "rules may be prescribed", "block", "blocking", "intercept", "monitor", "decrypt",
    ]

    # Statute → Constitution link mapper (lightweight)
    def _statute_links(meta: Dict, text: str) -> List[int]:
        title = (meta.get("title") or meta.get("source_path") or "").lower()
        section = str(meta.get("section") or "").upper()
        t = (text or "").lower()
        links: List[int] = []
        # JSON-driven mapping
        try:
            mapping = _load_legal_links()
            for art_key, cfg in (mapping or {}).items():
                try:
                    art_num = int(re.sub(r"[^0-9]", "", art_key))
                except Exception:
                    art_num = None
                sections = [str(s).upper() for s in (cfg.get("Linked_Sections") or [])]
                kws = [k.lower() for k in (cfg.get("Keywords") or [])]
                if any(sec in (section or "") or (section and sec.find(section) >= 0) or (sec and sec in t.upper()) for sec in sections):
                    if art_num:
                        links.append(art_num)
                if kws and any(k in t for k in kws):
                    if art_num:
                        links.append(art_num)
        except Exception:
            pass
        # Hand-tuned fallbacks
        if ("information technology" in title or "it_act" in title or "it act" in title):
            if section in ("69A", "69") or ("section 69a" in t or "section 69" in t):
                links.append(19)
        if ("code of criminal procedure" in title or "crpc" in title) and section == "144":
            links.append(19)
        return links

    reranked: List[Tuple[float, Dict]] = []
    for r in results or []:
        base = float(r.get("score", 0.0))
        bonus = 0.0
        meta = r.get("meta", {}) or {}
        # Exact legal number alignment boosts
        art = (meta.get("article") or meta.get("Article") or meta.get("ARTICLE"))
        sec = (meta.get("section") or meta.get("Section") or meta.get("SECTION"))
        part = (meta.get("part") or meta.get("Part") or meta.get("PART"))
        chap = (meta.get("chapter") or meta.get("Chapter") or meta.get("CHAPTER"))
        if art and any(str(art).lower() == a for a in refs["article"]):
            bonus += 0.22
        if sec and any(str(sec).lower() == s for s in refs["section"]):
            bonus += 0.18
        if part and any(str(part).lower() == p for p in refs["part"]):
            bonus += 0.06
        if chap and any(str(chap).lower() == c for c in refs["chapter"]):
            bonus += 0.05
        # Article number proximity relative to invoked right/articles
        try:
            art_num = int(re.sub(r"[^0-9]", "", str(art))) if art else None
        except Exception:
            art_num = None
        if art_num and target_articles:
            dist = min(abs(art_num - t) for t in target_articles)
            proximity = max(0.0, 1.0 - (dist / 10.0))
            bonus += 0.15 * proximity
        # Restriction/exception vocabulary presence
        text_low = (r.get("text", "") or "").lower()
        if any(term in text_low for term in restriction_terms):
            bonus += 0.10
        # Procedure/safeguard vocabulary presence
        if any(term in text_low for term in procedural_terms):
            bonus += 0.08
        # Payload tags (from ingestion) can also signal procedure
        tags = meta.get("tags") or []
        if isinstance(tags, list) and any(t in tags for t in ["procedure", "safeguard", "blocking", "interception"]):
            bonus += 0.10
        # Keyword overlap (lightweight BM25-ish)
        bonus += 0.12 * _keyword_overlap(q0, r.get("text", ""))
        # Constitution–statute link bonus: if a statute section is linked to a constitutional article we target
        links = _statute_links(meta, r.get("text") or "")
        if links and target_articles:
            if any(lnk in target_articles for lnk in links):
                bonus += 0.12
            # Also expand target_articles slightly to include links
            for lnk in links:
                if lnk not in target_articles:
                    target_articles.append(lnk)
        reranked.append((base + bonus, r))
    reranked.sort(key=lambda x: x[0], reverse=True)
    results = [r for _, r in reranked][:top_k]
    # Debug print: rewritten query and top sources
    try:
        logging.getLogger(__name__).info(
            "RAG debug: rewritten_query=%s | sources=%s",
            expanded_q or q0,
            [(r.get("doc_id"), r.get("chunk_id"), round(r.get("score", 0.0), 3)) for r in results],
        )
    except Exception:
        pass
    return results


def build_prompt(user_query: str, contexts: List[Dict], lang_override: str | None = None) -> list[dict]:
    """Construct the system and user messages to enforce NyaySaathi's role and structure.

    This prompt encodes the user's requested policy: role definition, objectives, answer framework,
    language handling, citation discipline, missing-context behavior, and a safety clause.
    """
    # Language instruction: respond in the requested language (override or detect from query)
    lang = lang_override or _detect_lang(user_query)

    header = (
        "Use the provided constitutional and statutory context to explain legal reasoning for the scenario.\n"
        "Identify (1) applicable rights, (2) lawful restrictions, (3) relevant statutory powers, and (4) available remedies.\n"
        "Distinguish what the Constitution guarantees and what the IT Act authorizes.\n"
        "Apply reasonableness/proportionality tests. Be concise and factual.\n"
        "If context is incomplete, note which law is missing.\n\n"
        "Style (low-key): Prefer concise bullet points and minimal subheadings (e.g., 'Legal basis', 'Sources'). Avoid long essays.\n"
        "Citations: Only from the provided context; no invented provisions or cases.\n"
        "Safety: Not legal advice; suggest consulting an advocate for case-specific matters.\n"
        "Fallback: If context is missing or unrelated, reply exactly: \"Sorry, I don't have the relevant information for your query right now. Please refer to official Government of India legal resources: India Code (https://www.indiacode.nic.in/) for Acts and the Legislative Department (https://legislative.gov.in) for the Constitution of India.\"\n"
    )
    # Prepend language rule
    header = _lang_system_line(lang) + "\n\n" + header

    # Intent-specific guidance (kept inside the system message for clarity)
    intent = _detect_intent(user_query)
    if intent.get("fundamental_rights_all"):
        header += (
            "\nWhen the user asks to list ALL fundamental rights, enumerate each category with accurate article ranges: "
            "Right to Equality (Arts 14–18), Right to Freedom (Arts 19–22 including 21), Right against Exploitation (Arts 23–24), "
            "Right to Freedom of Religion (Arts 25–28), Cultural and Educational Rights (Arts 29–30), Right to Constitutional Remedies (Art 32), "
            "and include Article 21A (Right to Education). Keep it concise and accurate."
        )

    # Prepare context
    ctx_text = "\n\n".join(
        f"[{c.get('doc_id','?')}:{c.get('chunk_id','?')}] {c['text']}" for c in contexts
    ) or "(no context)"

    system = {"role": "system", "content": header}
    user = {"role": "user", "content": (
        f"<context>\n{ctx_text}\n</context>\n\n"
        f"<instruction>\nUser Query: {user_query}\n\n"
        "Use only the text in <context> to answer. If <context> is empty or unrelated, output only the fallback message exactly as defined in the system prompt.\n"
        "Do not output both the fallback message and an answer in the same response.\n"
        "Prefer bullet points for key points. Use a minimal subheading like 'Legal basis:' or 'Sources:' only if it improves clarity.\n"
        "When statutes appear (e.g., IT Act s.69A), briefly link them to the relevant constitutional grounds (e.g., Art 19(2) public order/sovereignty/etc.) and state the test for reasonableness.\n"
        "Avoid decorative headings or long templates; no long essays unless explicitly asked.\n"
        "</instruction>"
    )}
    return [system, user]


def _build_free_prompt(user_query: str, forced_lang: str | None = None) -> list[dict]:
    """Free-mode prompt: answer based on general Indian legal knowledge when RAG context is unavailable.

    Keeps the low-key style and safety guidance, but does not enforce 'use only provided context'.
    """
    lang = forced_lang or _detect_lang(user_query)
    header = (
        "You are NyaySaathi. Explain Indian law clearly and concisely.\n"
        "Focus on: (1) relevant constitutional provisions, (2) statutory framework, (3) leading Supreme Court/HC cases, (4) practical examples/remedies.\n"
        "Be conservative and avoid speculation. If uncertain, say so briefly and point to official sources (India Code; Legislative Dept.).\n"
        "Style: bullets > short paragraphs. Minimal headings like 'Legal basis:' or 'Sources:'. Not legal advice."
    )
    header = _lang_system_line(lang) + "\n\n" + header
    system = {"role": "system", "content": header}
    user = {"role": "user", "content": user_query}
    return [system, user]


def _is_free_mode(user_query: str) -> bool:
    q = (user_query or "").lower()
    markers = [
        "please explain further for indian law",
        "nyayshala",
        "know more in chatbot",
        "free-mode",
    ]
    return any(m in q for m in markers)


def _format_output(text: str) -> str:
        """Output formatter honoring settings.enable_markdown_rendering.

        - When Markdown rendering is enabled, keep Markdown intact and only normalize
            excessive blank lines/trim whitespace.
        - When disabled, sanitize Markdown markers and keep a low-key plain text style.
        """
        if settings.enable_markdown_rendering:
                t = (text or "")
                # Collapse excessive blank lines and trim; keep markdown markers
                t = re.sub(r"\n{3,}", "\n\n", t)
                return t.strip()
        return _format_plain(text)


def answer(query: str, stream: bool = True) -> Iterable[str] | str:
    # First-pass: script-based detection
    lang = _detect_lang(query)
    # Second-pass: LLM-based detection to broaden coverage (romanized/other languages)
    try:
        detected = _detect_lang_via_llm(query)
        if detected and detected != lang:
            lang = detected
    except Exception:
        pass
    # Small-talk friendly response
    if _is_smalltalk(query):
        text = _greeting_response(lang)
        formatted = clean_legal_response(text)
        if stream:
            def _gen():
                yield _format_output(formatted)
            return _gen()
        return _format_output(formatted)

    # Translate query to English for retrieval if needed
    search_query = query
    if lang != "en":
        try:
            search_query = _translate_to_english(query)
        except Exception:
            search_query = query

    contexts = retrieve_context(search_query)
    # Filter out weak matches so we don't show irrelevant citations
    strong = [c for c in contexts or [] if c.get("score", 0.0) >= MIN_SCORE]
    # Also enforce admin approval gating based on metadata store
    try:
        approved_ids = {d.get("doc_id") for d in (meta_list() or []) if d.get("approved") is True}
        if approved_ids:
            strong = [c for c in strong if c.get("doc_id") in approved_ids]
    except Exception:
        # If metadata loading fails, proceed with current list
        pass

    # Intent-specific deterministic answer for complete fundamental rights list
    intent = _detect_intent(query)
    if intent.get("fundamental_rights_all"):
        text = _compose_fundamental_rights_answer_lang(lang)
        formatted = clean_legal_response(text)
        if stream:
            def _gen():
                yield _format_output(formatted)
            return _gen()
        return _format_output(formatted)

    # Intent-specific deterministic answer for Right to Equality
    if intent.get("right_to_equality"):
        text = _compose_right_to_equality_answer(query)
        if stream:
            def _gen():
                yield _format_plain(text)
            return _gen()
        return _format_plain(text)

    # If retrieval came up empty or very weak
    if not strong:
        # Always try a careful general answer instead of hard fallback (with quick retries)
        if not stream:
            import time as _time
            last_err = None
            # First, try in detected language
            for i in range(2):
                try:
                    llm = LLMClient()
                    # Generate in English, then translate back to the user's language
                    raw_en = llm.generate(_build_free_prompt(query, forced_lang="en"), temperature=0.2, top_p=0.8, max_tokens=min(768, settings.llm_max_output_tokens))
                    formatted_en = clean_legal_response(raw_en)
                    final_text = _translate_from_english(formatted_en, lang) if lang != "en" else formatted_en
                    return _format_output(final_text)
                except Exception as e:
                    last_err = e
                    logging.getLogger(__name__).exception("LLM free-mode failed: %s", e)
                    _time.sleep(0.25 * (2 ** i))
            # If that fails (e.g., model/language issue), try English as a universal fallback
            try:
                llm2 = LLMClient()
                raw2 = llm2.generate(_build_free_prompt(query, forced_lang="en"), temperature=0.2, top_p=0.8, max_tokens=min(768, settings.llm_max_output_tokens))
                return _format_output(clean_legal_response(raw2))
            except Exception:
                pass
            # fallthrough to official sources guidance
        guidance = _guidance_message(lang)
        formatted = clean_legal_response(guidance)
        if stream:
            def _gen():
                yield _format_output(formatted)
            return _gen()
        return _format_output(formatted)

    # Context compression: synthesize retrieved excerpts into a single, concise context before answering
    try:
        compressed = _compress_contexts(query, strong, max_chunks=8)
        contexts_for_prompt = [{"doc_id": "synth", "chunk_id": 0, "text": compressed}]
    except Exception:
        # Fallback: join top chunks
        join_text = "\n\n".join((c.get("text") or "")[:1200] for c in strong[:8])
        contexts_for_prompt = [{"doc_id": "concat", "chunk_id": 0, "text": join_text}]

    # Build prompt and generate
    # Generate in English for accuracy; we will translate the final answer back to the user's language
    msgs = build_prompt(_translate_to_english(query) if lang != "en" else query, contexts_for_prompt, lang_override="en")
    if stream:
        def _stream():
            buf: List[str] = []
            try:
                llm = LLMClient()
                for tok in llm.stream_generate(msgs, temperature=0.2, top_p=0.8, max_tokens=settings.llm_max_output_tokens):
                    buf.append(tok)
            except Exception as e:
                # Graceful degradation for streaming path
                logging.getLogger(__name__).exception("LLM streaming failed: %s", e)
                # Try non-stream fallback with a couple of quick retries
                try:
                    import time as _time
                    last_err = None
                    for i in range(2):
                        try:
                            llm2 = LLMClient()
                            raw2 = llm2.generate(msgs, temperature=0.2, top_p=0.8, max_tokens=settings.llm_max_output_tokens)
                            final2 = clean_legal_response(raw2)
                            yield _format_output(final2)
                            return
                        except Exception as ee:
                            last_err = ee
                            _time.sleep(0.25 * (2 ** i))
                    # Final attempt: English free-mode
                    try:
                        llm3 = LLMClient()
                        raw3 = llm3.generate(_build_free_prompt(query, forced_lang="en"), temperature=0.2, top_p=0.8, max_tokens=min(768, settings.llm_max_output_tokens))
                        yield _format_output(clean_legal_response(raw3))
                        return
                    except Exception:
                        pass
                    raise last_err or e
                except Exception:
                    # Fall back to official sources message instead of transient error text
                    guidance = _guidance_message(lang, transient=True)
                    yield _format_output(clean_legal_response(guidance))
                    return
            final_en = clean_legal_response("".join(buf))
            # Translate back to original language if needed
            final_text = _translate_from_english(final_en, lang) if lang != "en" else final_en
            final_text = _format_output(final_text)
            yield final_text
        return _stream()
    # Non-stream: quick retry before official fallback
    try:
        import time as _time
        last_err = None
        for i in range(2):
            try:
                llm = LLMClient()
                raw_en = llm.generate(msgs, temperature=0.2, top_p=0.8, max_tokens=settings.llm_max_output_tokens)
                formatted_en = clean_legal_response(raw_en)
                final_text = _translate_from_english(formatted_en, lang) if lang != "en" else formatted_en
                return _format_output(final_text)
            except Exception as ee:
                last_err = ee
                _time.sleep(0.25 * (2 ** i))
        raise last_err
    except Exception as e:
        logging.getLogger(__name__).exception("LLM generate failed: %s", e)
        guidance = _guidance_message(lang, transient=True)
        formatted = clean_legal_response(guidance)
        return _format_output(formatted)


def _compose_fundamental_rights_answer(user_query: str) -> str:
    # Deterministic, accurate enumeration per Constitution (Part III), low-key style
    lines = []
    lines.append("A complete list of Fundamental Rights under the Constitution of India (Part III, Arts 12–35):")
    lines.append("- Right to Equality — Articles 14–18")
    lines.append("- Right to Freedom — Articles 19–22 (includes 21 and 21A)")
    lines.append("- Right against Exploitation — Articles 23–24")
    lines.append("- Right to Freedom of Religion — Articles 25–28")
    lines.append("- Cultural and Educational Rights — Articles 29–30")
    lines.append("- Right to Constitutional Remedies — Article 32")
    lines.append("")
    lines.append("Legal basis: Constitution of India, Part III (Articles 14–18, 19–22 incl. 21 & 21A, 23–24, 25–28, 29–30, 32)")
    return "\n".join(lines)


def _compose_fundamental_rights_answer_lang(lang: str) -> str:
    """Deterministic list of Fundamental Rights localized to common Indian languages.

    Falls back to English if language not explicitly supported.
    """
    if lang == "hi":
        lines = []
        lines.append("मौलिक अधिकारों की पूर्ण सूची (भाग III, अनुच्छेद 12–35):")
        lines.append("- समानता का अधिकार — अनुच्छेद 14–18")
        lines.append("- स्वतंत्रता का अधिकार — अनुच्छेद 19–22 (21 और 21A सहित)")
        lines.append("- शोषण के विरुद्ध अधिकार — अनुच्छेद 23–24")
        lines.append("- धर्म की स्वतंत्रता का अधिकार — अनुच्छेद 25–28")
        lines.append("- सांस्कृतिक और शैक्षिक अधिकार — अनुच्छेद 29–30")
        lines.append("- संवैधानिक उपचारों का अधिकार — अनुच्छेद 32")
        lines.append("")
        lines.append("कानूनी आधार: भारत का संविधान, भाग III (अनुच्छेद 14–18, 19–22 (21 व 21A सहित), 23–24, 25–28, 29–30, 32)")
        return "\n".join(lines)
    if lang == "pa":
        lines = []
        lines.append("ਮੂਲ ਅਧਿਕਾਰਾਂ ਦੀ ਪੂਰੀ ਸੂਚੀ (ਭਾਗ III, ਅਨੁਛੇਦ 12–35):")
        lines.append("- ਬਰਾਬਰੀ ਦਾ ਅਧਿਕਾਰ — ਅਨੁਛੇਦ 14–18")
        lines.append("- ਆਜ਼ਾਦੀ ਦਾ ਅਧਿਕਾਰ — ਅਨੁਛੇਦ 19–22 (21 ਅਤੇ 21A ਸਮੇਤ)")
        lines.append("- ਸ਼ੋਸ਼ਣ ਖ਼ਿਲਾਫ਼ ਅਧਿਕਾਰ — ਅਨੁਛੇਦ 23–24")
        lines.append("- ਧਰਮ ਦੀ ਆਜ਼ਾਦੀ ਦਾ ਅਧਿਕਾਰ — ਅਨੁਛੇਦ 25–28")
        lines.append("- ਸੱਭਿਆਚਾਰਕ ਅਤੇ ਸ਼ਿਕਸ਼ਾ ਸੰਬੰਧੀ ਅਧਿਕਾਰ — ਅਨੁਛੇਦ 29–30")
        lines.append("- ਸੰਵਿਧਾਨਕ ਉਪਚਾਰਾਂ ਦਾ ਅਧਿਕਾਰ — ਅਨੁਛੇਦ 32")
        lines.append("")
        lines.append("ਕਾਨੂੰਨੀ ਆਧਾਰ: ਭਾਰਤ ਦਾ ਸੰਵਿਧਾਨ, ਭਾਗ III (ਅਨੁਛੇਦ 14–18, 19–22 (21 ਅਤੇ 21A ਸਮੇਤ), 23–24, 25–28, 29–30, 32)")
        return "\n".join(lines)
    if lang == "bn":
        lines = []
        lines.append("মৌলিক অধিকারের সম্পূর্ণ তালিকা (পার্ট III, অনুচ্ছেদ ১২–৩৫):")
        lines.append("- সমতার অধিকার — অনুচ্ছেদ ১৪–১৮")
        lines.append("- স্বাধীনতার অধিকার — অনুচ্ছেদ ১৯–২২ (২১ ও ২১A সহ)")
        lines.append("- শোষণবিরোধী অধিকার — অনুচ্ছেদ ২৩–২৪")
        lines.append("- ধর্মীয় স্বাধীনতার অধিকার — অনুচ্ছেদ ২৫–২৮")
        lines.append("- সাংস্কৃতিক ও শিক্ষাগত অধিকার — অনুচ্ছেদ ২৯–৩০")
        lines.append("- সাংবিধানিক প্রতিকার পাওয়ার অধিকার — অনুচ্ছেদ ৩২")
        lines.append("")
        lines.append("আইনি ভিত্তি: ভারতের সংবিধান, পার্ট III (অনুচ্ছেদ ১৪–১৮, ১৯–২২ (২১ ও ২১A সহ), ২৩–২৪, ২৫–২৮, ২৯–৩০, ৩২)")
        return "\n".join(lines)
    # Default to English
    return _compose_fundamental_rights_answer("")


def _sanitize_plain(text: str) -> str:
    """Remove common Markdown markers to keep output plain text only."""
    if not text:
        return text
    out = text
    # Remove emphasis/strong markers and code markers
    out = out.replace("**", "")
    out = out.replace("*", "")
    out = out.replace("`", "")
    out = out.replace("#", "")
    # Replace underscores that are often used for italics/formatting with spaces
    out = out.replace("_", " ")
    return out


def _format_plain(text: str) -> str:
    """Light normalization for low-key output.

    - Strip markdown emphasis/code markers (bold/italic/backticks)
    - Preserve minimal inline subheadings like 'Legal basis:' or 'Sources:' as-is
    - Keep bullet lists as '-' bullets (do not renumber)
    - Collapse excessive blank lines
    """
    t = (text or "")

    # Inline emphasis/code cleanup first (but keep heading/list markers intact)
    # Replace **bold** and *italic* with plain text
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)
    t = re.sub(r"\*(.*?)\*", r"\1", t)
    # Replace `code` with plain text
    t = re.sub(r"`([^`]*)`", r"\1", t)

    lines = t.splitlines()
    out_lines: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        # Drop a bare 'Title' line if the model emitted it literally
        if i == 0 and line.strip().lower() == "title":
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            continue
        # Keep '#' headings as plain lines (remove the '#' markers for low-key style)
        m = re.match(r"^\s{0,3}(#{1,6})\s+(.*)$", line)
        if m:
            title = m.group(2).strip()
            out_lines.append(title)
            i += 1
            continue
        # Keep bullets as '-' (do not renumber)
        if line.lstrip().startswith("* "):
            # Convert '*' bullets to '-' to keep a consistent minimal style
            out_lines.append("- " + line.lstrip()[2:].strip())
            i += 1
            # Copy through following bullet lines
            while i < len(lines) and (lines[i].lstrip().startswith("* ")):
                out_lines.append("- " + lines[i].lstrip()[2:].strip())
                i += 1
            continue

        out_lines.append(line)
        i += 1

    # Collapse excessive blank lines
    normalized = re.sub(r"\n{3,}", "\n\n", "\n".join(out_lines)).strip()
    # Final cleanup: remove stray hashes/asterisks/underscores that may remain
    normalized = normalized.replace("#", "")
    normalized = normalized.replace("**", "").replace("*", "")
    normalized = normalized.replace("_", " ")
    return normalized


def clean_legal_response(text: str) -> str:
    """Lightweight post-formatter for legal responses.

    Rules:
    - Normalize headings (#, ##, ###, …) to a single 'Heading:' line style
    - Convert bold line headings (**Legal Basis**) to 'Legal Basis:'
    - Convert Markdown links [text](url) to 'text (url)'
    - Standardize bullets: '-' or '*' to '•'
    - Remove duplicate consecutive titles/headings
    - Collapse excessive blank lines
    - Remove stray markdown markers (` ** * _ ) that remain
    """
    if not text:
        return text
    t = text

    # 1) Convert markdown links to 'text (url)'
    t = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 (\2)", t)

    # 2) Normalize atx headings (# ...)
    #    Any line starting with 1-6 hashes becomes a simple 'Heading:' line (no bold)
    t = re.sub(r"(?m)^\s*#{1,6}\s*(.+?)\s*$", r"\n\1:\n", t)

    # 3) Convert bold-only lines at start to 'Label:'
    #    E.g., '**Legal Basis**' or '**Legal Basis:**' => 'Legal Basis:'
    t = re.sub(r"(?m)^\s*\*\*\s*(.*?)\s*\*\*\s*:?[\s]*$", r"\1:", t)

    # 3a) If a heading line starts with 'Title: ...', drop the 'Title: ' label
    t = re.sub(r"(?m)^\s*Title:\s*(.+?):\s*$", r"\1:", t)

    # 4) Standardize bullets: lines starting with '-' or '*' become '• '
    t = re.sub(r"(?m)^\s*[\-\*]\s+", "• ", t)

    # 5) Remove remaining bold/italic markers within text
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)
    t = re.sub(r"\*(.*?)\*", r"\1", t)

    # 6) Remove inline code/backticks; underscores to spaces
    t = t.replace("`", "")
    t = t.replace("_", " ")

    # 7) Trim duplicate consecutive title lines (lines that end with ':')
    lines = t.splitlines()
    out_lines: List[str] = []
    prev_title = None
    for line in lines:
        s = line.strip()
        if s.endswith(":"):
            if prev_title == s:
                continue  # skip duplicate title
            prev_title = s
        else:
            prev_title = None
        out_lines.append(line)
    t = "\n".join(out_lines)

    # 8) Collapse 3+ blank lines into 2, strip ends
    t = re.sub(r"\n{3,}", "\n\n", t)
    # 9) De-duplicate link text when it's the same as URL: 'url (url)' -> 'url'
    t = re.sub(r"(?im)(https?://[^\s)]+) \(\1\)", r"\1", t)
    return t.strip()


def _guidance_message(lang: str, transient: bool = False) -> str:
    """Localized guidance/fallback message.

    transient=True is used when there's a temporary failure; wording stays similar but can be slightly different.
    """
    if lang == "hi":
        return (
            "क्षमा करें, अभी आवश्यक जानकारी उपलब्ध नहीं है। आधिकारिक स्रोत देखें:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- विधि विभाग (Legislative Dept.): https://legislative.gov.in"
        )
    if lang == "bn":
        return (
            "দুঃখিত, প্রয়োজনীয় তথ্য এই মুহূর্তে নেই। সরকারি উৎস দেখুন:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- আইন বিভাগ (Legislative Dept.): https://legislative.gov.in"
        )
    if lang == "ta":
        return (
            "மன்னிக்கவும், இப்போது தேவையான தகவல் இல்லை. அதிகாரப்பூர்வ மூலங்களைப் பார்க்கவும்:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- Legislative Dept.: https://legislative.gov.in"
        )
    if lang == "te":
        return (
            "క్షమించండి, ప్రస్తుతం అవసరమైన సమాచారం లేదు. అధికారిక వనరులు చూడండి:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- Legislative Dept.: https://legislative.gov.in"
        )
    if lang == "mr":
        return (
            "क्षमस्व, आवश्यक माहिती सध्या उपलब्ध नाही. अधिकृत स्रोत पहा:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- विधी विभाग (Legislative Dept.): https://legislative.gov.in"
        )
    if lang == "kn":
        return (
            "ಕ್ಷಮಿಸಿ, ಅಗತ್ಯ ಮಾಹಿತಿಯು ಈಗ ಲಭ್ಯವಿಲ್ಲ. ಅಧಿಕೃತ ಮೂಲಗಳನ್ನು ನೋಡಿ:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- Legislative Dept.: https://legislative.gov.in"
        )
    if lang == "ml":
        return (
            "ക്ഷമിക്കണം, ആവശ്യമായ വിവരം ഇപ്പോൾ ലഭ്യമല്ല. ഔദ്യോഗിക ഉറവിടങ്ങൾ കാണുക:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- Legislative Dept.: https://legislative.gov.in"
        )
    if lang == "gu":
        return (
            "માફ કરશો, જરૂરી માહિતી હાલ ઉપલબ્ધ નથી. સત્તાવાર સ્ત્રોત જુઓ:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- Legislative Dept.: https://legislative.gov.in"
        )
    if lang == "pa":
        return (
            "ਮਾਫ ਕਰਨਾ, ਲੋੜੀਂਦੀ ਜਾਣਕਾਰੀ ਇਸ ਸਮੇਂ ਉਪਲਬਧ ਨਹੀਂ। ਸਰਕਾਰੀ ਸਰੋਤ ਵੇਖੋ:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- Legislative Dept.: https://legislative.gov.in"
        )
    if lang == "ur":
        return (
            "معاف کیجیے، مطلوبہ معلومات فی الحال دستیاب نہیں۔ سرکاری ذرائع دیکھیں:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- Legislative Dept.: https://legislative.gov.in"
        )
    if lang == "or":
        return (
            "ମାପ କରନ୍ତୁ, ଆବଶ୍ୟକ ତଥ୍ୟ ବର୍ତ୍ତମାନ ଉପଲବ୍ଧ ନାହିଁ। ଅଧିକୃତ ସ୍ରୋତ ଦେଖନ୍ତୁ:\n"
            "- India Code: https://www.indiacode.nic.in/\n"
            "- Legislative Dept.: https://legislative.gov.in"
        )
    # English default
    base = (
        "Sorry, I don't have the relevant information for your query right now. "
        "Please refer to official Government of India legal resources: \n"
        "- India Code: https://www.indiacode.nic.in/ (official repository of Central Acts)\n"
        "- Legislative Department: https://legislative.gov.in (includes the Constitution of India)"
    )
    if transient:
        base = base.replace("I don't have the relevant information", "I can't complete this")
    return base


def _translate_to_english(text: str) -> str:
    """Use the configured LLM (Gemini expected) to translate arbitrary text to English only.

    The prompt instructs: output only the translation, keep statute/case names and section numbers intact.
    """
    if not text:
        return text
    try:
        llm = LLMClient()
        sys = {
            "role": "system",
            "content": (
                "Translate the user text into English. Output only the translation, no explanations. "
                "Preserve statute and case names and section/article numbers verbatim (e.g., Section 69A, Article 19(2))."
            ),
        }
        user = {"role": "user", "content": text}
        out = llm.generate([sys, user], temperature=0.0, top_p=1.0, max_tokens=600)
        return (out or "").strip()
    except Exception:
        return text


def _translate_from_english(text: str, target_lang: str) -> str:
    """Translate English text to target language. Output only the translation.

    Keeps statute/case names and section/article numbers in English.
    """
    if not text or target_lang == "en":
        return text
    try:
        llm = LLMClient()
        sys = {
            "role": "system",
            "content": (
                "Translate the user text into the language specified by this BCP-47 code. "
                "Output only the translation, no explanations. "
                "Preserve statute and case names and section/article numbers verbatim (e.g., Section 69A, Article 19(2))."
            ),
        }
        # Provide the target language code explicitly
        user = {"role": "user", "content": f"Target-Language: {target_lang}\n\n{text}"}
        out = llm.generate([sys, user], temperature=0.0, top_p=1.0, max_tokens=1200)
        return (out or "").strip()
    except Exception:
        return text


def _detect_lang_via_llm(text: str) -> str:
    """Use the LLM to detect primary language of the text. Returns a BCP-47/ISO-639-1 code (lowercase), or 'en'.

    We instruct the model to respond with only the 2-3 letter language code. Handles romanized inputs too.
    """
    try:
        llm = LLMClient()
        sys = {
            "role": "system",
            "content": (
                "Given a user text, output ONLY the primary language code (BCP-47 / ISO 639-1/2), lowercase. "
                "Examples: 'en', 'hi', 'bn', 'ta', 'te', 'mr', 'kn', 'ml', 'gu', 'pa', 'ur', 'or', 'as'. "
                "If the text is romanized but clearly belongs to a language, return that language code (e.g., 'mere mool adhikar' -> 'hi')."
            ),
        }
        user = {"role": "user", "content": text}
        code = (llm.generate([sys, user], temperature=0.0, top_p=1.0, max_tokens=8) or "").strip().lower()
        # Basic sanity filter
        if 1 <= len(code) <= 10 and code.isascii() and code.replace('-', '').isalpha():
            return code.split('-')[0]
        return "en"
    except Exception:
        return "en"


def _detect_intent(query: str) -> Dict[str, bool]:
    q = (query or "").lower()
    intents = {
        "fundamental_rights_all": False,
        "right_to_equality": False,
    }
    # English
    if any(kw in q for kw in [
        "all fundamental rights",
        "list fundamental rights",
        "enumerate fundamental rights",
        "give me all my fundamental rights",
        "what are all my fundamental rights",
        "what are my fundamental rights",
        "what are the fundamental rights",
        "fundamental rights list",
        "list of fundamental rights"
    ]):
        intents["fundamental_rights_all"] = True
    # Hindi
    if any(kw in q for kw in ["मौलिक अधिकार", "सभी मौलिक अधिकार", "मौलिक अधिकारों की सूची"]):
        intents["fundamental_rights_all"] = True
    # Hinglish (romanized Hindi)
    if any(kw in q for kw in [
        "mool adhikar", "sabhi mool adhikar", "mool adhikar ki soochi", "mere mool adhikar",
        "mool adhikar kaunse", "mool adhikar kaun se", "mere kya mool adhikar",
    ]):
        intents["fundamental_rights_all"] = True
    # Punjabi
    if any(kw in q for kw in ["ਮੂਲ ਅਧਿਕਾਰ", "ਸਾਰੇ ਮੂਲ ਅਧਿਕਾਰ", "ਮੂਲ ਅਧਿਕਾਰਾਂ ਦੀ ਸੂਚੀ"]):
        intents["fundamental_rights_all"] = True
    # Bengali
    if any(kw in q for kw in ["মৌলিক অধিকার", "সমস্ত মৌলিক অধিকার", "মৌলিক অধিকারের তালিকা"]):
        intents["fundamental_rights_all"] = True
    if any(kw in q for kw in [
        "right to equality",
        "equality before law",
        "articles 14-18",
        "article 14",
        "article 15",
        "article 16",
        "article 17",
        "article 18"
    ]):
        intents["right_to_equality"] = True
    return intents


def _compose_right_to_equality_answer(user_query: str) -> str:
    lines = []
    lines.append("Right to Equality — key points (Articles 14–18):")
    lines.append("- Article 14: Equality before law and equal protection of laws; no arbitrariness. Reasonable classification must have intelligible differentia and rational nexus to the objective.")
    lines.append("- Article 15: No discrimination by the State on religion, race, caste, sex, place of birth; access to public places protected (15(2)). Special provisions permitted: 15(3) women/children; 15(4), 15(5) SEBC/SC/ST (including admissions; 15(5) excludes minority institutions); 15(6) EWS.")
    lines.append("- Article 16: Equality of opportunity in public employment; no discrimination on similar grounds. Specific clauses: 16(3) residence requirements by Parliament; 16(4) reservation for backward classes; 16(4A) promotion reservation for SC/ST (subject to conditions); 16(4B) carry‑forward; 16(5) posts in religious institutions; 16(6) EWS.")
    lines.append("- Article 17: Abolition of ‘untouchability’ and its practice in any form; offences punishable (e.g., PCR Act 1955; SC/ST (Prevention of Atrocities) Act 1989).")
    lines.append("- Article 18: Abolition of titles (except military/academic distinctions); restrictions on accepting foreign titles/honours, especially for public office holders.")
    lines.append("")
    lines.append("Legal basis: Constitution of India — Articles 14, 15 (incl. 15(3), 15(4), 15(5), 15(6)), 16 (incl. 16(3), 16(4), 16(4A), 16(4B), 16(5), 16(6)), 17, 18.")
    return "\n".join(lines)


def _compress_contexts(user_query: str, contexts: List[Dict], max_chunks: int = 8) -> str:
    """Summarize retrieved contexts into a single concise, reasoning-oriented context.

    Uses the configured LLM with a small token budget; falls back to concatenation if generation fails.
    """
    # Prepare compact snippets from top-N strong contexts
    snippets = []
    for c in (contexts or [])[:max_chunks]:
        text = (c.get("text") or "").strip().replace("\n", " ")
        if not text:
            continue
        snippets.append(text[:800])  # trim per snippet to control size
    if not snippets:
        return ""

    system = {
        "role": "system",
        "content": (
            "You are a legal context compressor. Given excerpts and a user query, produce a concise synthesis that:\n"
            "- Extracts the controlling legal propositions, tests, exceptions, and definitions.\n"
            "- Groups related points and removes redundancy.\n"
            "- Cites Article/Section numbers inline where clear.\n"
            "- Emphasizes reasoning and application, not a laundry list.\n"
            "Output as short bullet points and 1–2 brief linking sentences. Plain text only."
        ),
    }
    user = {
        "role": "user",
        "content": (
            f"User Query: {user_query}\n\n"
            "Excerpts:\n- " + "\n- ".join(snippets)
        ),
    }
    try:
        llm = LLMClient()
        summary = llm.generate([system, user], temperature=0.1, top_p=0.9, max_tokens=600)
        return summary or "\n\n".join(snippets[:3])
    except Exception:
        return "\n\n".join(snippets[:3])


@lru_cache(maxsize=1)
def _load_legal_links() -> Dict[str, Dict]:
    """Load cross-link mapping between constitutional articles and statutory sections/keywords.

    JSON format example:
    {
      "19(1)(a)": {"Linked_Sections": ["69A IT Act", "69 IT Act"], "Keywords": ["speech","ban","public order"]},
      "19(2)": {"Linked_Sections": ["69A IT Act"], "Keywords": ["reasonable restriction","public order","decency","morality","security of state"]}
    }
    """
    try:
        here = os.path.dirname(__file__)
        path = os.path.join(here, "legal_links.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    # Default minimal mapping
    return {
        "19(1)(a)": {
            "Linked_Sections": ["69A IT Act", "69 IT Act"],
            "Keywords": ["speech", "publish", "ban", "expression", "censorship"],
        },
        "19(2)": {
            "Linked_Sections": ["69A IT Act"],
            "Keywords": ["reasonable restriction", "public order", "decency", "morality", "security of the state", "sovereignty"],
        },
        "32": {
            "Linked_Sections": [],
            "Keywords": ["writ", "remedy"],
        },
        "226": {
            "Linked_Sections": [],
            "Keywords": ["writ", "high court"],
        },
    }


def _detect_legal_refs(q: str) -> Dict[str, object]:
    ql = (q or "").lower()
    arts = re.findall(r"article\s+(\d+[a-z]?(?:\([^)]+\))?)", ql)
    secs = re.findall(r"section\s+(\d+[a-z]?)", ql)
    has_ref = bool(arts or secs)
    return {"articles": arts, "sections": secs, "has_ref": has_ref}


def _expand_query(q: str, det: Dict[str, object], links: Dict[str, Dict]) -> Tuple[str, str]:
    """Return (expanded_query, keyword_query)."""
    tokens: List[str] = [q]
    kw_tokens: List[str] = []
    # Expand from detected articles
    for a in det.get("articles", []) or []:
        a_key = a.upper()
        # normalize e.g., 19 -> consider 19(1)(a)/19(2)
        if a_key.isdigit() and a_key == "19":
            a_keys = ["19(1)(a)", "19(2)"]
        else:
            a_keys = [a_key]
        for ak in a_keys:
            cfg = links.get(ak) or links.get(ak.replace("ARTICLE ", "")) or {}
            secs = cfg.get("Linked_Sections") or []
            kws = cfg.get("Keywords") or []
            if secs:
                tokens.append("; related sections: " + ", ".join(secs))
            if kws:
                kw_tokens.extend(kws)
    # Expand from detected sections
    for s in det.get("sections", []) or []:
        # If Section 69A, hint Article 19(2)
        if s.upper() in ("69A", "69"):
            tokens.append("; constitutional grounds: Article 19(2) public order/sovereignty/decency/morality")
            kw_tokens.extend(["public order", "reasonable restriction", "procedure", "safeguard"])
    expanded = " ".join(tokens).strip()
    kw_query = (q + " " + " ".join(sorted(set(kw_tokens)))) if kw_tokens else q
    return expanded, kw_query


def _build_reasoning_memo(user_query: str, contexts: List[Dict]) -> str:
    """Construct a structured reasoning memo from retrieved chunks using light rules.

    Sections:
    - Context summary
    - Fundamental right(s)
    - Restriction(s)
    - Statutory link(s)
    - Remedy or safeguard(s)
    """
    texts = [(c.get("text") or "") for c in (contexts or [])]
    full = "\n".join(texts).lower()

    rights: List[str] = []
    for m in re.findall(r"article\s+\d+[a-z]?(?:\([^)]+\))?", full):
        item = m.strip().title()
        if item not in rights:
            rights.append(item)

    grounds = [
        "sovereignty and integrity of india",
        "security of the state",
        "public order",
        "decency",
        "morality",
        "friendly relations with foreign states",
        "contempt of court",
        "defamation",
        "incitement to an offence",
    ]
    restr: List[str] = [g for g in grounds if g in full]

    # Statutory links
    statutes: List[str] = []
    if re.search(r"section\s+69a", full):
        statutes.append("IT Act s. 69A [Source: IT Act s. 69A]")
    if re.search(r"section\s+69(?!a)", full):
        statutes.append("IT Act s. 69 [Source: IT Act s. 69]")
    if re.search(r"section\s+144", full) and ("code of criminal procedure" in full or "crpc" in full):
        statutes.append("CrPC s. 144 [Source: CrPC s. 144]")

    # Remedies / safeguards
    remedies: List[str] = []
    if "article 32" in full:
        remedies.append("Art. 32 (Supreme Court writs)")
    if "article 226" in full:
        remedies.append("Art. 226 (High Court writs)")
    if "reasons to be recorded in writing" in full:
        remedies.append("Reasons to be recorded in writing [Source: IT Act s. 69/69A framework]")
    if "procedure and safeguards" in full or "procedure" in full and "safeguard" in full:
        remedies.append("Procedure and safeguards in delegated rules")

    # Context summary (brief)
    summary_bits: List[str] = []
    if rights:
        summary_bits.append(f"Rights: {', '.join(sorted(set(rights))[:3])}")
    if restr:
        summary_bits.append(f"Restrictions: {', '.join(sorted(set(restr))[:4])}")
    if statutes:
        summary_bits.append(f"Statutes: {', '.join(statutes[:3])}")
    summary = "; ".join(summary_bits) or "Key constitutional and statutory provisions summarized below."

    lines: List[str] = []
    lines.append("Context summary:")
    lines.append(f"- {summary}")
    lines.append("")
    lines.append("Fundamental right(s):")
    if rights:
        for r in rights[:6]:
            lines.append(f"- {r}")
    else:
        lines.append("- (not explicit in retrieved text)")
    lines.append("")
    lines.append("Restriction(s):")
    if restr:
        for g in restr[:8]:
            lines.append(f"- {g}")
    else:
        lines.append("- (no clear restriction grounds found)")
    lines.append("")
    lines.append("Statutory link(s):")
    if statutes:
        for s in statutes[:6]:
            lines.append(f"- {s}")
    else:
        lines.append("- (no explicit statutory link found)")
    lines.append("")
    lines.append("Remedy or safeguard(s):")
    if remedies:
        for r in remedies[:6]:
            lines.append(f"- {r}")
    else:
        lines.append("- (no explicit remedy/safeguard found)")

    memo = "\n".join(lines)
    try:
        logging.getLogger(__name__).info("RAG debug memo: %s", memo)
    except Exception:
        pass
    return memo
