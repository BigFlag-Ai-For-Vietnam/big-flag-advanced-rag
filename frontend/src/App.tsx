import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import UploadPage from "./pages/Upload";
import DocumentsPage from "./pages/Documents";
import PlaygroundPage from "./pages/Playground";

export default function App() {
  return (
    <>
      <nav className="nav">
        <span style={{ fontWeight: 700 }}>RAG Platform</span>
        <NavLink to="/upload">Upload</NavLink>
        <NavLink to="/documents">Documents</NavLink>
        <NavLink to="/playground">Playground</NavLink>
      </nav>
      <div className="container">
        <Routes>
          <Route path="/" element={<Navigate to="/documents" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/playground" element={<PlaygroundPage />} />
        </Routes>
      </div>
    </>
  );
}
