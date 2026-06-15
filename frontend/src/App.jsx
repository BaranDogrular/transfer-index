import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import PlayerPage from "./pages/PlayerPage";
import Scouting from "./pages/Scouting";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/player/:id" element={<PlayerPage />} />
        <Route path="/scouting" element={<Scouting />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
