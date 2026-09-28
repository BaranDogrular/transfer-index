import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { formatClubDisplayName } from "../utils/display";

const EMPTY_FILTER_OPTIONS = {
  positions: [],
  nationalities: [],
  leagues: [],
  clubs: [],
  preferred_feet: [],
};

const humanizeFilterLabel = (value) =>
  String(value || "")
    .trim()
    .replace(/_/g, " ")
    .replace(/(^|[\s-])([a-z])/g, (match, separator, character) =>
      `${separator}${character.toUpperCase()}`,
    );

const normalizeFilterOptions = (options, labelFormatter = humanizeFilterLabel) => {
  const seenLabels = new Set();

  return (Array.isArray(options) ? options : []).reduce((result, option) => {
    const rawValue = typeof option === "string" ? option : option?.value;
    const rawLabel = typeof option === "string" ? null : option?.label;
    const value = String(rawValue || "").trim();
    const label = String(rawLabel || labelFormatter(value) || "").trim();
    const normalizedLabel = label.toLocaleLowerCase();

    if (
      !value ||
      !label ||
      value === "-" ||
      label === "-" ||
      value.toLocaleLowerCase() === "unknown" ||
      label.toLocaleLowerCase() === "unknown" ||
      seenLabels.has(normalizedLabel)
    ) {
      return result;
    }

    seenLabels.add(normalizedLabel);
    result.push({ value, label });
    return result;
  }, []);
};

const normalizeFilterOptionPayload = (data) => ({
  positions: normalizeFilterOptions(data?.positions),
  nationalities: normalizeFilterOptions(data?.nationalities),
  leagues: normalizeFilterOptions(data?.leagues),
  clubs: normalizeFilterOptions(data?.clubs, formatClubDisplayName),
  preferred_feet: normalizeFilterOptions(data?.preferred_feet),
});

const parseNumericFilter = (value) => {
  if (value === "") return null;

  const parsedValue = Number(value);
  return Number.isFinite(parsedValue) && parsedValue >= 0 ? parsedValue : null;
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
  const [loadError, setLoadError] = useState("");

  const limit = 50;
  const totalPages = Math.ceil(totalPlayers / limit);
  const parsedMinAge = parseNumericFilter(minAge);
  const parsedMaxAge = parseNumericFilter(maxAge);
  const parsedMinValue = parseNumericFilter(minValue);
  const parsedMaxValue = parseNumericFilter(maxValue);
  const invalidNumericInput = [
    minAge,
    maxAge,
    minValue,
    maxValue,
    minMinutes,
    minGoals,
    minAssists,
  ].some((value) => value !== "" && parseNumericFilter(value) === null);
  const numericValidationError = invalidNumericInput
    ? "Enter valid non-negative numbers."
    : parsedMinAge !== null &&
        parsedMaxAge !== null &&
        parsedMinAge > parsedMaxAge
      ? "Minimum age cannot be greater than maximum age."
      : parsedMinValue !== null &&
          parsedMaxValue !== null &&
          parsedMinValue > parsedMaxValue
        ? "Minimum market value cannot be greater than maximum market value."
        : "";
  const resultStatusText = numericValidationError
    ? numericValidationError
    : loadError
      ? loadError
      : loading
        ? "Loading players..."
        : `${totalPlayers.toLocaleString()} players found`;

  const loadPlayers = useCallback(async (signal) => {
    if (numericValidationError) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setLoadError("");

      const params = new URLSearchParams();

      params.append("page", page);
      params.append("limit", limit);

      if (debouncedQuery.trim()) {
        params.append("q", debouncedQuery.trim());
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

      const numericParams = {
        min_age: parsedMinAge,
        max_age: parsedMaxAge,
        min_value: parsedMinValue,
        max_value: parsedMaxValue,
        min_minutes: parseNumericFilter(minMinutes),
        min_goals: parseNumericFilter(minGoals),
        min_assists: parseNumericFilter(minAssists),
      };

      Object.entries(numericParams).forEach(([key, value]) => {
        if (value !== null) {
          params.append(key, String(value));
        }
      });

      const response = await fetch(
        `http://127.0.0.1:8000/players/search?${params}`,
        { signal },
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load scouting results.");
      }

      setPlayers(data.players || []);
      setTotalPlayers(data.total || 0);
    } catch (error) {
      if (error.name === "AbortError") return;

      setPlayers([]);
      setTotalPlayers(0);
      setLoadError(
        error instanceof TypeError
          ? "Unable to reach the scouting database."
          : error.message || "Unable to load scouting results.",
      );
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, [
    clubFilter,
    debouncedQuery,
    leagueFilter,
    minAssists,
    minGoals,
    minMinutes,
    nationalityFilter,
    numericValidationError,
    page,
    parsedMaxAge,
    parsedMaxValue,
    parsedMinAge,
    parsedMinValue,
    positionFilter,
    preferredFootFilter,
  ]);

  const resetFilters = () => {
    setSearchQuery("");
    setDebouncedQuery("");
    setAutocompleteResults([]);
    setAutocompleteOpen(false);
    setActiveAutocompleteIndex(-1);
    setLoadError("");
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
    if (score >= 90) {
      return {
        label: "Elite",
        color: "score-high",
        bg: "scout-badge scout-badge-success",
      };
    }

    if (score >= 80) {
      return {
        label: "Strong Option",
        color: "score-medium",
        bg: "scout-badge scout-badge-cyan",
      };
    }

    if (score >= 70) {
      return {
        label: "Good Option",
        color: "score-medium",
        bg: "scout-badge scout-badge-cyan",
      };
    }

    if (score >= 60) {
      return {
        label: "Monitor",
        color: "score-warning",
        bg: "scout-badge scout-badge-warning",
      };
    }

    return {
      label: "Low Priority",
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
        setFilterOptions(normalizeFilterOptionPayload(data));
      } catch {
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

  const changeSearchQuery = (event) => {
    const nextQuery = event.target.value;

    setSearchQuery(nextQuery);
    if (nextQuery.trim().length < 2) {
      setAutocompleteResults([]);
      setAutocompleteOpen(false);
      setActiveAutocompleteIndex(-1);
      setAutocompleteLoading(false);
    }
  };

  useEffect(() => {
    const abortController = new AbortController();
    const timeout = setTimeout(async () => {
      if (searchQuery.trim().length < 2) {
        return;
      }

      try {
        setAutocompleteLoading(true);
        const params = new URLSearchParams({
          q: searchQuery.trim(),
        });
        const response = await fetch(
          `http://127.0.0.1:8000/players/search?${params}`,
          { signal: abortController.signal },
        );
        const data = await response.json().catch(() => []);

        if (!response.ok) {
          throw new Error("Player search failed");
        }

        setAutocompleteResults(Array.isArray(data) ? data : data.players || []);
        setAutocompleteOpen(true);
        setActiveAutocompleteIndex(-1);
      } catch (error) {
        if (error.name === "AbortError") return;

        setAutocompleteResults([]);
        setAutocompleteOpen(true);
      } finally {
        if (!abortController.signal.aborted) {
          setAutocompleteLoading(false);
        }
      }
    }, 275);

    return () => {
      clearTimeout(timeout);
      abortController.abort();
    };
  }, [searchQuery]);

  useEffect(() => {
    const abortController = new AbortController();
    const requestTimeout = setTimeout(() => {
      loadPlayers(abortController.signal);
    }, 0);

    return () => {
      clearTimeout(requestTimeout);
      abortController.abort();
    };
  }, [loadPlayers]);

  const filterControlClass =
    "h-11 w-full rounded-xl border border-white/10 bg-black/40 px-3.5 text-sm text-white outline-none transition-colors placeholder:text-zinc-500 focus:border-cyan-400 focus:ring-1 focus:ring-emerald-400/20";

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
        onChange={(event) => {
          onChange(event.target.value);
          setPage(1);
        }}
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

  const renderNumberFilter = (
    label,
    value,
    onChange,
    placeholder,
    { allowDecimal = false } = {},
  ) => {
    const inputPattern = allowDecimal ? /^\d*(?:[.,]\d{0,2})?$/ : /^\d*$/;

    return (
      <label className="block">
        {renderFilterLabel(label)}
        <input
          type="text"
          inputMode={allowDecimal ? "decimal" : "numeric"}
          placeholder={placeholder}
          value={value}
          aria-invalid={Boolean(numericValidationError)}
          onChange={(event) => {
            const nextValue = event.target.value.trim();

            if (inputPattern.test(nextValue)) {
              onChange(nextValue.replace(",", "."));
              setPage(1);
            }
          }}
          className={`${filterControlClass} ${
            numericValidationError ? "border-red-400/40" : ""
          }`}
        />
      </label>
    );
  };

  return (
    <div className="scout-theme min-h-screen px-4 py-8 text-white sm:px-6 sm:py-10">
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
        <div className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-4 sm:p-5">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-xl font-black">Filters</h2>
              <p className="mt-1 text-sm text-zinc-400">
                {resultStatusText}
              </p>
            </div>

            <button
              type="button"
              onClick={resetFilters}
              className="scout-secondary-button h-11 rounded-xl px-4 text-sm font-bold transition sm:self-end"
            >
              Reset Filters
            </button>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-4">
            <label className="relative block md:col-span-2">
              {renderFilterLabel("Search Player")}
              <input
                type="text"
                placeholder="Search by player name"
                value={searchQuery}
                onChange={changeSearchQuery}
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
                <div className="custom-scrollbar absolute left-0 right-0 top-full z-30 mt-2 max-h-80 overflow-y-auto rounded-xl border border-white/10 bg-zinc-950 shadow-2xl">
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
                              {formatClubDisplayName(player.club)} / {player.position || "-"}
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
            {renderNumberFilter(
              "Min Value (€M)",
              minValue,
              setMinValue,
              "5",
              { allowDecimal: true },
            )}
            {renderNumberFilter(
              "Max Value (€M)",
              maxValue,
              setMaxValue,
              "50",
              { allowDecimal: true },
            )}
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

          {(numericValidationError || loadError) && (
            <div
              role="alert"
              className="mt-3 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm font-semibold text-red-200"
            >
              {numericValidationError || loadError}
            </div>
          )}
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

                      <td className="px-6 py-5 text-zinc-300">
                        {formatClubDisplayName(player.club)}
                      </td>

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
