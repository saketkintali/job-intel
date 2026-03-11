import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

interface Job {
  id: string;
  company: string;
  title: string;
  location: string;
  url: string;
}

export default function CompaniesPage() {
  const routeLocation = useLocation();
  const navigate = useNavigate();
  const state = routeLocation.state as { profileId?: string; roles?: string[]; manualRole?: string; location?: string } | null;

  const isManual = state?.profileId === "manual";
  const initialRole = state?.manualRole ?? (state?.roles ?? [])[0] ?? "software engineer";
  const initialLocation = state?.location ?? "Seattle, WA";

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [role, setRole] = useState(initialRole);
  const [location, setLocation] = useState(initialLocation);
  const [salaryMin, setSalaryMin] = useState<string>("");

  useEffect(() => {
    if (!state?.profileId) {
      navigate("/");
      return;
    }
    fetchJobs(state.profileId, initialRole, initialLocation, "");
  }, []);

  async function fetchJobs(profileId: string, searchRole: string, searchLocation: string, minSalary: string) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ profileId, role: searchRole, location: searchLocation });
      if (minSalary) params.set("salary_min", minSalary);
      const res = await fetch(`/api/companies?${params}`);
      if (!res.ok) throw new Error("Failed to fetch jobs");
      const data = await res.json();
      setJobs(data);
    } catch (e: any) {
      setError(e.message ?? "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (state?.profileId) fetchJobs(state.profileId, role, location, salaryMin);
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Job Matches</h2>
          <p className="text-gray-500 text-sm mt-0.5">{isManual ? "Based on your search" : "Based on your resume"}</p>
        </div>
        <button
          onClick={() => navigate("/")}
          className="text-sm text-blue-600 hover:underline"
        >
          ← {isManual ? "New search" : "Upload another resume"}
        </button>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 flex-wrap">
        <input
          type="text"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          placeholder="Role (e.g. Software Engineer)"
          className="flex-1 min-w-[160px] border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Location (e.g. Seattle, WA)"
          className="flex-1 min-w-[140px] border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <select
          value={salaryMin}
          onChange={(e) => setSalaryMin(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
        >
          <option value="">Any salary</option>
          <option value="80000">$80k+</option>
          <option value="100000">$100k+</option>
          <option value="120000">$120k+</option>
          <option value="150000">$150k+</option>
          <option value="180000">$180k+</option>
          <option value="200000">$200k+</option>
        </select>
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Search
        </button>
      </form>

      {loading && (
        <div className="flex justify-center py-16">
          <svg className="animate-spin h-8 w-8 text-blue-500" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        </div>
      )}

      {error && (
        <p className="text-red-500 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-2">{error}</p>
      )}

      {!loading && !error && jobs.length === 0 && (
        <p className="text-center text-gray-500 py-16">No jobs found. Try a different role.</p>
      )}

      {!loading && jobs.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <div key={job.id} className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-3 hover:shadow-md transition-shadow">
              <div className="flex flex-col gap-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-blue-600">{job.company}</span>
                <h3 className="font-semibold text-gray-800 leading-snug">{job.title}</h3>
                <span className="text-sm text-gray-500 flex items-center gap-1">
                  <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M17.657 16.657L13.414 20.9a2 2 0 01-2.828 0l-4.243-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  {job.location || "Remote / Unknown"}
                </span>
              </div>
              <div className="mt-auto flex gap-2">
                <button
                  onClick={() => navigate("/dashboard", { state: { job, profileId: state?.profileId } })}
                  className="flex-1 text-center bg-blue-600 text-white text-sm font-medium rounded-lg px-4 py-2 hover:bg-blue-700 transition-colors"
                >
                  View Details
                </button>
                {job.url && job.url !== "#" && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 text-center border border-blue-600 text-blue-600 text-sm font-medium rounded-lg px-4 py-2 hover:bg-blue-50 transition-colors"
                  >
                    Apply →
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
