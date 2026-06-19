import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const EMPTY_FILTER_OPTIONS = {
  positions: [],
  nationalities: [],
  leagues: [],
  clubs: [],
  preferred_feet: [],
};

export default function Scouting() {
  const navigate = useNavigate();

  const [players, setPlayers] = useState([]);
  const [filterOptions, setFilterOptions] = useState(EMPTY_FILTER_OPTIONS);

  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [autocompleteResults, setAutocompleteResults] = useState([]);
  const [autocompleteLoading, setAutocompleteLoading] = useState(false);
  const [autocompleteOpen, setAutocompleteOpen] = useState(false);
  const [activeAutocompleteIndex, setActiveAutocompleteIndex] = useState(-1);

  const [positionFilter, setPositionFilter] = useState("");
  const [nationalityFilter, setNationalityFilter] = useState("");
  const [leagueFilter, setLeagueFilter] = useState("");
  const [clubFilter, setClubFilter] = useState("");
  const [preferredFootFilter, setPreferredFootFilter] = useState("");
  const [minAge, setMinAge] = useState("");
  const [maxAge, setMaxAge] = useState("");
  const [minValue, setMinValue] = useState("");
  const [maxValue, setMaxValue] = useState("");
  const [minMinutes, setMinMinutes] = useState("");
  const [minGoals, setMinGoals] = useState("");
  const [minAssists, setMinAssists] = useState("");

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

      if (nationalityFilter) {
        params.append("nationality", nationalityFilter);
      }

      if (leagueFilter) {
        params.append("league", leagueFilter);
      }

      if (clubFilter) {
        params.append("club", clubFilter);
      }

      if (preferredFootFilter) {
        params.append("preferred_foot", preferredFootFilter);
      }

      if (minAge) {
        params.append("min_age", minAge);
      }

      if (maxAge) {
        params.append("max_age", maxAge);
      }

      if (minValue) {
        params.append("min_value", minValue);
      }

      if (maxValue) {
        params.append("max_value", maxValue);
      }

      if (minMinutes) {
        params.append("min_minutes", minMinutes);
      }

      if (minGoals) {
        params.append("min_goals", minGoals);
      }

      if (minAssists) {
        params.append("min_assists", minAssists);
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
    setAutocompleteResults([]);
    setAutocompleteOpen(false);
    setActiveAutocompleteIndex(-1);
    setPositionFilter("");
    setNationalityFilter("");
    setLeagueFilter("");
    setClubFilter("");
    setPreferredFootFilter("");
    setMinAge("");
    setMaxAge("");
    setMinValue("");
    setMaxValue("");
    setMinMinutes("");
    setMinGoals("");
    setMinAssists("");
    setPage(1);
  };

  const formatMoney = (value) => {
    if (!value || value === 0) {
      return "-";
    }

    return `€${Number(value).toFixed(2)}M`;
  };

  const openPlayer = (player) => {
    if (!player) return;
    setAutocompleteOpen(false);
    navigate(`/player/${player.id}`);
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
        color: "score-high",
        bg: "scout-badge scout-badge-success",
      };
    }

    if (score >= 70) {
      return {
        label: "STRONG OPTION",
        color: "score-medium",
        bg: "scout-badge scout-badge-cyan",
      };
    }

    if (score >= 55) {
      return {
        label: "MONITOR",
        color: "score-warning",
        bg: "scout-badge scout-badge-warning",
      };
    }

    return {
      label: "HIGH RISK",
      color: "score-risk",
      bg: "scout-badge scout-badge-danger",
    };
  };

  const getScoreToneClass = (score) => {
    if (score >= 85) return "score-high";
    if (score >= 70) return "score-medium";
    if (score >= 55) return "score-warning";
    return "score-risk";
  };

  useEffect(() => {
    const loadFilterOptions = async () => {
      try {
        const response = await fetch(
          "http://127.0.0.1:8000/players/filter-options",
        );

        if (!response.ok) {
          throw new Error("Failed to fetch filter options");
        }

        const data = await response.json();
        setFilterOptions({
          ...EMPTY_FILTER_OPTIONS,
          ...data,
        });
      } catch (error) {
        console.error("FILTER OPTIONS ERROR:", error);
        setFilterOptions(EMPTY_FILTER_OPTIONS);
      }
    };

    loadFilterOptions();
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1);
    }, 300);

    return () => clearTimeout(timeout);
  }, [searchQuery]);

  useEffect(() => {
    const timeout = setTimeout(async () => {
      if (searchQuery.trim().length < 2) {
        setAutocompleteResults([]);
        setAutocompleteOpen(false);
        setActiveAutocompleteIndex(-1);
        return;
      }

      try {
        setAutocompleteLoading(true);
        const params = new URLSearchParams({
          q: searchQuery.trim(),
        });
        const response = await fetch(
          `http://127.0.0.1:8000/players/search?${params}`,
        );
        const data = await response.json();
        setAutocompleteResults(Array.isArray(data) ? data : data.players || []);
        setAutocompleteOpen(true);
        setActiveAutocompleteIndex(-1);
      } catch (error) {
        console.error("AUTOCOMPLETE ERROR:", error);
        setAutocompleteResults([]);
        setAutocompleteOpen(true);
      } finally {
        setAutocompleteLoading(false);
      }
    }, 275);

    return () => clearTimeout(timeout);
  }, [searchQuery]);

  useEffect(() => {
    setPage(1);
  }, [
    positionFilter,
    nationalityFilter,
    leagueFilter,
    clubFilter,
    preferredFootFilter,
    minAge,
    maxAge,
    minValue,
    maxValue,
    minMinutes,
    minGoals,
    minAssists,
  ]);

  useEffect(() => {
    loadPlayers();
  }, [
    debouncedQuery,
    positionFilter,
    nationalityFilter,
    leagueFilter,
    clubFilter,
    preferredFootFilter,
    minAge,
    maxAge,
    minValue,
    maxValue,
    minMinutes,
    minGoals,
    minAssists,
    page,
  ]);

  const filterControlClass =
    "h-12 w-full rounded-2xl border border-white/10 bg-black/40 px-4 text-white outline-none transition-colors placeholder:text-zinc-500 focus:border-cyan-400";

  const renderFilterLabel = (label) => (
    <span className="mb-2 block text-sm font-semibold text-zinc-300">
      {label}
    </span>
  );

  const renderSelectFilter = (label, value, onChange, options, placeholder) => (
    <label className="block">
      {renderFilterLabel(label)}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={filterControlClass}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => {
          const optionValue =
            typeof option === "string" ? option : option.value;
          const optionLabel =
            typeof option === "string" ? option : option.label || option.value;

          return (
            <option key={optionValue} value={optionValue}>
              {optionLabel}
            </option>
          );
        })}
      </select>
    </label>
  );

  const renderNumberFilter = (label, value, onChange, placeholder) => (
    <label className="block">
      {renderFilterLabel(label)}
      <input
        type="number"
        inputMode="numeric"
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={filterControlClass}
      />
    </label>
  );

  return (
    <div className="scout-theme min-h-screen px-6 py-10 text-white">
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
        <div className="mb-8 rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-xl font-black">Filters</h2>
              <p className="mt-1 text-sm text-zinc-400">
                {loading
                  ? "Loading players..."
                  : `${totalPlayers.toLocaleString()} players found`}
              </p>
            </div>

            <button
              type="button"
              onClick={resetFilters}
              className="scout-secondary-button h-12 rounded-2xl px-5 font-bold transition md:self-end"
            >
              Reset
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-4">
            <label className="relative block md:col-span-2">
              {renderFilterLabel("Search Player")}
              <input
                type="text"
                placeholder="Search by player name"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => {
                  if (searchQuery.trim().length >= 2) {
                    setAutocompleteOpen(true);
                  }
                }}
                onKeyDown={(event) => {
                  if (!autocompleteOpen) return;

                  if (event.key === "Escape") {
                    setAutocompleteOpen(false);
                    setActiveAutocompleteIndex(-1);
                  }

                  if (event.key === "ArrowDown") {
                    event.preventDefault();
                    setActiveAutocompleteIndex((current) =>
                      Math.min(current + 1, autocompleteResults.length - 1),
                    );
                  }

                  if (event.key === "ArrowUp") {
                    event.preventDefault();
                    setActiveAutocompleteIndex((current) =>
                      Math.max(current - 1, 0),
                    );
                  }

                  if (event.key === "Enter") {
                    event.preventDefault();
                    openPlayer(
                      autocompleteResults[
                        activeAutocompleteIndex >= 0
                          ? activeAutocompleteIndex
                          : 0
                      ],
                    );
                  }
                }}
                className={filterControlClass}
              />

              {autocompleteOpen && searchQuery.trim().length >= 2 && (
                <div className="absolute left-0 right-0 top-full z-30 mt-2 max-h-96 overflow-y-auto rounded-2xl border border-white/10 bg-zinc-950 shadow-2xl">
                  {autocompleteLoading ? (
                    <div className="px-4 py-4 text-sm text-zinc-500">
                      Loading players...
                    </div>
                  ) : autocompleteResults.length > 0 ? (
                    autocompleteResults.map((player, index) => (
                      <button
                        key={player.id}
                        type="button"
                        onMouseDown={(event) => {
                          event.preventDefault();
                          openPlayer(player);
                        }}
                        className={`flex w-full items-center gap-4 border-b border-white/5 px-4 py-3 text-left transition-colors last:border-b-0 ${
                          activeAutocompleteIndex === index
                            ? "bg-cyan-400/10"
                            : "hover:bg-white/5"
                        }`}
                      >
                        <img
                          src={
                            player.image_url && player.image_url !== "https://..."
                              ? player.image_url
                              : "https://placehold.co/80x80/111111/ffffff?text=Player"
                          }
                          alt={player.name}
                          className="h-11 w-11 rounded-xl bg-zinc-900 object-cover"
                        />

                        <div className="min-w-0 flex-1">
                          <div className="truncate font-bold text-white">
                            {player.name}
                          </div>
                          <div className="mt-1 flex min-w-0 items-center gap-2 text-sm text-zinc-500">
                            {player.club_logo_url ? (
                              <img
                                src={player.club_logo_url}
                                alt=""
                                className="h-4 w-4 shrink-0 rounded-full bg-white object-contain p-0.5"
                              />
                            ) : (
                              <span className="h-4 w-4 shrink-0 rounded-full border border-white/10 bg-white/5" />
                            )}
                            <span className="truncate">
                              {player.club || "-"} · {player.position || "-"}
                            </span>
                          </div>
                        </div>

                        <div className="text-sm font-bold text-cyan-300">
                          {formatMoney(player.market_value_m)}
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="px-4 py-4 text-sm text-zinc-500">
                      No players found
                    </div>
                  )}
                </div>
              )}
            </label>

            {renderSelectFilter(
              "Position",
              positionFilter,
              setPositionFilter,
              filterOptions.positions,
              "All positions",
            )}

            {renderSelectFilter(
              "Nationality",
              nationalityFilter,
              setNationalityFilter,
              filterOptions.nationalities,
              "All nationalities",
            )}
            {renderSelectFilter(
              "League",
              leagueFilter,
              setLeagueFilter,
              filterOptions.leagues,
              "All leagues",
            )}
            {renderSelectFilter(
              "Club",
              clubFilter,
              setClubFilter,
              filterOptions.clubs,
              "All clubs",
            )}
            {renderSelectFilter(
              "Preferred Foot",
              preferredFootFilter,
              setPreferredFootFilter,
              filterOptions.preferred_feet,
              "Any foot",
            )}

            {renderNumberFilter("Min Age", minAge, setMinAge, "18")}
            {renderNumberFilter("Max Age", maxAge, setMaxAge, "25")}
            {renderNumberFilter("Min Value (€M)", minValue, setMinValue, "5")}
            {renderNumberFilter("Max Value (€M)", maxValue, setMaxValue, "50")}
            {renderNumberFilter(
              "Min Minutes",
              minMinutes,
              setMinMinutes,
              "900",
            )}
            {renderNumberFilter("Min Goals", minGoals, setMinGoals, "5")}
            {renderNumberFilter(
              "Min Assists",
              minAssists,
              setMinAssists,
              "5",
            )}

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
                        <div className={`text-2xl font-black ${getScoreToneClass(score)}`}>
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
                className="scout-secondary-button
                  px-4
                  py-2
                  rounded-xl
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
                className="scout-primary-button
                  px-4
                  py-2
                  rounded-xl
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
