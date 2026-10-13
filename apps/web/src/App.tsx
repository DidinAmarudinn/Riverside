import { NavLink, Route, Routes } from "react-router-dom";
import About from "./routes/About";
import Gaps from "./routes/Gaps";
import Home from "./routes/Home";
import Kiosk from "./routes/Kiosk";
import Manager from "./routes/Manager";
import SkuDetail from "./routes/SkuDetail";

export default function App() {
  return (
    <>
      <header className="nav">
        <NavLink to="/" className="brand">Demand Radar</NavLink>
        <nav>
          <NavLink to="/kiosk">Kiosk</NavLink>
          <NavLink to="/manager">Manager</NavLink>
          <NavLink to="/manager/gaps">Gaps</NavLink>
          <NavLink to="/about">About</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/kiosk" element={<Kiosk />} />
          <Route path="/manager" element={<Manager />} />
          <Route path="/manager/sku/:sku" element={<SkuDetail />} />
          <Route path="/manager/gaps" element={<Gaps />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>
    </>
  );
}
