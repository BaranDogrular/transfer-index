import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

const API_BASE_URL = "http://127.0.0.1:8000";

const comparisonRows = [
  { label: "Position", key: "position" },
  { label: "Age", key: "age", format: "integer", better: "lower" },
  { label: "Height", key: "height", format: "height" },
  { label: "Preferred Foot", key: "preferred_foot" },
  { label: "Club", key: "club" },
  { label: "League", key: "league" },
  { label: "Market Value", key: "market_value_m", format: "money", better: "higher" },
  { label: "Contract Until", key: "contract_expiration_date", format: "date" },
  { label: "Matches", key: "matches", format: "integer", better: "higher" },
  { label: "Goals", key: "goals", format: "integer", better: "higher" },
  { label: "Assists", key: "assists", format: "integer", better: "higher" },
  { label: "Minutes", key: "minutes_played", format: "integer", better: "higher" },
  { label: "Goals / 90", key: "goals_per_90", format: "decimal", better: "higher" },
  { label: "Assists / 90", key: "assists_per_90", format: "decimal", better: "higher" },
  { label: "G+A", key: "goal_contributions", format: "integer", better: "higher" },
  {
    label: "G+A / 90",
    key: "goal_contributions_per_90",
    format: "decimal",
    better: "higher",
  },
  { label: "Yellow Cards", key: "yellow_cards", format: "integer", better: "lower" },
  { label: "Red Cards", key: "red_cards", format: "integer", better: "lower" },
];

function isMissing(value) {
  return value === null || value === undefined || value === "";
}

function formatDate(value) {
  if (!value) return "-";

  return new Date(value).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatValue(value, format) {
  if (isMissing(value)) return "-";

  const numberValue = Number(value);

  if (format === "money") {
    if (!Number.isFinite(numberValue) || numberValue === 0) return "-";
    return `€${numberValue.toFixed(2)}M`;
  }

  if (format === "height") {
    if (!Number.isFinite(numberValue)) return "-";
    return `${numberValue} cm`;
  }

  if (format === "integer") {
    if (!Number.isFinite(numberValue)) return "-";
    return numberValue.toLocaleString();
  }

  if (format === "decimal") {
    if (!Number.isFinite(numberValue)) return "-";
    return numberValue.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  if (format === "date") {
    return formatDate(value);
  }

  return value;
}

function getBetterSide(row, player1, player2) {
  if (!row.better) return null;

  const value1 = player1?.[row.key];
  const value2 = player2?.[row.key];

  if (isMissing(value1) || isMissing(value2)) return null;

  const number1 = Number(value1);
  const number2 = Number(value2);

  if (!Number.isFinite(number1) || !Number.isFinite(number2) || number1 === number2) {
    return null;
  }

  if (row.better === "lower") {
    return number1 < number2 ? "player1" : "player2";
  }

  return number1 > number2 ? "player1" : "player2";
}

function PlayerSearchBox({
  label,
  query,
  setQuery,
  results,
  loading,
  selectedPlayer,
  onSelect,
  onClear,
}) {
  return (
    <div className="relative">
      <label className="mb-3 block text-sm font-bold uppercase tracking-wide text-zinc-500">
        {label}
      </label>

      <input
        type="text"
        value={query}
        onChange={(event) => {
          if (selectedPlayer) {
            onClear();
          }

          setQuery(event.target.value);
        }}
        placeholder="Search player..."
        className="w-full rounded-2xl border border-white/10 bg-black/40 px-4 py-3 text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-cyan-400"
      />

      {selectedPlayer && (
        <button
          type="button"
          onClick={onClear}
          className="absolute right-3 top-10 rounded-xl bg-white/10 px-3 py-1 text-xs font-bold text-zinc-300 transition-colors hover:bg-white/20"
        >
          Clear
        </button>
      )}

      {!selectedPlayer && query.length >= 2 && (
        <div className="absolute z-20 mt-2 max-h-80 w-full overflow-y-auto rounded-2xl border border-white/10 bg-zinc-950 shadow-2xl">
          {loading ? (
            <div className="px-4 py-4 text-sm text-zinc-500">Loading...</div>
          ) : results.length > 0 ? (
            results.map((player) => (
              <button
                key={player.id}
                type="button"
                onClick={() => onSelect(player)}
                className="flex w-full items-center gap-3 border-b border-white/5 px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-white/5"
              >
                <img
                  src={
                    player.image_url && player.image_url !== "https://..."
                      ? player.image_url
                      : "https://placehold.co/80x80/111111/ffffff?text=Player"
                  }
                  alt={player.name}
                  className="h-10 w-10 rounded-xl bg-zinc-900 object-cover"
                />

                <div className="min-w-0">
                  <div className="truncate font-bold text-white">{player.name}</div>
                  <div className="truncate text-sm text-zinc-500">
                    {player.club || "-"} · {player.position || "-"}
                  </div>
                </div>
              </button>
            ))
          ) : (
            <div className="px-4 py-4 text-sm text-zinc-500">No players found</div>
          )}
        </div>
      )}
    </div>
  );
}

function PlayerSummary({ player }) {
  return (
    <div className="flex items-center gap-4 rounded-3xl border border-white/10 bg-white/5 p-5">
      <img
        src={
          player?.image_url && player.image_url !== "https://..."
            ? player.image_url
            : "https://placehold.co/120x120/111111/ffffff?text=Player"
        }
        alt={player?.name || "Player"}
        className="h-20 w-20 shrink-0 rounded-2xl bg-zinc-900 object-cover"
      />

      <div className="min-w-0">
        <h2 className="truncate text-2xl font-black">{player?.name || "-"}</h2>
        <p className="mt-1 truncate text-zinc-400">
          {player?.club || "-"} · {player?.position || "-"}
        </p>
        <p className="mt-2 text-sm font-semibold text-cyan-300">
          {formatValue(player?.market_value_m, "money")}
        </p>
      </div>
    </div>
  );
}

export default function ComparePage() {
  const [searchParams] = useSearchParams();

  const [query1, setQuery1] = useState("");
  const [query2, setQuery2] = useState("");
  const [results1, setResults1] = useState([]);
  const [results2, setResults2] = useState([]);
  const [loading1, setLoading1] = useState(false);
  const [loading2, setLoading2] = useState(false);
  const [selectedPlayer1, setSelectedPlayer1] = useState(null);
  const [selectedPlayer2, setSelectedPlayer2] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [error, setError] = useState("");

  const searchPlayers = async (query, setResults, setLoading) => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }

    try {
      setLoading(true);
      const params = new URLSearchParams({
        q: query.trim(),
        page: "1",
        limit: "8",
      });
      const response = await fetch(`${API_BASE_URL}/players/search?${params}`);
      const data = await response.json();
      setResults(data.players || []);
    } catch (searchError) {
      console.error(searchError);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (!selectedPlayer1 || query1 !== selectedPlayer1.name) {
        searchPlayers(query1, setResults1, setLoading1);
      }
    }, 250);

    return () => clearTimeout(timeout);
  }, [query1, selectedPlayer1]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (!selectedPlayer2 || query2 !== selectedPlayer2.name) {
        searchPlayers(query2, setResults2, setLoading2);
      }
    }, 250);

    return () => clearTimeout(timeout);
  }, [query2, selectedPlayer2]);

  useEffect(() => {
    const loadInitialPlayer = async (paramName, setPlayer, setQuery) => {
      const playerId = searchParams.get(paramName);

      if (!playerId) return;

      try {
        const response = await fetch(`${API_BASE_URL}/players/${playerId}`);

        if (!response.ok) return;

        const data = await response.json();
        setPlayer(data);
        setQuery(data.name || "");
      } catch (initialLoadError) {
        console.error(initialLoadError);
      }
    };

    loadInitialPlayer("player1_id", setSelectedPlayer1, setQuery1);
    loadInitialPlayer("player2_id", setSelectedPlayer2, setQuery2);
  }, [searchParams]);

  useEffect(() => {
    const loadComparison = async () => {
      if (!selectedPlayer1 || !selectedPlayer2) {
        setComparison(null);
        return;
      }

      try {
        setComparisonLoading(true);
        setError("");

        const params = new URLSearchParams({
          player1_id: selectedPlayer1.id,
          player2_id: selectedPlayer2.id,
        });
        const response = await fetch(`${API_BASE_URL}/players/compare?${params}`);

        if (!response.ok) {
          throw new Error("Failed to compare players");
        }

        const data = await response.json();
        setComparison(data);
      } catch (comparisonError) {
        console.error(comparisonError);
        setComparison(null);
        setError("Comparison could not be loaded");
      } finally {
        setComparisonLoading(false);
      }
    };

    loadComparison();
  }, [selectedPlayer1, selectedPlayer2]);

  const selectPlayer1 = (player) => {
    setSelectedPlayer1(player);
    setQuery1(player.name || "");
    setResults1([]);
  };

  const selectPlayer2 = (player) => {
    setSelectedPlayer2(player);
    setQuery2(player.name || "");
    setResults2([]);
  };

  const player1 = comparison?.player1;
  const player2 = comparison?.player2;

  return (
    <div className="min-h-screen bg-black px-6 py-10 text-white">
      <div className="mx-auto max-w-7xl">
        <div className="mb-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-5xl font-black">Scout Comparison</h1>
            <p className="mt-3 text-zinc-400">Side-by-side player evaluation</p>
          </div>

          <Link to="/scouting" className="font-semibold text-cyan-400 hover:text-cyan-300">
            ← Back to Scouting
          </Link>
        </div>

        <div className="mb-8 grid grid-cols-1 gap-5 rounded-3xl border border-white/10 bg-white/5 p-6 md:grid-cols-2">
          <PlayerSearchBox
            label="Player 1"
            query={query1}
            setQuery={setQuery1}
            results={results1}
            loading={loading1}
            selectedPlayer={selectedPlayer1}
            onSelect={selectPlayer1}
            onClear={() => {
              setSelectedPlayer1(null);
              setQuery1("");
              setResults1([]);
            }}
          />

          <PlayerSearchBox
            label="Player 2"
            query={query2}
            setQuery={setQuery2}
            results={results2}
            loading={loading2}
            selectedPlayer={selectedPlayer2}
            onSelect={selectPlayer2}
            onClear={() => {
              setSelectedPlayer2(null);
              setQuery2("");
              setResults2([]);
            }}
          />
        </div>

        {error && (
          <div className="mb-8 rounded-2xl border border-red-500/20 bg-red-500/10 px-5 py-4 text-red-300">
            {error}
          </div>
        )}

        {comparisonLoading ? (
          <div className="rounded-3xl border border-white/10 bg-white/5 p-10 text-center text-zinc-400">
            Loading comparison...
          </div>
        ) : player1 && player2 ? (
          <>
            <div className="mb-6 grid grid-cols-1 gap-5 md:grid-cols-2">
              <PlayerSummary player={player1} />
              <PlayerSummary player={player2} />
            </div>

            <div className="overflow-x-auto rounded-3xl border border-white/10 bg-white/5">
              <table className="w-full min-w-[840px]">
                <thead className="border-b border-white/10 bg-zinc-950/80">
                  <tr className="text-left text-sm uppercase tracking-wide text-zinc-500">
                    <th className="px-6 py-4">Metric</th>
                    <th className="px-6 py-4">{player1.name || "Player 1"}</th>
                    <th className="px-6 py-4">{player2.name || "Player 2"}</th>
                  </tr>
                </thead>

                <tbody>
                  {comparisonRows.map((row) => {
                    const betterSide = getBetterSide(row, player1, player2);

                    return (
                      <tr key={row.key} className="border-b border-white/5 last:border-b-0">
                        <td className="px-6 py-4 font-semibold text-zinc-400">
                          {row.label}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex rounded-xl px-3 py-2 font-bold ${
                              betterSide === "player1"
                                ? "bg-cyan-400/10 text-cyan-300"
                                : "text-zinc-200"
                            }`}
                          >
                            {formatValue(player1[row.key], row.format)}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex rounded-xl px-3 py-2 font-bold ${
                              betterSide === "player2"
                                ? "bg-cyan-400/10 text-cyan-300"
                                : "text-zinc-200"
                            }`}
                          >
                            {formatValue(player2[row.key], row.format)}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="rounded-3xl border border-dashed border-white/10 bg-white/[0.03] p-10 text-center text-zinc-500">
            Select two players to compare.
          </div>
        )}
      </div>
    </div>
  );
}
