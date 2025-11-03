import React, { useEffect, useState, useCallback, useMemo } from "react";
import Nav from "../Navbar/Nav";
import { getDailyNyayShala } from "../../lib/api";

const FIELDS = ["contract", "criminal", "family", "ip", "tax", "property"];

export default function NyayShala() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openIdx, setOpenIdx] = useState(null);
  const displayList = useMemo(() => {
    const list = [];
    const target = 18;
    if (items && items.length) {
      for (let i = 0; i < target; i++) list.push(items[i % items.length]);
    }
    return list;
  }, [items]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // Default to cached daily set for instant load
      const data = await getDailyNyayShala(undefined, false);
      setItems(data.items || []);
    } catch (e) {
      console.error(e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadRandom = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getDailyNyayShala(undefined, true);
      setItems(data.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="min-h-screen bg-white">
      <Nav />
      <main className="pt-16 max-w-6xl mx-auto px-4 py-8">
        {/* Breadcrumb */}
        <div className="text-xs text-[#99BACE] mb-3">Home &gt; NyayShala</div>
        <div className="flex items-center justify-between">
          <div className="w-full flex flex-col items-center">
            <h1 className="text-4xl font-serif font-semibold text-[#0A2B42] text-center">NyayShala</h1>
            <p className="text-sm text-[#2C6BA1] mt-2 text-center max-w-2xl">Know Your Rights. We've translated complex legal topics into simple guides you can actually use.</p>
          </div>
          <div className="flex items-center">
            <button
              onClick={loadRandom}
              disabled={loading}
              className="mr-2 border border-[#EEF6FB] rounded px-3 py-1 text-[#0A2B42] hover:bg-[#F7FBFE] disabled:opacity-50"
              title="Show a shuffled set"
            >
              Shuffle
            </button>
          </div>
        </div>

        {loading ? (
          <div className="mt-6 text-[#99BACE]">Loading...</div>
        ) : (
          <>
            <h2 className="mt-10 mb-4 text-2xl font-semibold text-[#0A2B42]">Trending Now</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {displayList.map((it, idx) => {
                const dark = idx % 2 === 1; // alternate backgrounds
                const cardBg = dark ? "bg-[#E7F3FB]" : "bg-[#F7FBFE]";
                const hoverBg = dark ? "hover:bg-[#E3EFF7]" : "hover:bg-[#EEF6FB]";
                const yearMatch = (it.content || "").match(/\b(19\d{2}|20\d{2})\b/);
                const year = yearMatch ? yearMatch[1] : "";
                const expanded = openIdx === idx;
                const spanClass = expanded ? "sm:col-span-2 lg:col-span-3" : "col-span-1";
                const padClass = expanded ? "p-6 md:p-7 lg:p-8" : "p-5";
                const heightClass = expanded ? "min-h-56 md:min-h-64" : "min-h-40";
                return (
                  <div key={idx} className={`${spanClass} rounded-2xl border border-[#EEF6FB] ${cardBg} ${hoverBg} transition flex flex-col ${padClass} ${heightClass}`}>
                    {/* Title only on the card face */}
                    <div className="mt-1 text-lg md:text-[18px] font-semibold text-[#0A2B42] flex-1 leading-snug">{it.title}</div>
                    <div className="mt-4 flex items-center justify-between">
                      <div className="text-sm font-medium text-[#0A2B42]">{year}</div>
                      <button
                        onClick={() => setOpenIdx(expanded ? null : idx)}
                        className="text-[#2C6BA1] text-sm hover:underline"
                      >
                        {expanded ? "Hide Details" : "Learn More"}
                      </button>
                    </div>

                    {expanded && (
                      <div className="mt-4 bg-white border border-[#EEF6FB] rounded-xl p-4">
                        <div className="whitespace-pre-wrap text-[#0A2B42] text-sm">{it.content}</div>
                        <div className="mt-3 flex items-center justify-end">
                          <button
                            onClick={() => setOpenIdx(null)}
                            className="text-[#99BACE] hover:text-[#2C6BA1] text-sm"
                          >
                            Close
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            {items.length===0 && (
              <div className="mt-6 text-[#99BACE]">No items yet. Try generating from admin (coming soon) or check back later.</div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
