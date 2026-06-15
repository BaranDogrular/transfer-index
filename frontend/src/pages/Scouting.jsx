import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function Scouting() {
  const [players, setPlayers] = useState([]);

  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  const [positionFilter, setPositionFilter] = useState("");
  const [maxAge, setMaxAge] = useState("");
  const [maxValue, setMaxValue] = useState("");

  const [page, setPage] = useState(1);
  const [totalPlayers, setTotalPlayers] = useState(0);
  const [loading, setLoading] = useState(false);

  const limit = 50;
  const totalPages = Math.ceil(totalPlayers / limit);

  const loadPlayers = async () => {
    try {
      setLoading(true);

      const params = new URLSearchParams();

      params.append("page", page);
      params.append("limit", limit);

      if (debouncedQuery) {
        params.append("q", debouncedQuery);
      }

      if (positionFilter) {
        params.append("position", positionFilter);
      }

      if (maxAge) {
        params.append("max_age", maxAge);
      }

      if (maxValue) {
        params.append("max_value", maxValue);
      }

      const response = await fetch(
        `http://127.0.0.1:8000/players/search?${params}`,
      );

      const data = await response.json();

      setPlayers(data.players || []);
      setTotalPlayers(data.total || 0);
    } catch (error) {
      console.error("SCOUTING LOAD ERROR:", error);
    } finally {
      setLoading(false);
    }
  };

  const resetFilters = () => {
    setSearchQuery("");
    setDebouncedQuery("");
    setPositionFilter("");
    setMaxAge("");
    setMaxValue("");
    setPage(1);
  };

  const getPlayerScore = (player) => {
    let score = 35;

    score += Math.min(
      ((player.goals + player.assists) / Math.max(player.matches, 1)) * 18,
      18,
    );

    if (player.age >= 22 && player.age <= 28) {
      score += 20;
    } else if (player.age <= 31) {
      score += 10;
    }

    if (player.market_value_m <= 25) {
      score += 15;
    }

    if (player.injury_days < 30) {
      score += 10;
    }

    return Math.min(Math.round(score), 92);
  };

  const getRecommendation = (score) => {
    if (score >= 85) {
      return {
        label: "ELITE TARGET",
        color: "text-green-400",
        bg: "bg-green-500/20",
      };
    }

    if (score >= 70) {
      return {
        label: "STRONG OPTION",
        color: "text-cyan-400",
        bg: "bg-cyan-500/20",
      };
    }

    if (score >= 55) {
      return {
        label: "MONITOR",
        color: "text-yellow-400",
        bg: "bg-yellow-500/20",
      };
    }

    return {
      label: "HIGH RISK",
      color: "text-red-400",
      bg: "bg-red-500/20",
    };
  };

  useEffect(() => {
    const timeout = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1);
    }, 300);

    return () => clearTimeout(timeout);
  }, [searchQuery]);

  useEffect(() => {
    setPage(1);
  }, [positionFilter, maxAge, maxValue]);

  useEffect(() => {
    loadPlayers();
  }, [debouncedQuery, positionFilter, maxAge, maxValue, page]);

  return (
    <div className="min-h-screen bg-black text-white px-6 py-10">
      <div className="max-w-7xl mx-auto">
        {/* HEADER */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6 mb-10">
          <div>
            <h1 className="text-5xl font-black">Scouting Database</h1>

            <p className="text-zinc-400 mt-3">
              AI-powered recruitment intelligence workspace
            </p>
          </div>

          <Link to="/" className="text-cyan-400 hover:text-cyan-300">
            ← Back Home
          </Link>
        </div>

        {/* FILTERS */}
        <div className="bg-white/5 border border-white/10 rounded-3xl p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <input
              type="text"
              placeholder="Search player..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="
                md:col-span-2
                bg-black/40
                border
                border-white/10
                rounded-2xl
                px-4
                py-3
                text-white
                placeholder:text-zinc-500
                outline-none
                focus:border-cyan-400
              "
            />

            <select
              value={positionFilter}
              onChange={(e) => setPositionFilter(e.target.value)}
              className="
                bg-black/40
                border
                border-white/10
                rounded-2xl
                px-4
                py-3
                text-white
                outline-none
                focus:border-cyan-400
              "
            >
              <option value="">All Positions</option>
              <option value="Goalkeeper">Goalkeeper</option>
              <option value="Defender">Defender</option>
              <option value="Midfield">Midfield</option>
              <option value="Attack">Attack</option>
              <option value="Centre-Forward">Centre-Forward</option>
              <option value="Left Winger">Left Winger</option>
              <option value="Right Winger">Right Winger</option>
              <option value="Attacking Midfield">Attacking Midfield</option>
              <option value="Defensive Midfield">Defensive Midfield</option>
              <option value="Centre-Back">Centre-Back</option>
              <option value="Left-Back">Left-Back</option>
              <option value="Right-Back">Right-Back</option>
            </select>

            <button
              onClick={resetFilters}
              className="
                px-5
                py-3
                rounded-2xl
                bg-white/10
                hover:bg-white/20
                transition
              "
            >
              Reset
            </button>

            <input
              type="number"
              placeholder="Max Age"
              value={maxAge}
              onChange={(e) => setMaxAge(e.target.value)}
              className="
                bg-black/40
                border
                border-white/10
                rounded-2xl
                px-4
                py-3
                text-white
                placeholder:text-zinc-500
                outline-none
                focus:border-cyan-400
              "
            />

            <input
              type="number"
              placeholder="Max Value (€M)"
              value={maxValue}
              onChange={(e) => setMaxValue(e.target.value)}
              className="
                bg-black/40
                border
                border-white/10
                rounded-2xl
                px-4
                py-3
                text-white
                placeholder:text-zinc-500
                outline-none
                focus:border-cyan-400
              "
            />
          </div>

          <div className="mt-5 text-sm text-zinc-400">
            {loading
              ? "Loading players..."
              : `${totalPlayers.toLocaleString()} players found`}
          </div>
        </div>

        {/* TABLE */}
        <div className="overflow-x-auto rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl">
          <table className="w-full">
            <thead className="border-b border-white/10 bg-black/20">
              <tr className="text-left text-zinc-300">
                <th className="px-6 py-5">Player</th>
                <th className="px-6 py-5">Position</th>
                <th className="px-6 py-5">Age</th>
                <th className="px-6 py-5">Club</th>
                <th className="px-6 py-5">Value</th>
                <th className="px-6 py-5">Score</th>
                <th className="px-6 py-5">Status</th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td
                    colSpan="7"
                    className="px-6 py-10 text-center text-zinc-400"
                  >
                    Loading scouting database...
                  </td>
                </tr>
              ) : players.length > 0 ? (
                players.map((player) => {
                  const score = getPlayerScore(player);
                  const recommendation = getRecommendation(score);

                  return (
                    <tr
                      key={player.id}
                      className="border-b border-white/5 hover:bg-white/5 transition-colors"
                    >
                      <td className="px-6 py-5">
                        <Link
                          to={`/player/${player.id}`}
                          className="flex items-center gap-4"
                        >
                          <img
                            src={
                              player.image_url &&
                              player.image_url !== "https://..."
                                ? player.image_url
                                : "https://placehold.co/100x100?text=Player"
                            }
                            alt={player.name}
                            className="w-12 h-12 rounded-xl object-cover bg-zinc-900"
                          />

                          <div>
                            <div className="font-bold text-white">
                              {player.name}
                            </div>

                            <div className="text-sm text-zinc-400">
                              {player.nationality}
                            </div>
                          </div>
                        </Link>
                      </td>

                      <td className="px-6 py-5 text-zinc-300">
                        {player.position}
                      </td>

                      <td className="px-6 py-5 text-zinc-300">
                        {player.age || "-"}
                      </td>

                      <td className="px-6 py-5 text-zinc-300">{player.club}</td>

                      <td className="px-6 py-5 text-zinc-300">
                        €{Number(player.market_value_m || 0).toFixed(2)}M
                      </td>

                      <td className="px-6 py-5">
                        <div className="text-2xl font-black text-cyan-300">
                          {score}
                        </div>
                      </td>

                      <td className="px-6 py-5">
                        <div
                          className={`
                            inline-flex
                            items-center
                            px-3
                            py-1
                            rounded-full
                            text-xs
                            font-bold
                            ${recommendation.bg}
                            ${recommendation.color}
                          `}
                        >
                          {recommendation.label}
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td
                    colSpan="7"
                    className="px-6 py-10 text-center text-zinc-400"
                  >
                    No players found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {/* PAGINATION */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 px-6 py-5 border-t border-white/10">
            <div className="text-zinc-400 text-sm">
              Page {page} of {totalPages || 1} • {totalPlayers.toLocaleString()}{" "}
              players
            </div>

            <div className="flex gap-3">
              <button
                disabled={page <= 1 || loading}
                onClick={() => setPage((prev) => Math.max(prev - 1, 1))}
                className="
                  px-4
                  py-2
                  rounded-xl
                  bg-white/10
                  hover:bg-white/20
                  disabled:opacity-40
                  disabled:cursor-not-allowed
                  transition
                "
              >
                Previous
              </button>

              <button
                disabled={page >= totalPages || loading}
                onClick={() => setPage((prev) => prev + 1)}
                className="
                  px-4
                  py-2
                  rounded-xl
                  bg-cyan-500/20
                  hover:bg-cyan-500/30
                  text-cyan-300
                  disabled:opacity-40
                  disabled:cursor-not-allowed
                  transition
                "
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
