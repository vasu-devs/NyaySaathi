import Footer from "./components/Footer/Footer";
import Hero from "./components/Main/Hero";
import Nav from "./components/Navbar/Nav";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Chatbot from "./components/ChatInterface/Chatbot";
function App() {
  return (
    <Router>
      <div className="min-h-screen flex flex-col">
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<Hero />} />
            <Route path="/chatbot" element={<Chatbot />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
