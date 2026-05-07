import { useState, useEffect, useRef } from "react";
import { getAllSkills, getRecommendations, exportUserData, resetUserData } from "./api/api";

// --- UUID helper — generates once, persists in localStorage ---
function getOrCreateUserId() {
  let userId = localStorage.getItem("skill_recommender_user_id");
  if (!userId) {
    userId = crypto.randomUUID();
    localStorage.setItem("skill_recommender_user_id", userId);
  }
  return userId;
}

// --- Level badge color ---
const LEVEL_COLORS = {
  Beginner:  "bg-green-100 text-green-800",
  "Mid-Level": "bg-blue-100 text-blue-800",
  Senior:    "bg-purple-100 text-purple-800",
  Architect: "bg-orange-100 text-orange-800",
};

export default function App() {
  const [tags, setTags] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [allSkills, setAllSkills] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const wrapperRef = useRef(null);

  // Stable user identity
  const userId = getOrCreateUserId();

  // Fetch all skills on mount
  useEffect(() => {
    getAllSkills().then(setAllSkills);
  }, []);

  // Filter dropdown
  useEffect(() => {
    if (inputValue.trim() === "") {
      setFiltered([]);
      setShowDropdown(false);
      return;
    }
    const query = inputValue.toLowerCase();
    const matches = allSkills.filter(
      (skill) => skill.toLowerCase().includes(query) && !tags.includes(skill)
    );
    setFiltered(matches);
    setShowDropdown(matches.length > 0);
  }, [inputValue, allSkills, tags]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const addTag = (skill) => {
    if (!tags.includes(skill)) setTags([...tags, skill]);
    setInputValue("");
    setShowDropdown(false);
  };

  const removeTag = (skill) => setTags(tags.filter((t) => t !== skill));

  const handleRecommend = async () => {
    if (tags.length === 0) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await getRecommendations(tags, userId);
      if (res.error) {
        setError(res.error);
      } else {
        setResult(res);
      }
    } catch {
      setError("Something went wrong. Please try again.");
    }
    setLoading(false);
  };

  const handleExport = async () => {
    try {
      const data = await exportUserData(userId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "skill_history.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Export failed. Please try again.");
    }
  };

  const handleReset = async () => {
    try {
      await resetUserData(userId);
      localStorage.removeItem("skill_recommender_user_id");
      setResult(null);
      setTags([]);
      setShowResetConfirm(false);
      window.location.reload(); // generates fresh UUID on next render
    } catch {
      setError("Reset failed. Please try again.");
    }
  };

  const userLevel = result?.user_level;
  const specialization = result?.specialization;
  const leafNodes = result?.leaf_nodes ?? [];

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 py-10">

      {/* Card */}
      <div className="w-full max-w-xl bg-white shadow-xl rounded-2xl p-8">

        {/* Header */}
        <h1 className="text-3xl font-bold text-center mb-2 text-gray-900 tracking-tight">
          Career Graph Builder
        </h1>
        <p className="text-center mb-8 text-gray-500 text-sm max-w-md mx-auto leading-relaxed">
          Tell us the skills you already know. Our knowledge graph will analyze your level and recommend the exact skills you need to learn next to advance your career.
        </p>

        {/* Career Level Badge — shown after first recommendation */}
        {userLevel && (
          <div className="flex items-center justify-between mb-6 p-3 bg-gray-50 rounded-xl border border-gray-200">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold px-3 py-1 rounded-full ${LEVEL_COLORS[userLevel.label] ?? "bg-gray-100 text-gray-700"}`}>
                {userLevel.label}
              </span>
              <span className="text-xs text-gray-500">Score: {userLevel.score}</span>
            </div>
            {specialization && (
              <span className="text-xs text-gray-500">
                Specialization: <span className="font-medium text-gray-700">{specialization}</span>
              </span>
            )}
          </div>
        )}

        {/* Skill Input */}
        <div ref={wrapperRef} className="relative">
          <div className="flex flex-wrap gap-2 border border-gray-300 rounded-xl px-4 py-3 bg-gray-50 focus-within:ring-2 focus-within:ring-black transition">
            {tags.map((tag) => (
              <span
                key={tag}
                className="flex items-center gap-1 bg-black text-white text-sm px-3 py-1 rounded-full"
              >
                {tag}
                <button onClick={() => removeTag(tag)} className="ml-1 hover:text-red-300">
                  ×
                </button>
              </span>
            ))}
            <input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && inputValue.trim() !== "") {
                  addTag(inputValue.trim());
                }
              }}
              placeholder="Type your skills here.."
              className="flex-1 outline-none text-sm bg-transparent min-w-[120px] placeholder-gray-400"
            />
          </div>

          {/* Dropdown */}
          {showDropdown && (
            <ul className="absolute z-50 w-full bg-white border border-gray-200 rounded-xl mt-2 shadow-lg max-h-52 overflow-y-auto">
              {filtered.map((skill) => (
                <li
                  key={skill}
                  onMouseDown={() => addTag(skill)}
                  className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer transition"
                >
                  {skill}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Recommend Button */}
        <button
          onClick={handleRecommend}
          disabled={loading || tags.length === 0}
          className={`mt-4 w-full py-2 rounded-xl transition text-sm font-medium ${
            loading || tags.length === 0
              ? "bg-gray-300 cursor-not-allowed text-gray-500"
              : "bg-black text-white hover:bg-gray-800"
          }`}
        >
          {loading ? "Loading..." : "Get Recommendations"}
        </button>

        {/* Spinner */}
        {loading && (
          <div className="flex justify-center mt-6">
            <div className="w-8 h-8 border-4 border-gray-200 border-t-black rounded-full animate-spin"></div>
          </div>
        )}

        {/* Empty State Instructions */}
        {!result && tags.length === 0 && !loading && (
          <div className="mt-8 p-6 bg-gray-50 border border-gray-100 rounded-xl text-center">
            <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm border border-gray-100">
              <span className="text-xl">🚀</span>
            </div>
            <h3 className="text-sm font-medium text-gray-800 mb-1">Ready to level up?</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Add your current skills above (e.g., "Python", "React", "Docker") and click "Get Recommendations" to start building your career path.
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <p className="mt-3 text-red-500 text-sm text-center">{error}</p>
        )}

        {/* Leaf node expansion notice */}
        {leafNodes.length > 0 && (
          <p className="mt-3 text-xs text-gray-400 text-center">
            ✦ Graph dynamically expanded for: {leafNodes.join(", ")}
          </p>
        )}

        {/* Results */}
        {result && Object.keys(result.recommendations).length > 0 && (
          <div className="mt-6">
            {Object.entries(result.recommendations).map(([track, skills]) => (
              <div key={track} className="mb-4">
                <h2 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">
                  {track}
                </h2>
                <ul className="mt-2 space-y-2">
                  {skills.map((s, i) => (
                    <li key={i} className="p-3 bg-gray-50 rounded-xl text-sm border border-gray-100">
                      <div className="flex items-center justify-between">
                        <strong className="text-gray-800">{s.skill}</strong>
                        {s.difficulty && (
                          <span className="text-xs text-gray-400">
                            Level {s.difficulty}/5
                          </span>
                        )}
                      </div>
                      <p className="text-gray-500 mt-1">{s.reason}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        {/* Empty recommendations */}
        {result && Object.keys(result.recommendations).length === 0 && (
          <p className="mt-6 text-center text-gray-400 text-sm">
            No new recommendations found for your current level.
          </p>
        )}

        {/* Export & Reset — shown after at least one recommendation */}
        {result && (
          <div className="mt-6 flex gap-3">
            <button
              onClick={handleExport}
              className="flex-1 py-2 text-sm rounded-xl border border-gray-300 text-gray-600 hover:bg-gray-50 transition"
            >
              Export History
            </button>
            <button
              onClick={() => setShowResetConfirm(true)}
              className="flex-1 py-2 text-sm rounded-xl border border-red-200 text-red-500 hover:bg-red-50 transition"
            >
              Reset Data
            </button>
          </div>
        )}

        {/* Reset Confirmation Modal */}
        {showResetConfirm && (
          <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
              <h3 className="font-semibold text-gray-800 mb-2">Reset all data?</h3>
              <p className="text-sm text-gray-500 mb-4">
                Your skill history and career level will be permanently deleted. The skill graph is unaffected.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowResetConfirm(false)}
                  className="flex-1 py-2 rounded-xl border border-gray-200 text-sm text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleReset}
                  className="flex-1 py-2 rounded-xl bg-red-500 text-white text-sm hover:bg-red-600"
                >
                  Yes, Reset
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
