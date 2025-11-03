import React, { useState, useEffect, useRef } from "react";
import Nav from "../Navbar/Nav";
import SideBar from "../Sidebar/SideBar";
import { login, listDocuments, setToken, uploadDocumentWithProgress, pingHealth, approveDocument, deleteDocument as apiDeleteDocument } from "../../lib/api";

export default function Admin() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [docs, setDocs] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const inputRef = useRef(null);
  const [apiOk, setApiOk] = useState(null); // null=unknown, true/false

  const [authed, setAuthed] = useState(false);

  // Force login once, on initial mount only
  useEffect(() => {
    setToken(null);
    setAuthed(false);
    // quick health ping
    pingHealth().then(()=>setApiOk(true)).catch(()=>setApiOk(false));
  }, []);

  // After login, load documents
  useEffect(() => {
    if (authed) refreshDocs();
  }, [authed]);

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await login(email, password);
      setToken(res.access_token);
      setAuthed(true);
    } catch {
      setError("Login failed. Check credentials.");
    }
  }

  async function refreshDocs() {
    try {
      const res = await listDocuments();
      setDocs(res.items || []);
    } catch (e) {
      console.error(e);
    }
  }

  async function handleApprove(docId) {
    try {
      await approveDocument(docId);
      await refreshDocs();
    } catch (e) {
      console.error(e);
      alert("Failed to approve document");
    }
  }

  async function handleDelete(docId) {
    if (!confirm("Delete embeddings and remove this document from the index?")) return;
    try {
      await apiDeleteDocument(docId);
      await refreshDocs();
    } catch (e) {
      console.error(e);
      alert("Failed to delete document");
    }
  }

  async function doUpload(f) {
    if (!f) return;
    setUploadError("");
    if (f.size > 50 * 1024 * 1024) {
      setUploadError("File too large (max 50 MB)");
      return;
    }
    setIsUploading(true);
    setProgress(0);
    try {
      await uploadDocumentWithProgress(f, title || f.name, (pct)=> setProgress(pct));
      setTitle("");
      await refreshDocs();
    } catch (e) {
      console.error(e);
      setUploadError(e?.message || "Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <Nav />
      <SideBar initialCollapsed />
      <main className="pt-16 pl-16 sm:pl-20 lg:pl-0">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
          <div className="text-xs text-[#99BACE] mt-4">Home &gt; Admin</div>

          <h1 className="text-3xl sm:text-4xl font-semibold text-[#0A2B42] text-center mt-8">Global Corpus Admin</h1>
          <p className="text-[#2C6BA1] text-center mt-3 max-w-2xl mx-auto">
            Ingest documents into the global knowledge base used by the Chatbot. PDFs, DOCX, TXT and Markdown are supported.
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-10">
              {/* Upload Card with drag & drop */}
              <div className="rounded-2xl border border-[#E6EEF6] bg-[#EFF6FB]/60 p-8 shadow-sm">
                <div className="text-[#0A2B42] font-semibold text-lg mb-4">Upload &amp; Ingest</div>
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs text-[#99BACE] mb-1">Title (optional)</label>
                    <input value={title} onChange={e=>setTitle(e.target.value)} type="text" className="w-full border border-[#E6EEF6] rounded px-3 py-2" placeholder="Document title" />
                  </div>
                  <div
                    onDragOver={(e)=>{e.preventDefault(); setIsDragOver(true);}}
                    onDragLeave={()=>setIsDragOver(false)}
                    onDrop={(e)=>{e.preventDefault(); setIsDragOver(false); const f = e.dataTransfer.files?.[0]; if (f) doUpload(f);} }
                    className={`w-full rounded-2xl border ${isDragOver? 'border-[#2C6BA1]':'border-[#E6EEF6]'} bg-white p-10 sm:p-14 flex flex-col items-center text-center`}
                  >
                    <img src="/doc.svg" alt="doc" className="w-14 h-14 opacity-80" onError={(e)=>{e.currentTarget.style.display='none';}} />
                    <div className="mt-4 text-[#0A2B42] font-semibold">Drag &amp; drop your file here</div>
                    <div className="text-xs text-[#99BACE] mt-1">PDF, DOCX, TXT, or Markdown (max 50 MB)</div>
                    <div className="mt-6">
                      <button
                        type="button"
                        onClick={()=>!isUploading && inputRef.current?.click()}
                        className={`bg-white border border-[#2C6BA1] text-[#2C6BA1] hover:bg-[#F1F7FB] font-medium rounded px-5 py-2 ${isUploading? 'opacity-60 cursor-not-allowed':''}`}
                      >
                        {isUploading ? 'Uploading...' : 'Browse File'}
                      </button>
                      <input
                        ref={inputRef}
                        type="file"
                        accept=".pdf,.docx,.txt,.md"
                        className="hidden"
                        onChange={(e)=>{ const f=e.target.files?.[0]; if (f) doUpload(f);} }
                      />
                    </div>
                    {isUploading && (
                      <div className="mt-6 w-full max-w-md text-left">
                        <div className="text-xs text-[#99BACE] mb-1">
                          {progress < 100 ? (
                            <>Uploading: {progress}%</>
                          ) : (
                            <span className="animate-pulse">Processing document on server…</span>
                          )}
                        </div>
                        <div className="w-full h-2 bg-[#F7FBFF] rounded-full overflow-hidden border border-[#E6EEF6]">
                          <div className="h-full bg-[#2C6BA1] transition-all duration-200" style={{ width: `${progress}%` }} />
                        </div>
                      </div>
                    )}
                    {uploadError && <div className="mt-4 text-sm text-red-600">{uploadError}</div>}
                  </div>
                </div>
              </div>

              {/* Documents Card */}
              <div className="rounded-2xl border border-[#E6EEF6] bg-white p-8 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div className="text-[#0A2B42] font-semibold text-lg">Documents</div>
                  <div className="text-xs">
                    {apiOk===true && <span className="text-green-600">API: healthy</span>}
                    {apiOk===false && <span className="text-red-600">API: unreachable</span>}
                  </div>
                </div>
                <ul className="space-y-2">
                  {docs.map((d)=> (
                    <li key={d.doc_id} className="border border-[#EEF6FB] bg-[#F9FCFF] rounded px-3 py-2 text-sm flex items-center justify-between gap-3">
                      <div>
                        <div className="font-medium text-[#0A2B42]">{d.title || d.path || d.doc_id}</div>
                        <div className="text-[#99BACE]">doc_id: {d.doc_id} • chunks: {d.chunks} {typeof d.approved !== 'undefined' && (d.approved ? '• approved' : '• not approved')}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          title={d.approved ? "Approved" : "Approve"}
                          onClick={()=>handleApprove(d.doc_id)}
                          className={`w-8 h-8 rounded-full border flex items-center justify-center ${d.approved ? 'bg-green-500 text-white border-green-600' : 'bg-white text-[#2C6BA1] border-[#2C6BA1] hover:bg-[#F1F7FB]'}`}
                        >
                          ✓
                        </button>
                        <button
                          title="Delete embeddings"
                          onClick={()=>handleDelete(d.doc_id)}
                          className="w-8 h-8 rounded-full border border-red-300 text-red-600 bg-white hover:bg-red-50 flex items-center justify-center"
                        >
                          🗑
                        </button>
                      </div>
                    </li>
                  ))}
                  {docs.length===0 && <div className="text-sm text-[#99BACE]">No documents yet.</div>}
                </ul>
              </div>
          </div>

          {/* Login Modal Overlay */}
          {!authed && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
              <div className="w-full max-w-md rounded-2xl border border-[#E6EEF6] bg-white p-8 shadow-xl" role="dialog" aria-modal="true">
                <div className="text-lg font-semibold text-[#0A2B42] mb-4 text-center">Admin Sign In</div>
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <label className="block text-sm text-[#99BACE] mb-1">Email</label>
                    <input autoFocus value={email} onChange={e=>setEmail(e.target.value)} type="email" className="w-full border border-[#E6EEF6] rounded px-3 py-2" placeholder="admin@example.com" />
                  </div>
                  <div>
                    <label className="block text-sm text-[#99BACE] mb-1">Password</label>
                    <input value={password} onChange={e=>setPassword(e.target.value)} type="password" className="w-full border border-[#E6EEF6] rounded px-3 py-2" placeholder="admin123" />
                  </div>
                  {error && <div className="text-red-600 text-sm">{error}</div>}
                  <button type="submit" className="w-full bg-[#0A2B42] text-white px-4 py-2 rounded">Login</button>
                  <p className="text-xs text-[#99BACE] mt-2 text-center">Defaults (dev): admin@example.com / admin123 — change in .env</p>
                </form>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
