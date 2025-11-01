const Footer = () => {
  return (
    <footer className="bg-[#0A2B42] text-white px-6 md:px-12 lg:px-20 py-12">
      {/* Top Section */}
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row justify-between gap-12 lg:gap-24">
        {/* Left - NyaySaathi Section */}
        <div className="flex-1">
          <h2 className="text-2xl font-semibold mb-4">NyaySaathi</h2>
          <p className="text-white leading-relaxed max-w-sm text-sm">
            A non-profit, mission-driven platform dedicated to making justice
            accessible for every Indian.
          </p>
        </div>

        {/* Right - Three Columns */}
        <div className="flex flex-wrap lg:flex-nowrap gap-16 lg:gap-40 text-[#99BACE]">
          {/* GET HELP */}
          <div>
            <h3 className="text-lg text-white font-semibold mb-4">GET HELP</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Ask the AI Saathi
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Check a Document
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Talk to a Helper
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Emergency Help
                </a>
              </li>
            </ul>
          </div>

          {/* EXPLORE */}
          <div>
            <h3 className="text-lg text-white font-semibold mb-4">EXPLORE</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Learn (NyayShala)
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Discuss (NyayShaba)
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Find (NyayMap)
                </a>
              </li>
            </ul>
          </div>

          {/* COMPANY */}
          <div>
            <h3 className="text-lg text-white font-semibold mb-4">COMPANY</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Our Sources
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  About Us
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Contact Us
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Privacy Policy
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Disclaimer
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Terms of Service
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Divider + Bottom Text */}
      <div className="border-t border-[#99BACE]/30 mt-10 pt-6 text-sm text-white">
        <p>© 2025 NyaySaathi. All rights reserved.</p>
        <p className="mt-2 max-w-3xl text-left">
          <span className="font-semibold">Disclaimer:</span> NyaySaathi is not a
          law firm and does not provide legal advice. All information and tools
          are for informational and self-help purposes only.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
