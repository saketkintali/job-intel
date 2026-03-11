import React, { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function UploadPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"upload" | "search">("upload");
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobTitle, setJobTitle] = useState("");
  const [jobLocation, setJobLocation] = useState("Seattle, WA");

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError("Please upload a PDF file.");
        return;
      }
      setError(null);
      setLoading(true);
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await fetch("/api/resume/upload", { method: "POST", body: form });
        if (!res.ok) {
          const msg = await res.text();
          throw new Error(msg || "Upload failed");
        }
        const data = await res.json();
        navigate("/companies", { state: { profileId: data.profileId, roles: data.roles } });
      } catch (e: any) {
        setError(e.message ?? "Something went wrong");
      } finally {
        setLoading(false);
      }
    },
    [navigate]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleJobSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobTitle.trim()) return;
    navigate("/companies", {
      state: { manualRole: jobTitle.trim(), location: jobLocation.trim() || "Seattle, WA", profileId: "manual" },
    });
  };

  return (
    <div className="flex flex-col items-center gap-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-800">Find Your Next Role</h2>
        <p className="mt-1 text-gray-500">Upload your resume for smart matching, or search by job title directly</p>
      </div>

      {/* Tab selector */}
      <div className="flex w-full max-w-lg rounded-xl border border-gray-200 bg-gray-50 p-1 gap-1">
        <button
          onClick={() => { setActiveTab("upload"); setError(null); }}
          className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "upload"
              ? "bg-white text-blue-600 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Upload Resume
        </button>
        <button
          onClick={() => { setActiveTab("search"); setError(null); }}
          className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "search"
              ? "bg-white text-blue-600 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Search by Job Title
        </button>
      </div>

      {activeTab === "upload" && (
        <div className="flex flex-col items-center gap-4 w-full max-w-lg">
          <p className="text-sm text-gray-500 text-center">
            We'll parse your resume and match you with relevant openings automatically.
          </p>
          <label
            className={`flex flex-col items-center justify-center w-full h-56 border-2 border-dashed rounded-xl cursor-pointer transition-colors
              ${dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white hover:border-blue-400 hover:bg-blue-50"}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <input type="file" accept=".pdf" className="hidden" onChange={onInputChange} />
            {loading ? (
              <div className="flex flex-col items-center gap-3">
                <svg className="animate-spin h-8 w-8 text-blue-500" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span className="text-sm text-gray-600">Parsing resume…</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 text-gray-500">
                <svg className="h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M12 16v-8m0 0-3 3m3-3 3 3M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1" />
                </svg>
                <span className="font-medium">Drag & drop your PDF here</span>
                <span className="text-sm">or click to browse</span>
              </div>
            )}
          </label>
        </div>
      )}

      {activeTab === "search" && (
        <div className="flex flex-col gap-4 w-full max-w-lg">
          <p className="text-sm text-gray-500 text-center">
            Enter a job title and location to search openings directly.
          </p>
          <form onSubmit={handleJobSearch} className="flex flex-col gap-3">
            <input
              type="text"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              placeholder="Job title (e.g. Software Engineer)"
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <input
              type="text"
              value={jobLocation}
              onChange={(e) => setJobLocation(e.target.value)}
              placeholder="Location (e.g. Seattle, WA)"
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <button
              type="submit"
              disabled={!jobTitle.trim()}
              className="w-full bg-blue-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Search Jobs
            </button>
          </form>
        </div>
      )}

      {error && (
        <p className="text-red-500 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-2">{error}</p>
      )}
    </div>
  );
}
