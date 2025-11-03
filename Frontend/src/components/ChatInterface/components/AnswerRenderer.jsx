import React from "react";
import ReactMarkdown from "react-markdown";

// Parse a structured plain-text answer into sections and render with headings/subheadings
function parseAnswer(text) {
  const lines = (text || "").split(/\r?\n/).map((l) => l.trimEnd());
  // Title is first non-empty line unless it is a section marker
  let idx = 0;
  while (idx < lines.length && !lines[idx].trim()) idx++;
  let title = "";
  if (idx < lines.length && !/^\d+\./.test(lines[idx]) && !/^\s*(Direct Answer|Key Points|Sources)/i.test(lines[idx])) {
    title = lines[idx].trim();
    idx++;
  }

  // Collect remaining content
  const rest = lines.slice(idx);

  // Sections to collect
  const sections = [];
  const pushSection = (name, content) => {
    sections.push({ name, content });
  };

  // Helper to flush paragraph buffer to content array
  const flushParagraph = (buf, content) => {
    if (buf.length) {
      // Preserve line breaks within a paragraph block
      content.push({ type: "p", text: buf.join("\n") });
      buf.length = 0;
    }
  };

  let i = 0;
  let currentName = null;
  let currentContent = [];
  let paraBuf = [];

  const commitCurrent = () => {
    flushParagraph(paraBuf, currentContent);
    if (currentName || currentContent.length) {
      pushSection(currentName || "", currentContent);
    }
    currentName = null;
    currentContent = [];
  };

  const sectionHeaderRe = /^(\d+(?:\.\d+)*)\.?\s*(.*)$/; // 1., 1.1, 2. etc

  while (i < rest.length) {
    const line = rest[i].trim();
    i++;
    if (!line) {
      // Paragraph break
      flushParagraph(paraBuf, currentContent);
      continue;
    }

    const m = line.match(sectionHeaderRe);
    if (m) {
      // Start of a new section
      commitCurrent();
      const num = m[1];
      const name = m[2] || "";
      currentName = name || `Section ${num}`;
      continue;
    }

    // Ordered list detection: lines starting with digit dot space (e.g., "1. item")
    const listMatch = line.match(/^\d+\.\s+(.+)$/);
    if (listMatch) {
      flushParagraph(paraBuf, currentContent);
      const items = [listMatch[1]];
      // collect following numeric list items
      while (i < rest.length) {
        const lm = rest[i].trim().match(/^\d+\.\s+(.+)$/);
        if (!lm) break;
        items.push(lm[1]);
        i++;
      }
      currentContent.push({ type: "ol", items });
      continue;
    }

    // Unordered list detection: lines starting with '- '
  const ulMatch = line.match(/^-\s+(.+)$/);
    if (ulMatch) {
      flushParagraph(paraBuf, currentContent);
      const items = [ulMatch[1]];
      while (i < rest.length) {
  const lm = rest[i].trim().match(/^-\s+(.+)$/);
        if (!lm) break;
        items.push(lm[1]);
        i++;
      }
      currentContent.push({ type: "ul", items });
      continue;
    }

    // Fallback: accumulate paragraph text
    paraBuf.push(line);
  }
  // finalize
  commitCurrent();

  return { title, sections };
}

export default function AnswerRenderer({ text, markdown = false }) {
  if (markdown) {
    // Render Markdown directly; keep typography minimal
    return (
      <div className="space-y-4 prose prose-sm sm:prose-base max-w-none">
        <ReactMarkdown>{text || ""}</ReactMarkdown>
      </div>
    );
  }

  const { title, sections } = parseAnswer(text);

  return (
    <div className="space-y-4">
      {title ? (
        <h2 className="text-[#0A2B42] font-semibold text-lg sm:text-xl md:text-2xl leading-snug">
          {title}
        </h2>
      ) : null}

      {sections.map((sec, idx) => (
        <section key={idx} className="space-y-2">
          {sec.name ? (
            <h3 className="text-[#0A2B42] font-semibold text-sm sm:text-base md:text-lg mt-2">
              {sec.name}
            </h3>
          ) : null}

          {sec.content.map((block, i) => {
            if (block.type === "p") {
              return (
                <p key={i} className="text-[#0A2B42] text-xs sm:text-sm md:text-base leading-relaxed whitespace-pre-wrap">
                  {block.text}
                </p>
              );
            }
            if (block.type === "ol") {
              return (
                <ol key={i} className="list-decimal pl-5 text-[#0A2B42] text-xs sm:text-sm md:text-base space-y-1">
                  {block.items.map((it, j) => (
                    <li key={j}>{it}</li>
                  ))}
                </ol>
              );
            }
            if (block.type === "ul") {
              return (
                <ul key={i} className="list-disc pl-5 text-[#0A2B42] text-xs sm:text-sm md:text-base space-y-1">
                  {block.items.map((it, j) => (
                    <li key={j}>{it}</li>
                  ))}
                </ul>
              );
            }
            return null;
          })}
        </section>
      ))}
    </div>
  );
}
