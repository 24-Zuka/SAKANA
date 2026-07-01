import { HashRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { Dashboard } from "./screens/Dashboard/Dashboard";
import { Agents } from "./screens/Agents/Agents";
import { Build } from "./screens/Build/Build";
import { Memory } from "./screens/Memory/Memory";
import { Schedule } from "./screens/Schedule/Schedule";
import { Research } from "./screens/Research/Research";
import { QuotaCost } from "./screens/QuotaCost/QuotaCost";
import { Settings } from "./screens/Settings/Settings";

function App() {
  return (
    <HashRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="agents" element={<Agents />} />
          <Route path="build" element={<Build />} />
          <Route path="memory" element={<Memory />} />
          <Route path="schedule" element={<Schedule />} />
          <Route path="research" element={<Research />} />
          <Route path="quota" element={<QuotaCost />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}

export default App;
