import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import PlayerPage from "./pages/PlayerPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/player/:id" element={<PlayerPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
