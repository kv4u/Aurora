import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Trades from "./pages/Trades";
import Signals from "./pages/Signals";
import Audit from "./pages/Audit";
import Settings from "./pages/Settings";
import Login from "./pages/Login";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="trades" element={<Trades />} />
        <Route path="signals" element={<Signals />} />
        <Route path="audit" element={<Audit />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
