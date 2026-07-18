import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import UploadPage from "./pages/Upload";
import DocumentsPage from "./pages/Documents";
import PlaygroundPage from "./pages/Playground";
import ShowcasePage from "./pages/Showcase";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/documents" replace />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/playground" element={<PlaygroundPage />} />
        <Route path="/showcase" element={<ShowcasePage />} />
        <Route path="*" element={<Navigate to="/documents" replace />} />
      </Routes>
    </AppShell>
  );
}
