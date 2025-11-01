import React, { useState } from "react";
import { Menu, X } from "lucide-react";

const Nav = () => {
  const [language, setLanguage] = useState("En");
  const [menuOpen, setMenuOpen] = useState(false);

  const navItems = [
    { label: "Home", href: "#" },
    { label: "About Us", href: "#" },
    { label: "Features", href: "#" },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 w-full bg-white shadow-sm z-50">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 sm:px-6 md:px-8 py-3 relative">
        {/* Left - Logo */}
        <div className="flex items-center gap-2">
          <img
            src="/LogoSaathi.svg"
            alt="NyaySaathi Logo"
            className="w-6 h-6"
          />
          {/* Hide text on mobile */}
          <span className="text-xl font-semibold text-[#0B304A] hidden md:inline">
            NyaySaathi
          </span>
        </div>

        {/* Center - Emergency Help (always visible, consistent aspect ratio) */}
        <div className="absolute left-1/2 -translate-x-1/2 md:static md:translate-x-0 flex justify-center">
          <button
            className="bg-[#2C6BA1] hover:bg-[#1F5A85] text-white font-semibold 
                       rounded-md transition-colors
                        sm:min-w-[180px] sm:
                       w-[150px]
                       h-[42px] sm:h-[46px] 
                      flex items-center justify-center
                       text-sm sm:text-base cursor-pointer"
          >
            Get Emergency Help
          </button>
        </div>

        {/* Desktop Links and Controls */}
        <div className="hidden md:flex items-center gap-8">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="text-[#0B304A] hover:text-[#1F5A85] font-medium transition-colors"
            >
              {item.label}
            </a>
          ))}

          <button
            onClick={() => setLanguage(language === "En" ? "Hi" : "En")}
            className="px-3 py-1.5 rounded-md bg-[#EAF1F8] text-[#0B304A] font-semibold  cursor-pointer"
          >
            {language}
          </button>
        </div>

        {/* Right - Hamburger (only mobile) */}
        <button
          className="md:hidden text-[#0B304A]"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Dropdown Menu */}
      {menuOpen && (
        <div className="flex flex-col items-center gap-4 py-4 border-t border-gray-200 md:hidden mt-14">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="text-[#0B304A] hover:text-[#1F5A85] font-medium transition-colors"
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </a>
          ))}

          <button
            onClick={() => setLanguage(language === "En" ? "Hi" : "En")}
            className="px-3 py-1.5 rounded-md bg-[#EAF1F8] text-[#0B304A] font-semibold"
          >
            {language}
          </button>
        </div>
      )}
    </nav>
  );
};

export default Nav;
