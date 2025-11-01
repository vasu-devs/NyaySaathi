import React, { useState, useRef, useEffect } from "react";
import SideBar from "../Sidebar/SideBar";
import Nav from "../Navbar/Nav";

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [hasStarted, setHasStarted] = useState(false);
  const containerRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (hasStarted) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, hasStarted]);

  function sendMessage(text) {
    if (!text.trim()) return;

    if (!hasStarted) {
      setHasStarted(true);
    }

    const userMsg = { id: Date.now(), sender: "user", text };
    setMessages((m) => [...m, userMsg]);
    setInput("");

    setTimeout(() => {
      const botReply = {
        id: Date.now() + 1,
        sender: "bot",
        text: "No, your landlord cannot legally cut off essential services like water or electricity.\nSend a formal complaint and seek legal help if needed.",
      };
      setMessages((m) => [...m, botReply]);
    }, 700);
  }

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
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type your message and press Enter"
                    className="flex-1 outline-none text-xs sm:text-sm px-2 sm:px-3 py-2"
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
                          {m.text}
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
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Type your message and press Enter"
                      className="flex-1 outline-none text-xs sm:text-sm px-2 sm:px-3 py-2"
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
        </div>
      </main>
    </div>
  );
};

export default Chatbot;
