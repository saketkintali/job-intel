import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

interface Job {
  id: string;
  company: string;
  title: string;
  location: string;
  url: string;
}

type TileId = "interviews" | "salary" | "study" | "rounds";

interface TileState {
  loading: boolean;
  data: any;
  error: string | null;
  fetched: boolean;
}

const INITIAL_TILE: TileState = { loading: false, data: null, error: null, fetched: false };

// ── Icons ──────────────────────────────────────────────────────────────────

function ChatIcon() {
  return (
    <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  );
}

function DollarIcon() {
  return (
    <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  );
}

function CycleIcon() {
  return (
    <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin h-5 w-5 text-blue-500" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  );
}

// ── Expanded content renderers ─────────────────────────────────────────────

function InterviewsContent({ data }: { data: any }) {
  const typeBadge: Record<string, string> = {
    coding: "bg-blue-100 text-blue-700",
    behavioral: "bg-green-100 text-green-700",
    "system design": "bg-purple-100 text-purple-700",
  };
  const diffColor: Record<string, string> = {
    Easy: "text-green-600",
    Medium: "text-yellow-600",
    Hard: "text-red-600",
  };
  return (
    <div className="flex flex-col gap-3">
      {data.map((q: any, i: number) => (
        <div key={i} className="flex flex-col gap-1.5 border-b border-gray-100 pb-3 last:border-0">
          <div className="flex items-start gap-2">
            <span className={`mt-0.5 shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${typeBadge[q.type] ?? "bg-gray-100 text-gray-600"}`}>
              {q.type}
            </span>
            {q.url ? (
              <a href={q.url} target="_blank" rel="noopener noreferrer"
                className="text-sm text-blue-700 font-medium hover:underline leading-snug">
                {q.question}
              </a>
            ) : (
              <p className="text-sm text-gray-800">{q.question}</p>
            )}
          </div>
          <div className="flex items-center gap-2 ml-0.5 flex-wrap">
            {q.difficulty && (
              <span className={`text-xs font-semibold ${diffColor[q.difficulty] ?? "text-gray-500"}`}>
                {q.difficulty}
              </span>
            )}
            {q.source && (
              <span className="text-xs bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">{q.source}</span>
            )}
            {q.tags?.length > 0 && (
              <span className="text-xs text-gray-400">{q.tags.join(" · ")}</span>
            )}
            {q.frequency && (
              <span className="text-xs text-gray-400">· Asked {q.frequency}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function SalaryContent({ data }: { data: any }) {
  const pct = (data.median - data.min) / (data.max - data.min);
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 text-center">
        {[["Min", data.min], ["Median", data.median], ["Max", data.max]].map(([label, val]) => (
          <div key={label as string} className="flex flex-col gap-1">
            <span className="text-xs text-gray-500">{label}</span>
            <span className="text-xl font-bold text-gray-800">
              ${(val as number).toLocaleString()}
            </span>
            <span className="text-xs text-gray-400">{data.currency}</span>
          </div>
        ))}
      </div>
      <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="absolute top-0 left-0 h-full bg-blue-500 rounded-full"
          style={{ width: `${pct * 100}%` }}
        />
      </div>
      {data.note && <p className="text-xs text-gray-500 italic">{data.note}</p>}
    </div>
  );
}

function StudyContent({ data }: { data: any }) {
  const priorityColor: Record<string, string> = {
    high: "border-red-200 bg-red-50",
    medium: "border-yellow-200 bg-yellow-50",
    low: "border-green-200 bg-green-50",
  };
  const priorityLabel: Record<string, string> = {
    high: "text-red-600",
    medium: "text-yellow-700",
    low: "text-green-700",
  };
  return (
    <div className="flex flex-col gap-4">
      {data.plan.map((item: any, i: number) => (
        <div key={i} className={`rounded-lg border px-4 py-3 ${priorityColor[item.priority] ?? "border-gray-200 bg-white"}`}>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              {item.round > 0 && (
                <span className="text-xs font-bold text-blue-600 bg-blue-100 rounded-full w-5 h-5 flex items-center justify-center shrink-0">
                  {item.round}
                </span>
              )}
              <span className="font-semibold text-sm text-gray-800">{item.skill}</span>
            </div>
            <span className={`text-xs font-medium uppercase tracking-wide ${priorityLabel[item.priority] ?? "text-gray-500"}`}>
              {item.priority}
            </span>
          </div>
          {item.roundType && (
            <p className="text-xs text-gray-500 mb-2 ml-7">Prep for: <span className="font-medium">{item.roundType}</span></p>
          )}
          {item.tips && (
            <p className="text-xs text-gray-600 italic mb-2 ml-7">{item.tips}</p>
          )}
          <ul className="flex flex-col gap-1 ml-7">
            {(item.resources || []).map((r: any, j: number) => (
              <li key={j}>
                <a href={r.url} target="_blank" rel="noopener noreferrer"
                  className="text-xs text-blue-600 underline hover:opacity-80">
                  {r.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function RoundsContent({ data }: { data: any }) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-gray-600">
        Total rounds: <span className="font-semibold text-gray-800">{data.totalRounds}</span>
      </p>
      {data.rounds.map((r: any) => (
        <div key={r.number} className="bg-gray-50 rounded-lg px-4 py-3 flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-blue-600 bg-blue-50 rounded-full w-6 h-6 flex items-center justify-center shrink-0">
              {r.number}
            </span>
            <span className="font-semibold text-sm text-gray-800">{r.type}</span>
            {r.duration && <span className="text-xs text-gray-400 ml-auto">{r.duration}</span>}
          </div>
          {r.tips && <p className="text-xs text-gray-500 ml-8">{r.tips}</p>}
        </div>
      ))}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as { job?: Job; profileId?: string } | null;
  const job = state?.job;
  const profileId = state?.profileId ?? "";

  const [expanded, setExpanded] = useState<TileId | null>(null);
  const [tiles, setTiles] = useState<Record<TileId, TileState>>({
    interviews: { ...INITIAL_TILE },
    salary: { ...INITIAL_TILE },
    study: { ...INITIAL_TILE },
    rounds: { ...INITIAL_TILE },
  });

  if (!job) {
    navigate("/companies");
    return null;
  }

  async function fetchTile(id: TileId) {
    if (tiles[id].fetched) return;

    setTiles((prev) => ({ ...prev, [id]: { ...prev[id], loading: true, error: null } }));

    const params = new URLSearchParams({ company: job!.company, role: job!.title });
    if (id === "study") params.set("profileId", profileId);

    const urlMap: Record<TileId, string> = {
      interviews: `/api/interviews?${params}`,
      salary: `/api/salary?${params}`,
      study: `/api/study?${params}`,
      rounds: `/api/rounds?${params}`,
    };

    try {
      const res = await fetch(urlMap[id]);
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const data = await res.json();
      setTiles((prev) => ({ ...prev, [id]: { loading: false, data, error: null, fetched: true } }));
    } catch (e: any) {
      setTiles((prev) => ({
        ...prev,
        [id]: { loading: false, data: null, error: e.message ?? "Error", fetched: false },
      }));
    }
  }

  function handleTileClick(id: TileId) {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    fetchTile(id);
  }

  function tileSubtitle(id: TileId): string {
    const t = tiles[id];
    if (!t.fetched && !t.loading) return "Click to load";
    if (t.loading) return "Loading…";
    if (t.error) return "Error";
    if (id === "interviews") return `${t.data?.length ?? 0} questions`;
    if (id === "salary") return `$${t.data?.min?.toLocaleString()} – $${t.data?.max?.toLocaleString()}`;
    if (id === "study") return `${t.data?.plan?.length ?? 0} rounds to prep for`;
    if (id === "rounds") return `${t.data?.totalRounds ?? 0} rounds`;
    return "";
  }

  const TILES: { id: TileId; label: string; icon: React.ReactNode }[] = [
    { id: "interviews", label: "Interview Questions", icon: <ChatIcon /> },
    { id: "salary", label: "Salary Insights", icon: <DollarIcon /> },
    { id: "study", label: "Study Plan", icon: <BookIcon /> },
    { id: "rounds", label: "Interview Rounds", icon: <CycleIcon /> },
  ];

  function renderExpanded(id: TileId) {
    const t = tiles[id];
    if (t.loading) return <div className="flex justify-center py-6"><Spinner /></div>;
    if (t.error) return <p className="text-red-500 text-sm py-4">{t.error}</p>;
    if (!t.data) return null;
    if (id === "interviews") return <InterviewsContent data={t.data} />;
    if (id === "salary") return <SalaryContent data={t.data} />;
    if (id === "study") return <StudyContent data={t.data} />;
    if (id === "rounds") return <RoundsContent data={t.data} />;
    return null;
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Sticky header */}
      <div className="sticky top-0 z-10 bg-gray-50 py-3 -mx-6 px-6 border-b border-gray-200 flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wide text-blue-600">{job.company}</span>
          <h2 className="text-xl font-bold text-gray-900 leading-tight">{job.title}</h2>
          {job.location && <p className="text-sm text-gray-500">{job.location}</p>}
        </div>
        <div className="flex items-center gap-3">
          {job.url && job.url !== "#" && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap"
            >
              Apply Now →
            </a>
          )}
          <button
            onClick={() => navigate(-1)}
            className="text-sm text-blue-600 hover:underline whitespace-nowrap"
          >
            ← Back
          </button>
        </div>
      </div>

      {/* 2×2 tile grid + inline expansion */}
      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-4">
          {TILES.map(({ id, label, icon }) => {
            const isExpanded = expanded === id;
            const isLoading = tiles[id].loading;
            return (
              <button
                key={id}
                onClick={() => handleTileClick(id)}
                className={`text-left rounded-xl border p-5 flex flex-col gap-3 transition-all
                  ${isExpanded
                    ? "bg-blue-50 border-blue-400 shadow-md"
                    : "bg-white border-gray-200 hover:shadow-md hover:border-blue-300"
                  }`}
              >
                <div className={`${isExpanded ? "text-blue-600" : "text-gray-500"}`}>{icon}</div>
                <div className="flex flex-col gap-0.5">
                  <span className="font-semibold text-sm text-gray-800">{label}</span>
                  <span className="text-xs text-gray-400 flex items-center gap-1">
                    {isLoading && <Spinner />}
                    {tileSubtitle(id)}
                  </span>
                </div>
                <span className={`text-xs font-medium ${isExpanded ? "text-blue-600" : "text-gray-400"}`}>
                  {isExpanded ? "▲ Collapse" : "▼ Expand"}
                </span>
              </button>
            );
          })}
        </div>

        {/* Inline expanded panel */}
        {expanded && (
          <div className="bg-white rounded-xl border border-blue-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-800">
                {TILES.find((t) => t.id === expanded)?.label}
              </h3>
              <button
                onClick={() => setExpanded(null)}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                ✕ Close
              </button>
            </div>
            {renderExpanded(expanded)}
          </div>
        )}
      </div>
    </div>
  );
}
