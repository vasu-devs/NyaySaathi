import React, { useState, useRef, useEffect, useCallback } from "react";
import { useLocation } from "react-router-dom";
import SideBar from "../Sidebar/SideBar";
import Nav from "../Navbar/Nav";
import { streamChat, askOnce, debugRetrieve, pingHealth, getClientConfig } from "../../lib/api";
import AnswerRenderer from "./components/AnswerRenderer";

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [hasStarted, setHasStarted] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sources, setSources] = useState(null);
  const [health, setHealth] = useState({ status: "unknown" });
  const [clientCfg, setClientCfg] = useState({ markdown: false });
  const stopRef = useRef(null);
  const containerRef = useRef(null);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);
  const location = useLocation();

  useEffect(() => {
    if (hasStarted) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, hasStarted]);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        textareaRef.current.scrollHeight + "px";
    }
  }, [input]);

  // Ping backend health once on mount (optional indicator)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const h = await pingHealth();
        if (!cancelled) setHealth({ status: "ok", ...h });
      } catch {
        if (!cancelled) setHealth({ status: "error" });
      }
      // Fetch public client config (markdown toggle)
      try {
        const cfg = await getClientConfig();
        if (!cancelled && cfg) setClientCfg(cfg);
      } catch {
        // ignore; default remains false
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Optional prefill from navigation state or URL query (?q=...), without auto-send
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const q = params.get("q");
    const st = (location && location.state && location.state.prefill) || null;
    if (st && typeof st === "string" && st.trim()) {
      setInput(st);
      // Bring chat UI into focus to encourage sending
      if (!hasStarted) setHasStarted(true);
      // Focus the textarea for immediate editing/sending
      setTimeout(() => textareaRef.current?.focus(), 0);
      return;
    }
    if (q) {
      setInput(q);
      if (!hasStarted) setHasStarted(true);
      setTimeout(() => textareaRef.current?.focus(), 0);
    }
  }, [location, hasStarted]);

  const sendMessage = useCallback((text) => {
    const q = text.trim();
    if (!q || isStreaming) return;

    if (!hasStarted) setHasStarted(true);

    const userMsg = { id: Date.now(), sender: "user", text: q };
    setMessages((m) => [...m, userMsg]);
    setInput("");

    // Reset textarea height after sending
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    // Fetch top contexts (for transparency and debug)
    setSources(null);
    debugRetrieve(q, 6).then((res) => setSources(res?.contexts || null)).catch(() => setSources(null));

    // Start streaming from backend. If SSE fails or returns nothing, fall back to one-shot.
    let assistantId = Date.now() + 1;
    setIsStreaming(true);
    let gotAnyToken = false;
    stopRef.current = streamChat(
      q,
      (token) => {
        gotAnyToken = true;
        setMessages((m) => {
          if (m.length > 0 && m[m.length - 1].sender === "bot") {
            const copy = m.slice();
            copy[copy.length - 1] = {
              ...copy[copy.length - 1],
              text: (copy[copy.length - 1].text || "") + token,
            };
            return copy;
          }
          return [...m, { id: assistantId, sender: "bot", text: token }];
        });
      },
      async () => {
        setIsStreaming(false);
        // If SSE yielded nothing (CORS/proxy hiccup), try non-streaming fallback once
        if (!gotAnyToken) {
          try {
            const ans = await askOnce(q);
            setMessages((m) => {
              if (m.length > 0 && m[m.length - 1].sender === "bot") {
                const copy = m.slice();
                copy[copy.length - 1] = { ...copy[copy.length - 1], text: ans };
                return copy;
              }
              return [...m, { id: assistantId, sender: "bot", text: ans }];
            });
          } catch {
            // Surface a helpful error instead of silent failure
            const msg = "Unable to reach AI service. Check API_BASE and backend.";
            setMessages((m) => [...m, { id: assistantId, sender: "bot", text: msg }]);
          }
        }
      }
    );
  }, [isStreaming, hasStarted]);

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <Nav />
      <SideBar />

      <main className="pt-16 pl-16 sm:pl-20 lg:pl-0">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 pb-8">
          <div className="text-xs text-[#99BACE] mt-4">Home &gt; AI Saathi</div>

          {/* Health indicator */}
          {health.status !== "ok" && (
            <div className="mt-3 text-xs text-[#b06565] bg-[#fde8e8] border border-[#f5c2c2] rounded px-3 py-2 inline-block">
              Backend not ready or unreachable. Ensure API is running at http://localhost:8000.
            </div>
          )}

          {/* Welcome section - only visible before chat starts */}
          {!hasStarted && (
            <div className="flex flex-col items-center justify-center mt-12 sm:mt-16 md:mt-24 transition-all duration-300">
              <img
                src="/LogoSaathi.svg"
                alt="bot"
                className="w-16 h-16 sm:w-20 sm:h-20 mb-4"
              />
              <p className="text-[#0A2B42] text-center text-sm sm:text-base px-4">
                Hello, I am your AI Saathi.
                <br />I am trained on verified Indian legal information.
                <br />
                How can I help you today?
              </p>
            </div>
          )}

          {/* Input Box - centered when not started, moves down when chat begins */}
          {!hasStarted ? (
            <div className="flex items-center justify-center min-h-[30vh] sm:min-h-[40vh]">
              <div className="w-full max-w-3xl mx-auto bg-white rounded-xl border border-[#EEF6FB] p-3 sm:p-4 shadow-sm">
                <label className="text-xs sm:text-sm text-[#99BACE]">
                  Start Chat...
                </label>
                <div className="flex items-center gap-2 sm:gap-4 mt-3">
                  <button className="p-1.5 sm:p-2 rounded-full bg-[#F1F7FB] shrink-0">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="w-4 h-4 sm:w-5 sm:h-5 text-[#2C6BA1]"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                  </button>
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type your message and press Enter"
                    rows={1}
                    className="flex-1 outline-none text-xs sm:text-sm px-2 sm:px-3 py-2 resize-none overflow-hidden max-h-32"
                  />
                    <button
                    onClick={() => sendMessage(input)}
                    className="bg-[#0A2B42] text-white rounded-full w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center hover:bg-[#0D3A5A] transition shrink-0"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="w-3.5 h-3.5 sm:w-4 sm:h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M22 2L11 13" />
                      <path d="M22 2l-7 20-4-9-9-4 20-7z" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Messages area */}
              <div className="mt-8 sm:mt-12 bg-transparent min-h-[30vh]">
                <div className="w-full max-w-3xl mx-auto">
                  <div ref={containerRef} className="space-y-4 sm:space-y-6">
                    {messages.map((m) => (
                      <div
                        key={m.id}
                        className={`flex ${
                          m.sender === "user" ? "justify-end" : "justify-start"
                        }`}
                      >
                        <div
                          className={`rounded-lg p-3 sm:p-4 max-w-[85%] sm:max-w-[80%] md:max-w-[75%] whitespace-pre-line text-xs sm:text-sm md:text-base ${
                            m.sender === "user"
                              ? "bg-white border border-[#E6EEF6] text-[#0A2B42]"
                              : "bg-[#E7F3FB] text-[#0A2B42]"
                          }`}
                        >
                          {m.sender === "bot" ? (
                            <AnswerRenderer text={m.text} markdown={!!clientCfg?.markdown} />
                          ) : (
                            m.text
                          )}
                        </div>
                      </div>
                    ))}
                    <div ref={bottomRef} />
                  </div>
                </div>
              </div>

              {/* Input Box - moved to bottom after chat starts */}
              <div className="mt-8 sm:mt-12">
                <div className="w-full max-w-3xl mx-auto bg-white rounded-xl border border-[#EEF6FB] p-3 sm:p-4 shadow-sm">
                  <label className="text-xs sm:text-sm text-[#99BACE]">
                    Follow Up...
                  </label>
                  <div className="flex items-center gap-2 sm:gap-4 mt-3">
                    <button className="p-1.5 sm:p-2 rounded-full bg-[#F1F7FB] shrink-0">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="w-4 h-4 sm:w-5 sm:h-5 text-[#2C6BA1]"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 4v16m8-8H4"
                        />
                      </svg>
                    </button>
                    <textarea
                      ref={textareaRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Type your message and press Enter"
                      rows={1}
                      className="flex-1 outline-none text-xs sm:text-sm px-2 sm:px-3 py-2 resize-none overflow-hidden max-h-32"
                    />
                    <button
                      onClick={() => sendMessage(input)}
                      className="bg-[#0A2B42] text-white rounded-full w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center hover:bg-[#0D3A5A] transition shrink-0"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="w-3.5 h-3.5 sm:w-4 sm:h-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M22 2L11 13" />
                        <path d="M22 2l-7 20-4-9-9-4 20-7z" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}
                    {/* Sources (debug/transparent) */}
                    {sources && sources.filter((s) => (s.score ?? 0) >= 0.35).length > 0 && (
                      <div className="text-xs sm:text-sm text-[#2C6BA1] bg-[#F1F7FB] border border-[#E6EEF6] rounded p-3">
                        <div className="font-medium mb-1">Top sources used:</div>
                        <ul className="list-disc pl-5 space-y-1">
                          {sources.filter((s) => (s.score ?? 0) >= 0.35).slice(0, 3).map((s, idx) => (
                            <li key={idx}>
                              [{s.doc_id}:{s.chunk_id}] {s.text?.slice(0, 160)}{s.text && s.text.length > 160 ? "…" : ""}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
        </div>
      </main>
    </div>
  );
};

export default Chatbot;
