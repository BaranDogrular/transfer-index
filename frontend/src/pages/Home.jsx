import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Link } from "react-router-dom";
import { formatClubDisplayName } from "../utils/display";

const TRENDING_SEARCH_NAMES = [
  "Lamine Yamal",
  "Erling Haaland",
  "Kylian Mbappe",
  "Pedri",
];

const normalizeSearchText = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

const toNumber = (value) => {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : 0;
};

const hasNumber = (value) => {
  if (value === null || value === undefined || value === "") {
    return false;
  }

  return Number.isFinite(Number(value));
};

const formatMoney = (value) => {
  const numberValue = Number(value);

  if (!Number.isFinite(numberValue) || numberValue <= 0) {
    return "-";
  }

  return `€${numberValue.toFixed(2)}M`;
};

const getPlayerScore = (player) => {
  const goals = toNumber(player.goals);
  const assists = toNumber(player.assists);
  const matches = Math.max(toNumber(player.matches), 1);
  const age = toNumber(player.age);
  const marketValue = toNumber(player.market_value_m);
  const injuryDays = hasNumber(player.injury_days)
    ? Number(player.injury_days)
    : null;
  let score = 35;

  score += Math.min(((goals + assists) / matches) * 18, 18);

  if (age >= 22 && age <= 28) {
    score += 20;
  } else if (age > 0 && age <= 31) {
    score += 10;
  }

  if (marketValue > 0 && marketValue <= 25) {
    score += 15;
  }

  if (injuryDays !== null && injuryDays < 30) {
    score += 10;
  }

  return Math.min(Math.round(score), 92);
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState([]);
  const [allPlayers, setAllPlayers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [playersLoading, setPlayersLoading] = useState(true);

  useEffect(() => {
    let isCurrent = true;

    const loadPlayers = async () => {
      try {
        setPlayersLoading(true);

        const response = await fetch("http://127.0.0.1:8000/players");
        const data = await response.json();

        if (isCurrent) {
          setAllPlayers(Array.isArray(data.players) ? data.players : []);
        }
      } catch {
        if (isCurrent) {
          setAllPlayers([]);
        }
      } finally {
        if (isCurrent) {
          setPlayersLoading(false);
        }
      }
    };

    loadPlayers();

    return () => {
      isCurrent = false;
    };
  }, []);

  const searchPlayers = async (searchTerm) => {
    if (!searchTerm.trim()) {
      setPlayers([]);
      return;
    }

    try {
      setLoading(true);
      const normalizedTerm = normalizeSearchText(searchTerm);
      const filtered = allPlayers.filter((player) =>
        normalizeSearchText(player.name).includes(normalizedTerm),
      );

      setPlayers(filtered.slice(0, 8));
    } catch {
      setPlayers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timeout = setTimeout(() => {
      searchPlayers(query);
    }, 300);

    return () => clearTimeout(timeout);
  }, [query, allPlayers]);

  const scoredPlayers = useMemo(
    () =>
      allPlayers.map((player) => ({
        ...player,
        transferIndexScore: getPlayerScore(player),
      })),
    [allPlayers],
  );

  const homeSections = useMemo(() => {
    const sortByScore = (items) =>
      [...items].sort((firstPlayer, secondPlayer) => {
        if (secondPlayer.transferIndexScore !== firstPlayer.transferIndexScore) {
          return secondPlayer.transferIndexScore - firstPlayer.transferIndexScore;
        }

        return toNumber(secondPlayer.market_value_m) - toNumber(firstPlayer.market_value_m);
      });
    const highestTransferIndex = sortByScore(scoredPlayers).slice(0, 4);
    const topRisingTalents = sortByScore(
      scoredPlayers.filter((player) => toNumber(player.age) > 0 && toNumber(player.age) <= 21),
    ).slice(0, 4);
    const hasUpdatedAt = scoredPlayers.some((player) => player.updated_at);
    const recentlyUpdatedPlayers = hasUpdatedAt
      ? [...scoredPlayers]
          .filter((player) => player.updated_at)
          .sort(
            (firstPlayer, secondPlayer) =>
              new Date(secondPlayer.updated_at).getTime() -
              new Date(firstPlayer.updated_at).getTime(),
          )
          .slice(0, 4)
      : scoredPlayers.slice(0, 4);
    const trendingPlayers = TRENDING_SEARCH_NAMES.map((name) => {
      const normalizedName = normalizeSearchText(name);

      return scoredPlayers.find((player) =>
        normalizeSearchText(player.name).includes(normalizedName),
      );
    }).filter(Boolean);
    const trendingIds = new Set(trendingPlayers.map((player) => player.id));
    const trendingSearches = [
      ...trendingPlayers,
      ...highestTransferIndex.filter((player) => !trendingIds.has(player.id)),
    ].slice(0, 4);

    return [
      {
        title: "Top Rising Talents",
        subtitle: "Young profiles with high Transfer Index.",
        players: topRisingTalents,
      },
      {
        title: "Highest Transfer Index",
        subtitle: "Best deterministic score profiles.",
        players: highestTransferIndex,
      },
      {
        title: "Recently Updated Players",
        subtitle: hasUpdatedAt ? "Latest refreshed player records." : "Featured player records.",
        players: recentlyUpdatedPlayers,
      },
      {
        title: "Trending Searches",
        subtitle: "Frequently tracked player profiles.",
        players: trendingSearches,
      },
    ];
  }, [scoredPlayers]);

  const renderPlayerRow = (player, sectionTitle) => (
    <Link
      key={`${sectionTitle}-${player.id}`}
      to={`/player/${player.id}`}
      className="
        group
        flex
        items-center
        gap-3
        rounded-2xl
        border
        border-white/5
        bg-black/25
        px-3
        py-3
        transition-colors
        hover:border-cyan-400/25
        hover:bg-white/10
      "
    >
      {player.image_url ? (
        <img
          src={player.image_url}
          alt={player.name}
          className="h-11 w-11 shrink-0 rounded-full border border-white/10 bg-zinc-900 object-cover"
        />
      ) : (
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-cyan-400/20 bg-cyan-400/10 text-sm font-black text-cyan-200">
          {String(player.name || "?").slice(0, 1)}
        </div>
      )}

      <div className="min-w-0 flex-1 text-left">
        <p className="truncate text-sm font-black text-white group-hover:text-cyan-200">
          {player.name || "-"}
        </p>
        <p className="mt-1 truncate text-xs text-zinc-400">
          {formatClubDisplayName(player.club)} / {player.position || "-"}
        </p>
      </div>

      <div className="shrink-0 text-right">
        <p className="text-sm font-black text-emerald-300">
          {player.transferIndexScore}
        </p>
        <p className="mt-1 text-[11px] font-semibold text-zinc-500">
          {formatMoney(player.market_value_m)}
        </p>
      </div>
    </Link>
  );
  const isSearchLoading = loading || (Boolean(query.trim()) && playersLoading);

  return (
    <div className="scout-theme relative min-h-screen overflow-x-hidden text-white">
      {/* VIDEO */}
      <video
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        className="
          fixed
          inset-0
          z-0
          w-full
          h-full
          object-cover
          brightness-75
          saturate-125
        "
      >
        <source src="/videos/stadium-night.mp4" type="video/mp4" />
      </video>

      {/* OVERLAY */}
      <div className="absolute inset-0 z-[1] bg-[#020806]/55"></div>
      <div className="pitch-line-overlay pointer-events-none absolute inset-0 z-[2] opacity-25"></div>

      {/* GRADIENT */}
      <div
        className="
        absolute
        inset-0
        z-[3]
        bg-gradient-to-b
        from-emerald-950/25
        via-black/45
        to-[#020806]/90
      "
      ></div>

      {/* NAVBAR */}
      <div
        className="
        absolute
        top-0
        left-0
        w-full
        z-30
        px-6
        py-6
      "
      >
        <div
          className="
          max-w-7xl
          mx-auto
          flex
          items-center
          justify-between
          bg-white/5
          backdrop-blur-xl
          border
          border-white/10
          rounded-2xl
          px-6
          py-4
        "
        >
          <h1
            className="
            text-2xl
            font-black
            tracking-tight
          "
          >
            Transfer Index
          </h1>

          <div
            className="
            hidden
            md:flex
            items-center
            gap-8
            text-gray-300
          "
          >
            <Link
              to="/scouting"
              className="
                hover:text-cyan-300
                transition-colors
              "
            >
              Scouting
            </Link>

            <button
              className="
              hover:text-cyan-300
              transition-colors
            "
            >
              AI Reports
            </button>

            <button
              className="
              hover:text-cyan-300
              transition-colors
            "
            >
              Transfer Scores
            </button>
          </div>
        </div>
      </div>

      {/* CONTENT */}
      <div
        className="
        relative
        z-20
        flex
        flex-col
        items-center
        justify-center
        min-h-screen
        px-6
      "
      >
        {/* HERO */}
        <div
          className="
          w-full
          max-w-4xl
          text-center
        "
        >
          <div
            className="
            inline-flex
            items-center
            px-4
            py-2
            rounded-full
            scout-badge
            scout-badge-cyan
            text-sm
            font-semibold
            mb-8
            backdrop-blur-lg
            border
            border-cyan-500/20
          "
          >
            AI Football Intelligence Platform
          </div>

          <h1
            className="
            text-6xl
            md:text-8xl
            font-black
            tracking-tight
            leading-none
          "
          >
            Transfer
            <span className="text-cyan-300"> Index</span>
          </h1>

          <p
            className="
            mt-8
            text-gray-200
            text-lg
            md:text-2xl
            max-w-3xl
            mx-auto
            leading-relaxed
          "
          >
            AI-powered scouting, transfer analysis and recruitment intelligence
            platform built for modern football clubs.
          </p>

          {/* SEARCH */}
          <div
            className="
            mt-12
            relative
            max-w-2xl
            mx-auto
          "
          >
            <Search
              className="
                absolute
                left-5
                top-1/2
                -translate-y-1/2
                text-gray-400
                w-5
                h-5
              "
            />

            <input
              type="text"
              placeholder="Search players..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="
                w-full
                pl-14
                pr-6
                py-5
                rounded-2xl
                bg-white/10
                backdrop-blur-lg
                border
                border-white/20
                text-white
                text-lg
                placeholder:text-gray-300
                outline-none
                focus:border-cyan-400
                focus:bg-white/15
                transition-all
                shadow-2xl
              "
            />

            {/* SEARCH RESULTS */}
            {query && (
              <div
                className="
                absolute
                top-full
                left-0
                mt-3
                w-full
                bg-white/5
                backdrop-blur-xl
                border
                border-white/10
                rounded-2xl
                overflow-hidden
                z-50
              "
              >
                {isSearchLoading ? (
                  <div
                    className="
                    p-4
                    text-gray-400
                  "
                  >
                    Searching...
                  </div>
                ) : players.length > 0 ? (
                  players.map((player) => (
                    <Link
                      key={player.id}
                      to={`/player/${player.id}`}
                      className="
                        flex
                        items-center
                        justify-between
                        px-5
                        py-4
                        hover:bg-white/10
                        transition-colors
                        border-b
                        border-white/5
                      "
                    >
                      <div>
                        <h3
                          className="
                          font-semibold
                          text-white
                        "
                        >
                          {player.name}
                        </h3>

                        <p
                          className="
                          text-sm
                          text-gray-400
                        "
                        >
                          {formatClubDisplayName(player.club)}
                        </p>
                      </div>

                      <span
                        className="
                        text-cyan-300
                        text-sm
                        font-semibold
                      "
                      >
                        {player.position || "-"}
                      </span>
                    </Link>
                  ))
                ) : (
                  <div
                    className="
                    p-4
                    text-gray-400
                  "
                  >
                    No players found.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* CTA */}
          <div
            className="
            mt-10
            flex
            flex-col
            sm:flex-row
            items-center
            justify-center
            gap-4
          "
          >
            <Link
              to="/scouting"
              className="
                px-8
                py-4
                rounded-2xl
                scout-primary-button
                font-black
                transition-all
                shadow-2xl
              "
            >
              Open Scouting Workspace
            </Link>

            <button
              className="
              px-8
              py-4
              rounded-2xl
              scout-secondary-button
              backdrop-blur-lg
              font-semibold
              transition-all
            "
            >
              Explore AI Reports
            </button>
          </div>
        </div>
      </div>

      <section className="relative z-20 mx-auto w-full max-w-7xl px-6 pb-16">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {homeSections.map((section) => (
            <div
              key={section.title}
              className="rounded-3xl border border-white/10 bg-black/35 p-5 shadow-2xl shadow-black/30 backdrop-blur-xl"
            >
              <div className="mb-4 flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-cyan-300">
                    Scout Board
                  </p>
                  <h2 className="mt-1 text-xl font-black text-white">
                    {section.title}
                  </h2>
                  <p className="mt-1 text-sm text-zinc-400">
                    {section.subtitle}
                  </p>
                </div>

                <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-black text-emerald-200">
                  Top 4
                </span>
              </div>

              {playersLoading ? (
                <div className="space-y-3">
                  {[0, 1, 2, 3].map((item) => (
                    <div
                      key={item}
                      className="h-[68px] animate-pulse rounded-2xl bg-white/5"
                    />
                  ))}
                </div>
              ) : section.players.length > 0 ? (
                <div className="space-y-3">
                  {section.players.map((player) =>
                    renderPlayerRow(player, section.title),
                  )}
                </div>
              ) : (
                <div className="rounded-2xl border border-white/5 bg-black/25 px-4 py-5 text-sm text-zinc-500">
                  No players available.
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
