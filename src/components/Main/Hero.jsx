import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const Hero = () => {
  const [activeTab, setActiveTab] = useState("nyayshala");
  const [openIndex, setOpenIndex] = useState(null);

  const nyayShalaItems = [
    {
      title: "What to do if you are wrongly detained?",
      content:
        "If you are wrongly detained, remain calm, ask for identification, request to contact a lawyer, and note details (time, place, officers). File a complaint and seek legal help immediately.",
    },
    {
      title: "Your rights as a tenant in India.",
      content:
        "Tenants have rights around notice, repair, eviction, and rent. Check your lease and local tenancy laws — if needed, consult a legal aid or mediator.",
    },
    {
      title: "How to file a First Information Report (FIR)?",
      content:
        "Visit the nearest police station or use the online portal, provide a clear statement, and insist on a receipt. If refused, seek higher authority or legal assistance.",
    },
    {
      title: "Understanding a simple rental agreement.",
      content:
        "A rental agreement should clearly state rent, duration, deposit, responsibilities, and termination clauses. Keep a signed copy and record payments.",
    },
  ];

  const nyayMapItems = [
    {
      title: "Find nearby legal aid",
      content:
        "Search for nearby legal aid centers, NGOs, and pro bono lawyers using the NyayMap. Filter by services and ratings.",
    },
    {
      title: "Locate courts and police stations",
      content:
        "Get directions and contact info for local courts and police stations. Confirm timings and required documents before visiting.",
    },
    {
      title: "Community helpers",
      content:
        "Connect with trained community helpers and volunteers who can guide you through simple procedures and provide immediate support.",
    },
  ];

  const items = activeTab === "nyayshala" ? nyayShalaItems : nyayMapItems;

  return (
    <section className="w-full bg-white text-[#0A2B42] flex flex-col items-center justify-center px-6 sm:px-10 lg:px-16 py-16 mt-15">
      {/* ---------------- Heading ---------------- */}
      <div className="w-full max-w-6xl mx-auto flex flex-col items-center md:items-start text-center md:text-left mb-10">
        <div className="max-w-3xl">
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-snug mb-4">
            Legal Help, Made Simple And Safe.
          </h1>
          <p className="text-[#99BACE] text-base sm:text-lg leading-relaxed">
            You don’t need to be a lawyer to understand your rights. NyaySaathi
            connects you with verified legal sources, expert guidance, and
            trusted assistance.
          </p>
        </div>
      </div>

      {/* ---------------- Action Cards ---------------- */}
      <div className="flex flex-col sm:flex-row flex-wrap justify-center items-stretch gap-12 mt-12 w-full max-w-6xl">
        {/* Card 1 */}
        <div className="flex flex-col justify-between items-center text-center bg-[#F8FAFC] border border-[#E5E9F0] rounded-2xl p-6 flex-1 min-w-[280px] sm:max-w-[320px] md:max-w-[360px] shadow-lg transition-transform duration-200 hover:-translate-y-1 hover:shadow-xl">
          <img
            src="/bot.svg"
            alt="Legal Docs"
            className="w-10 h-10 sm:w-12 sm:h-12 md:w-14 md:h-14 lg:w-16 lg:h-16 mb-4"
          />
          <p className="text-[#0A2B42] text-lg font-semibold mb-3">
            Get Legal Documents
          </p>
          <p className="text-[#99BACE] text-sm mb-6">
            Access templates verified by legal experts.
          </p>
          <button className="border border-[#0A2B42] text-[#0A2B42] px-5 sm:px-6 md:px-7 py-2 rounded-lg text-sm font-medium hover:bg-[#0A2B42] hover:text-white transition-colors cursor-pointer">
            Explore Docs
          </button>
        </div>

        {/* Card 2 */}
        <div className="flex flex-col justify-between items-center text-center bg-[#F8FAFC] border border-[#E5E9F0] rounded-2xl p-6 flex-1 min-w-[280px] sm:max-w-[320px] md:max-w-[360px] shadow-lg transition-transform duration-200 hover:-translate-y-1 hover:shadow-xl">
          <img
            src="/tabler_text-scan-2.svg"
            alt="Lawyer Connect"
            className="w-10 h-10 sm:w-12 sm:h-12 md:w-14 md:h-14 lg:w-16 lg:h-16 mb-4"
          />
          <p className="text-[#0A2B42] text-lg font-semibold mb-3">
            Connect With Lawyers
          </p>
          <p className="text-[#99BACE] text-sm mb-6">
            Find verified legal experts for your needs.
          </p>
          <button className="border border-[#0A2B42] text-[#0A2B42] px-5 sm:px-6 md:px-7 py-2 rounded-lg text-sm font-medium hover:bg-[#0A2B42] hover:text-white transition-colors cursor-pointer">
            Find Now
          </button>
        </div>

        {/* Card 3 */}
        <div className="flex flex-col justify-between items-center text-center bg-[#F8FAFC] border border-[#E5E9F0] rounded-2xl p-6 flex-1 min-w-[280px] sm:max-w-[320px] md:max-w-[360px] shadow-lg transition-transform duration-200 hover:-translate-y-1 hover:shadow-xl">
          <img
            src="/ion_book-outline.svg"
            alt="Emergency Help"
            className="w-10 h-10 sm:w-12 sm:h-12 md:w-14 md:h-14 lg:w-16 lg:h-16 mb-4"
          />
          <p className="text-[#0A2B42] text-lg font-semibold mb-3">
            Get Emergency Help
          </p>
          <p className="text-[#99BACE] text-sm mb-6">
            Contact legal aid instantly during emergencies.
          </p>
          <button className="border border-[#0A2B42] text-[#0A2B42] px-5 sm:px-6 md:px-7 py-2 rounded-lg text-sm font-medium hover:bg-[#0A2B42] hover:text-white transition-colors cursor-pointer">
            Get Help
          </button>
        </div>
      </div>

      {/* ---------------- Verified Sources ---------------- */}
      <div className="flex flex-col items-center mt-25 w-full">
        <p className="text-[#99BACE] text-sm uppercase tracking-wider mb-4">
          Verified Legal Sources
        </p>
        <div className="flex flex-wrap justify-center items-center gap-18 sm:gap-12 lg:gap-60 md:gap-45 mt-10">
          <img
            src="/Mygov.svg"
            alt="MyGov"
            className="h-6 sm:h-8 md:h-10 lg:h-12 object-contain"
          />
          <img
            src="/IndiaCode.svg"
            alt="India Code"
            className="h-6 sm:h-8 md:h-10 lg:h-12 object-contain"
          />
          <img
            src="/Court.svg"
            alt="Ministry of Justice"
            className="h-6 sm:h-8 md:h-10 lg:h-12 object-contain"
          />
        </div>
      </div>

      {/* ---------------- How NyaySaathi Works ---------------- */}
      <div className="w-full max-w-6xl mx-auto mt-30">
        <h2 className="text-2xl md:text-3xl font-serif text-[#0A2B42] text-center mb-8">
          How NyaySaathi Works
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="bg-white border border-[#E5E9F0] rounded-lg p-6 shadow-sm flex flex-col items-start">
            <div className="w-full flex justify-center mb-4">
              <img
                src="/ChooseTrial.svg"
                alt="I have a problem"
                className="h-20 sm:h-24 md:h-28 lg:h-32 object-contain"
              />
            </div>
            <h3 className="font-semibold text-lg mb-2 text-left">
              I have a problem
            </h3>
            <p className="text-[#99BACE] text-sm text-left">
              You are in control. Start with what you need most ask the AI
              Saathi, scan a document with LegalLens, or connect anonymously
              with a verified helper.
            </p>
          </div>

          <div className="bg-white border border-[#E5E9F0] rounded-lg p-6 shadow-sm flex flex-col items-start">
            <div className="w-full flex justify-center mb-4">
              <img
                src="/GetAns.svg"
                alt="I get a solution"
                className="h-20 sm:h-24 md:h-28 lg:h-32 object-contain"
              />
            </div>
            <h3 className="font-semibold text-lg mb-2 text-left">
              I get a solution
            </h3>
            <p className="text-[#99BACE] text-sm text-left">
              Clear, plain-language explanations and tools so you can truly
              understand your rights and next steps.
            </p>
          </div>

          <div className="bg-white border border-[#E5E9F0] rounded-lg p-6 shadow-sm flex flex-col items-start">
            <div className="w-full flex justify-center mb-4">
              <img
                src="/MoveForward.svg"
                alt="I know what to do"
                className="h-20 sm:h-24 md:h-28 lg:h-32 object-contain"
              />
            </div>
            <h3 className="font-semibold text-lg mb-2 text-left">
              I know what to do
            </h3>
            <p className="text-[#99BACE] text-sm text-left">
              Move forward with confidence , connect to verified helpers, file
              documents, or get emergency guidance when needed.
            </p>
          </div>
        </div>
      </div>

      {/* ---------------- Learning & Resources ---------------- */}
      <div className="w-full max-w-6xl mx-auto mt-25 mb-12">
        <h2 className="text-2xl md:text-3xl font-serif text-[#0A2B42] text-center mb-10">
          Learning & Resources
        </h2>

        <div className="flex justify-center gap-4 mb-10">
          <button
            onClick={() => {
              setActiveTab("nyayshala");
              setOpenIndex(null);
            }}
            className={`rounded-lg cursor-pointer px-4 py-1 text-sm font-medium transition-colors ${
              activeTab === "nyayshala"
                ? "bg-[#0A2B42] text-white"
                : "bg-white border border-[#E5E9F0] text-[#99BACE]"
            }`}
          >
            NyayShala
          </button>
          <button
            onClick={() => {
              setActiveTab("nyaymap");
              setOpenIndex(null);
            }}
            className={`rounded-lg cursor-pointer px-4 py-1 text-sm font-medium transition-colors ${
              activeTab === "nyaymap"
                ? "bg-[#0A2B42] text-white"
                : "bg-white border border-[#E5E9F0] text-[#99BACE]"
            }`}
          >
            NyayMap
          </button>
        </div>

        <p className="text-center text-[#0A2B42] font-semibold mb-1">
          Know Your Rights
        </p>
        <p className="text-center text-[#99BACE] font-normal mb-10">
          We have broken down complex laws into simple, easy-to-understand
          guides.
        </p>
        <div className="max-w-2xl mx-auto">
          <div className="space-y-3">
            {items.map((it, idx) => {
              const isOpen = openIndex === idx;
              return (
                <div key={idx} className="border border-transparent rounded-md">
                  <button
                    onClick={() => setOpenIndex(isOpen ? null : idx)}
                    aria-expanded={isOpen}
                    aria-controls={`panel-${idx}`}
                    className={`w-full flex justify-between items-center bg-[#F8FAFC] text-[#0A2B42] py-3 px-4 text-left transition-all ${
                      isOpen ? "rounded-t-md" : "rounded-md"
                    }`}
                  >
                    <span>{it.title}</span>
                    <svg
                      className={`w-5 h-5 ml-2 transform transition-transform ${
                        isOpen ? "rotate-180" : "rotate-0"
                      }`}
                      viewBox="0 0 20 20"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M5 8l5 5 5-5"
                        stroke="#0A2B42"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        id={`panel-${idx}`}
                        role="region"
                        initial={{ opacity: 0, scaleY: 0 }}
                        animate={{ opacity: 1, scaleY: 1 }}
                        exit={{ opacity: 0, scaleY: 0 }}
                        transition={{ duration: 0.22, ease: "easeInOut" }}
                        style={{ transformOrigin: "top" }}
                        className="py-3 bg-white border border-t-0 border-[#E5E9F0] rounded-b-md px-4"
                      >
                        <p className="text-sm text-[#556E7F]">{it.content}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
