import { BrowserRouter, Routes, Route } from "react-router-dom";
import "@/App.css";
import Dashboard from "@/pages/Dashboard";
import Settings from "@/pages/Settings";
import Positions from "@/pages/Positions";
import Decisions from "@/pages/Decisions";
import History from "@/pages/History";
import Analyze from "@/pages/Analyze";
import Layout from "@/components/Layout";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="positions" element={<Positions />} />
            <Route path="history" element={<History />} />
            <Route path="decisions" element={<Decisions />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;