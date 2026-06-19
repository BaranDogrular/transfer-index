import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useParams } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

const ADVANCED_STAT_TOOLTIPS = {
  minutes: "Toplam oynanan dakika.",
  clean_sheets: "Clean Sheets. Kalecinin gol yemeden tamamladığı maç sayısı.",
  saves: "Saves. Kalecinin kurtardığı şut sayısı.",
  save_percentage: "Save %. Kaleye gelen isabetli şutlarda kurtarış oranı.",
  goals_against: "Goals Against. Kalecinin yediği toplam gol sayısı.",
  pass_completion: "Pass Completion. Başarılı pasların toplam paslara oranı.",
  goals: "Goals. Oyuncunun attığı toplam gol.",
  assists: "Assists. Oyuncunun yaptığı toplam asist.",
  xg: "Expected Goals. Bir oyuncunun şutlarının gol olma olasılığı.",
  xa: "Expected Assists. Pasların beklenen asist değeri.",
  npxg: "Penaltılar hariç beklenen gol.",
  shots: "Shots. Oyuncunun denediği toplam şut.",
  shots_on_target: "Shots On Target. Kaleyi bulan şutlar.",
  key_passes: "Key Pass. Şutla sonuçlanan pas.",
  progressive_passes: "Takımı rakip kaleye anlamlı şekilde ilerleten paslar.",
  progressive_carries: "Topu sürerek rakip kaleye önemli mesafe taşıma.",
  passes_into_final_third: "Rakip son üçte birlik bölgeye gönderilen paslar.",
  passes_into_penalty_area: "Ceza sahasına gönderilen başarılı paslar.",
  shot_creating_actions: "Shot Creating Actions. Şutla sonuçlanan hücum aksiyonları.",
  goal_creating_actions: "Goal Creating Actions. Gol ile sonuçlanan hücum aksiyonları.",
  tackles: "Tackles. Oyuncunun yaptığı müdahale sayısı.",
  interceptions: "Interceptions. Oyuncunun kestiği paslar.",
  blocks: "Engellenen şut veya pas aksiyonları.",
  aerials_won: "Aerial Won. Kazanılan hava topu mücadeleleri.",
};

const POSITION_ADVANCED_STATS = {
  GOALKEEPER: [
    "minutes",
    "clean_sheets",
    "saves",
    "save_percentage",
    "goals_against",
    "pass_completion",
  ],
  CENTRE_BACK: [
    "minutes",
    "tackles",
    "interceptions",
    "blocks",
    "aerials_won",
    "progressive_passes",
  ],
  FULL_BACK: [
    "tackles",
    "interceptions",
    "progressive_carries",
    "progressive_passes",
    "key_passes",
    "assists",
    "xa",
  ],
  DEFENSIVE_MIDFIELDER: [
    "tackles",
    "interceptions",
    "progressive_passes",
    "key_passes",
    "passes_into_final_third",
  ],
  CENTRAL_MIDFIELDER: [
    "assists",
    "xa",
    "progressive_passes",
    "progressive_carries",
    "key_passes",
    "shot_creating_actions",
    "goal_creating_actions",
  ],
  ATTACKING_MIDFIELDER: [
    "goals",
    "assists",
    "xg",
    "xa",
    "key_passes",
    "shot_creating_actions",
    "goal_creating_actions",
    "progressive_carries",
  ],
  WINGER: [
    "goals",
    "assists",
    "xg",
    "xa",
    "shots",
    "shots_on_target",
    "progressive_carries",
    "key_passes",
  ],
  STRIKER: [
    "goals",
    "xg",
    "npxg",
    "shots",
    "shots_on_target",
    "goal_creating_actions",
    "shot_creating_actions",
  ],
};

const POSITION_GROUP_LABELS = {
  GOALKEEPER: "Goalkeeper View",
  CENTRE_BACK: "Centre Back View",
  FULL_BACK: "Full Back View",
  DEFENSIVE_MIDFIELDER: "Defensive Midfielder View",
  CENTRAL_MIDFIELDER: "Central Midfielder View",
  ATTACKING_MIDFIELDER: "Attacking Midfielder View",
  WINGER: "Winger View",
  STRIKER: "Striker View",
};

const TRANSFER_SCENARIO_SUB_SCORE_LABELS = [
  ["player_quality_score", "Player Quality"],
  ["squad_fit_score", "Squad Fit"],
  ["financial_fit_score", "Financial Fit"],
  ["performance_score", "Performance"],
  ["advanced_stats_score", "Advanced Stats"],
  ["age_profile_score", "Age Profile"],
  ["contract_score", "Contract"],
  ["culture_fit_score", "Culture Fit"],
  ["pressure_readiness_score", "Pressure"],
  ["transfer_risk_score", "Transfer Risk"],
];

const normalizePositionText = (position) =>
  String(position || "")
    .toLowerCase()
    .replace(/[-_/]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const normalizeClubName = (clubName) => {
  const normalized = String(clubName || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
  const ignoredTokens = new Set([
    "fc",
    "cf",
    "afc",
    "club",
    "football",
    "futbol",
    "the",
  ]);

  return normalized
    .split(/\s+/)
    .filter((token) => token && !ignoredTokens.has(token))
    .join(" ")
    .trim();
};

const getScenarioErrorMessage = (detail, fallbackMessage) => {
  const rawMessage = Array.isArray(detail)
    ? detail.map((item) => item?.msg || item).join(" ")
    : String(detail || fallbackMessage || "");
  const normalizedMessage = rawMessage.toLowerCase();

  if (normalizedMessage.includes("already at this club")) {
    return "Player is already at this club.";
  }

  if (normalizedMessage.includes("target club is required")) {
    return "Please enter a target club.";
  }

  if (normalizedMessage.includes("target club not found")) {
    return "Target club not found.";
  }

  if (normalizedMessage.includes("player not found")) {
    return "Player not found.";
  }

  return rawMessage || fallbackMessage || "Transfer scenario analysis failed.";
};

const getPositionGroup = (position) => {
  const normalized = normalizePositionText(position);

  if (normalized.includes("goalkeeper")) {
    return "GOALKEEPER";
  }

  if (
    normalized.includes("centre back") ||
    normalized.includes("center back")
  ) {
    return "CENTRE_BACK";
  }

  if (
    normalized.includes("left back") ||
    normalized.includes("right back") ||
    normalized.includes("full back") ||
    normalized.includes("wing back")
  ) {
    return "FULL_BACK";
  }

  if (normalized.includes("defensive midfield")) {
    return "DEFENSIVE_MIDFIELDER";
  }

  if (normalized.includes("attacking midfield")) {
    return "ATTACKING_MIDFIELDER";
  }

  if (
    normalized.includes("winger") ||
    normalized.includes("left wing") ||
    normalized.includes("right wing")
  ) {
    return "WINGER";
  }

  if (
    normalized.includes("centre forward") ||
    normalized.includes("center forward") ||
    normalized.includes("striker") ||
    normalized.includes("second striker") ||
    normalized === "forward"
  ) {
    return "STRIKER";
  }

  if (normalized.includes("central midfield") || normalized.includes("midfield")) {
    return "CENTRAL_MIDFIELDER";
  }

  return "CENTRAL_MIDFIELDER";
};

const getPositionAdvancedStatKeys = (position) => {
  const positionGroup = getPositionGroup(position);
  const keys = POSITION_ADVANCED_STATS[positionGroup] || POSITION_ADVANCED_STATS.CENTRAL_MIDFIELDER;

  return Array.from(new Set(["minutes", ...keys]));
};

function StatInfoTooltip({ title, description }) {
  if (!description) {
    return null;
  }

  return (
    <button
      type="button"
      className="group relative inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-cyan-400/30 bg-cyan-400/10 text-[11px] font-bold text-cyan-200 transition hover:border-cyan-300 hover:bg-cyan-400/20 focus:outline-none focus:ring-2 focus:ring-cyan-400/40"
      aria-label={`${title} info`}
    >
      ⓘ
      <span className="pointer-events-none absolute left-1/2 top-7 z-30 hidden w-64 -translate-x-1/2 rounded-xl border border-cyan-400/25 bg-zinc-950 px-3 py-2 text-left text-xs font-normal leading-5 text-zinc-300 shadow-2xl shadow-cyan-950/40 group-hover:block group-focus:block sm:left-0 sm:translate-x-0">
        <span className="mb-1 block font-semibold text-cyan-300">{title}</span>
        {description}
      </span>
    </button>
  );
}

function PlayerPage() {
  const { id } = useParams();

  const [player, setPlayer] = useState(null);
  const [score, setScore] = useState(null);
  const [aiReport, setAiReport] = useState(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [isScenarioModalOpen, setIsScenarioModalOpen] = useState(false);
  const [scenarioTargetClub, setScenarioTargetClub] = useState("");
  const [selectedScenarioClub, setSelectedScenarioClub] = useState(null);
  const [clubSuggestions, setClubSuggestions] = useState([]);
  const [clubSuggestionsLoading, setClubSuggestionsLoading] = useState(false);
  const [scenarioResult, setScenarioResult] = useState(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenarioAiLoading, setScenarioAiLoading] = useState(false);
  const [scenarioError, setScenarioError] = useState("");
  const [playerScoreResult, setPlayerScoreResult] = useState(null);
  const [playerScoreLoading, setPlayerScoreLoading] = useState(false);
  const [playerScoreError, setPlayerScoreError] = useState("");

  const [valuations, setValuations] = useState(null);
  const [valuationsLoading, setValuationsLoading] = useState(true);
  const [transfers, setTransfers] = useState([]);
  const [transfersLoading, setTransfersLoading] = useState(true);
  const [similarPlayers, setSimilarPlayers] = useState([]);
  const [similarPlayersLoading, setSimilarPlayersLoading] = useState(true);
  const [advancedStats, setAdvancedStats] = useState(null);
  const [advancedStatsLoading, setAdvancedStatsLoading] = useState(true);
  const [clubInfo, setClubInfo] = useState(null);
  const currentScenarioClubNames = [
    player?.club,
    clubInfo?.club_name,
  ].filter(Boolean);
  const currentScenarioClubIds = [
    player?.club_id,
    player?.current_club_id,
  ]
    .filter((value) => value !== null && value !== undefined)
    .map((value) => String(value));
  const normalizedCurrentScenarioClubNames = currentScenarioClubNames
    .map(normalizeClubName)
    .filter(Boolean);
  const isCurrentScenarioClubName = (clubName) => {
    const normalizedClubName = normalizeClubName(clubName);

    return (
      normalizedClubName &&
      normalizedCurrentScenarioClubNames.includes(normalizedClubName)
    );
  };
  const isCurrentScenarioClubOption = (club) => {
    if (!club) {
      return false;
    }

    return (
      currentScenarioClubIds.includes(String(club.club_id)) ||
      isCurrentScenarioClubName(club.club_name)
    );
  };
  const dedupeScenarioClubs = (clubs) => {
    const seen = new Set();

    return (Array.isArray(clubs) ? clubs : []).filter((club) => {
      if (isCurrentScenarioClubOption(club)) {
        return false;
      }

      const key = club.club_id
        ? `id:${club.club_id}`
        : `name:${normalizeClubName(club.club_name)}`;

      if (!key || seen.has(key)) {
        return false;
      }

      seen.add(key);
      return true;
    });
  };

  useEffect(() => {
    const searchTerm = scenarioTargetClub.trim();

    if (!isScenarioModalOpen || selectedScenarioClub || searchTerm.length < 2) {
      setClubSuggestions([]);
      setClubSuggestionsLoading(false);
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      try {
        setClubSuggestionsLoading(true);

        const response = await fetch(
          `http://127.0.0.1:8000/clubs/search?q=${encodeURIComponent(
            searchTerm,
          )}`,
        );

        if (!response.ok) {
          throw new Error("Failed to fetch clubs");
        }

        const data = await response.json();
        setClubSuggestions(dedupeScenarioClubs(data));
      } catch {
        setClubSuggestions([]);
      } finally {
        setClubSuggestionsLoading(false);
      }
    }, 250);

    return () => window.clearTimeout(timeoutId);
  }, [
    isScenarioModalOpen,
    scenarioTargetClub,
    selectedScenarioClub,
    player?.club,
    player?.club_id,
    player?.current_club_id,
    clubInfo?.club_name,
  ]);

  useEffect(() => {
    if (!isScenarioModalOpen || typeof document === "undefined") {
      return undefined;
    }

    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";

    const handleKeyDown = (event) => {
      if (event.key === "Escape" && !scenarioLoading && !scenarioAiLoading) {
        setIsScenarioModalOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = "";
      document.documentElement.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isScenarioModalOpen, scenarioLoading, scenarioAiLoading]);

  useEffect(() => {
    setClubInfo(null);

    fetch(`http://127.0.0.1:8000/players/${id}`)
      .then((res) => res.json())
      .then((data) => setPlayer(data))
      .catch((err) => console.error(err));
  }, [id]);

  useEffect(() => {
    const fetchValuations = async () => {
      try {
        setValuationsLoading(true);

        const response = await fetch(
          `http://127.0.0.1:8000/players/${id}/valuations`,
        );

        if (!response.ok) {
          throw new Error("Failed to fetch valuations");
        }

        const data = await response.json();
        setValuations(data);
      } catch (error) {
        console.error(error);
        setValuations(null);
      } finally {
        setValuationsLoading(false);
      }
    };

    fetchValuations();
  }, [id]);

  useEffect(() => {
    const fetchTransfers = async () => {
      try {
        setTransfersLoading(true);

        const response = await fetch(
          `http://127.0.0.1:8000/players/${id}/transfers`,
        );

        if (!response.ok) {
          throw new Error("Failed to fetch transfers");
        }

        const data = await response.json();
        setTransfers(data.transfers || []);
      } catch (error) {
        console.error(error);
        setTransfers([]);
      } finally {
        setTransfersLoading(false);
      }
    };

    fetchTransfers();
  }, [id]);

  useEffect(() => {
    const fetchSimilarPlayers = async () => {
      try {
        setSimilarPlayersLoading(true);

        const response = await fetch(
          `http://127.0.0.1:8000/players/${id}/similar`,
        );

        if (!response.ok) {
          throw new Error("Failed to fetch similar players");
        }

        const data = await response.json();
        setSimilarPlayers(data || []);
      } catch (error) {
        console.error(error);
        setSimilarPlayers([]);
      } finally {
        setSimilarPlayersLoading(false);
      }
    };

    fetchSimilarPlayers();
  }, [id]);

  useEffect(() => {
    const fetchAdvancedStats = async () => {
      try {
        setAdvancedStatsLoading(true);

        const response = await fetch(
          `http://127.0.0.1:8000/players/${id}/advanced-stats`,
        );

        if (!response.ok) {
          throw new Error("Failed to fetch advanced stats");
        }

        const data = await response.json();
        setAdvancedStats(data);
      } catch (error) {
        console.error(error);
        setAdvancedStats(null);
      } finally {
        setAdvancedStatsLoading(false);
      }
    };

    fetchAdvancedStats();
  }, [id]);

  useEffect(() => {
    if (!player) {
      return;
    }

    const clubLookupValue =
      player.club_id || player.current_club_id || player.club;

    if (!clubLookupValue) {
      setClubInfo(null);
      return;
    }

    let isCurrent = true;

    const fetchClubInfo = async () => {
      try {
        const response = await fetch(
          `http://127.0.0.1:8000/clubs/${encodeURIComponent(
            String(clubLookupValue),
          )}`,
        );

        if (!response.ok) {
          throw new Error("Failed to fetch club");
        }

        const data = await response.json();

        if (isCurrent) {
          setClubInfo(data);
        }
      } catch (error) {
        console.error(error);

        if (isCurrent) {
          setClubInfo(null);
        }
      }
    };

    fetchClubInfo();

    return () => {
      isCurrent = false;
    };
  }, [player]);

  const formatValue = (value, suffix = "") => {
    if (!value || value === 0 || value === "0") {
      return "-";
    }

    return `${value}${suffix}`;
  };

  const formatMoney = (value) => {
    if (!value || value === 0) {
      return "-";
    }

    return `€${Number(value).toFixed(2)}M`;
  };

  const formatInteger = (value) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return "-";
    }

    return numberValue.toLocaleString();
  };

  const formatDecimal = (value, digits = 2) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return "-";
    }

    return numberValue.toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  };

  const formatPercent = (value) => {
    const formattedValue = formatDecimal(value, 1);
    return formattedValue === "-" ? "-" : `${formattedValue}%`;
  };

  const getScoreBarWidth = (value) => {
    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return "0%";
    }

    return `${Math.min(100, Math.max(0, numberValue))}%`;
  };

  const getScoreBarClass = (value) => {
    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return "bg-zinc-700";
    }

    if (numberValue >= 85) return "bg-green-400";
    if (numberValue >= 70) return "bg-cyan-300";
    if (numberValue >= 55) return "bg-yellow-300";
    return "bg-red-400";
  };

  const getScoreTextClass = (value) => {
    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return "text-cyan-300";
    }

    if (numberValue >= 85) return "score-high";
    if (numberValue >= 70) return "score-medium";
    if (numberValue >= 55) return "score-warning";
    return "score-risk";
  };

  const formatEuroRaw = (value) => {
    if (value === null || value === undefined || value === 0) {
      return "-";
    }

    if (value >= 1000000) {
      return `€${(value / 1000000).toFixed(1)}M`;
    }

    if (value >= 1000) {
      return `€${(value / 1000).toFixed(0)}K`;
    }

    return `€${value}`;
  };

  const formatContractDate = (dateValue) => {
    if (!dateValue) {
      return "-";
    }

    return new Date(dateValue).toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  };

  const formatText = (value) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    return value;
  };

  const formatKnownText = (value) => {
    const text = formatText(value);

    return text === "Unknown" ? "-" : text;
  };

  const formatTransferMoney = (value) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return "-";
    }

    if (numberValue >= 1000000) {
      return `€${(numberValue / 1000000).toFixed(1)}M`;
    }

    if (numberValue >= 1000) {
      return `€${(numberValue / 1000).toFixed(0)}K`;
    }

    return `€${numberValue}`;
  };

  const formatTransferFee = (transfer) => {
    const typeLabels = {
      loan: "Kiralık",
      loaned: "Kiralık",
      "loan return": "Kiralıktan geri döndü",
      "end of loan": "Kiralıktan geri döndü",
      "free transfer": "Bedelsiz",
      free: "Bedelsiz",
      "ablöse yok": "Bedelsiz",
      released: "Released",
    };

    if (transfer.transfer_label) {
      return transfer.transfer_label;
    }

    const transferType = transfer.transfer_type?.toLowerCase();

    if (transferType && typeLabels[transferType]) {
      return typeLabels[transferType];
    }

    const fee = transfer.transfer_fee_in_eur ?? transfer.transfer_fee;

    if (fee === null || fee === undefined || fee === "") {
      return "-";
    }

    if (Number(fee) <= 0) {
      return "-";
    }

    return formatTransferMoney(fee);
  };

  const getValidImageUrl = (imageUrl) =>
    imageUrl && imageUrl !== "https://..." ? imageUrl : null;

  const renderClubLogo = (logoUrl, className = "h-5 w-5") =>
    logoUrl ? (
      <img
        src={logoUrl}
        alt=""
        className={`${className} rounded-full bg-white object-contain p-0.5`}
      />
    ) : null;

  const renderClubCell = (clubName, country, logoUrl) => (
    <div className="flex min-w-0 items-center gap-3">
      {renderClubLogo(logoUrl, "h-8 w-8 shrink-0")}
      <div className="flex min-w-0 flex-col">
        <span className="truncate font-semibold text-zinc-100">
          {formatText(clubName)}
        </span>
        {country && (
          <span className="mt-1 truncate text-xs uppercase tracking-wide text-zinc-500">
            {country}
          </span>
        )}
      </div>
    </div>
  );

  const getRecommendation = () => {
    if (!playerScoreResult) return null;

    const value = playerScoreResult.player_score;

    if (value >= 86) {
      return {
        label: "ELITE PLAYER",
        className: "scout-badge scout-badge-success",
      };
    }

    if (value >= 76) {
      return {
        label: "HIGH QUALITY",
        className: "scout-badge scout-badge-cyan",
      };
    }

    if (value >= 66) {
      return {
        label: "STRONG PROSPECT",
        className: "scout-badge scout-badge-warning",
      };
    }

    return {
      label: "DEVELOPING",
      className: "scout-badge scout-badge-danger",
    };
  };

  const getScoutTags = () => {
    const tags = [];

    if (player.age && player.age <= 23) tags.push("YOUNG TALENT");
    if (player.market_value_m >= 20) tags.push("HIGH VALUE");
    if (player.market_value_m > 0 && player.market_value_m <= 5) {
      tags.push("VALUE PICK");
    }
    if (player.preferred_foot && player.preferred_foot !== "Unknown") {
      tags.push(`${player.preferred_foot.toUpperCase()} FOOT`);
    }
    if (player.position) tags.push(player.position.toUpperCase());

    return tags;
  };

  const analyzeTransfer = async () => {
    setScore(null);
    setAiReport(null);
    setLoadingAi(true);

    try {
      const scoreResponse = await fetch(
        `http://127.0.0.1:8000/players/${id}/transfer-score`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            team_name: "Fenerbahçe",
            needed_position: player.position,
            max_market_value_m: 20,
            max_salary_m: 4,
            preferred_age_min: 22,
            preferred_age_max: 29,
          }),
        },
      );

      const scoreData = await scoreResponse.json();
      const scoreResult = scoreData.transfer_index || scoreData;
      setScore(scoreResult);

      const aiResponse = await fetch(
        `http://127.0.0.1:8000/players/${id}/ai-report`,
        { method: "POST" },
      );

      const aiData = await aiResponse.json();
      setAiReport(aiData.report);
    } catch (error) {
      console.error(error);
    } finally {
      setLoadingAi(false);
    }
  };

  const analyzePlayerScore = async () => {
    setPlayerScoreError("");
    setPlayerScoreResult(null);
    setPlayerScoreLoading(true);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/players/${id}/player-score`,
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Player score analysis failed.");
      }

      setPlayerScoreResult(data);
    } catch (error) {
      console.error(error);
      setPlayerScoreError(error.message || "Player score analysis failed.");
    } finally {
      setPlayerScoreLoading(false);
    }
  };

  const openTransferScenarioModal = () => {
    setIsScenarioModalOpen(true);
    setScenarioError("");
  };

  const closeTransferScenarioModal = () => {
    setIsScenarioModalOpen(false);
  };

  const analyzeTransferScenario = async (event) => {
    event.preventDefault();
    setScenarioError("");
    setScenarioResult(null);

    const targetClub = (
      selectedScenarioClub?.club_name || scenarioTargetClub
    ).trim();

    if (!targetClub) {
      setScenarioError("Please enter a target club.");
      return;
    }

    if (isScenarioCurrentClubTarget) {
      setScenarioError("Player is already at this club.");
      return;
    }

    setScenarioLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/transfer-scenarios/analyze",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            player_id: Number(id),
            target_club: targetClub,
          }),
        },
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          getScenarioErrorMessage(
            data.detail,
            "Transfer scenario analysis failed.",
          ),
        );
      }

      setScenarioResult(data);
      setScenarioError("");
    } catch (error) {
      setScenarioError(error.message || "Transfer scenario analysis failed.");
    } finally {
      setScenarioLoading(false);
    }
  };

  const analyzeTransferScenarioAi = async () => {
    setScenarioError("");
    setScenarioResult(null);

    const targetClub = (
      selectedScenarioClub?.club_name || scenarioTargetClub
    ).trim();

    if (!targetClub) {
      setScenarioError("Please enter a target club.");
      return;
    }

    if (isScenarioCurrentClubTarget) {
      setScenarioError("Player is already at this club.");
      return;
    }

    setScenarioAiLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/transfer-scenarios/ai-analyze",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            player_id: Number(id),
            target_club: targetClub,
          }),
        },
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          getScenarioErrorMessage(
            data.detail,
            "AI transfer scenario analysis failed.",
          ),
        );
      }

      setScenarioResult(data);
      setScenarioError("");
    } catch (error) {
      setScenarioError(
        error.message || "AI transfer scenario analysis failed.",
      );
    } finally {
      setScenarioAiLoading(false);
    }
  };

  if (!player) {
    return (
      <div className="scout-theme flex min-h-screen items-center justify-center text-2xl text-white">
        Loading player...
      </div>
    );
  }

  const recommendation = getRecommendation();
  const scoutTags = getScoutTags();
  const playerImageUrl = getValidImageUrl(player.image_url);
  const clubRouteValue = player.club_id || player.current_club_id || player.club;
  const clubPath = clubRouteValue
    ? `/club/${encodeURIComponent(String(clubRouteValue))}`
    : null;
  const clubName = clubInfo?.club_name || player.club;
  const clubLeague = clubInfo?.league || player.league;
  const clubCountry = clubInfo?.country;
  const clubLogoUrl = clubInfo?.logo_url || player.club_logo_url;
  const nationalTeamFlagUrl =
    player.national_team_flag_url || player.country_flag_url;
  const profileFields = [
    { label: "Nationality", value: formatText(player.nationality) },
    { label: "Position", value: formatText(player.position) },
    { label: "Age", value: formatValue(player.age) },
    { label: "Height", value: formatValue(player.height_cm, " cm") },
    {
      label: "Preferred Foot",
      value:
        player.preferred_foot && player.preferred_foot !== "Unknown"
          ? player.preferred_foot
          : "-",
    },
    {
      label: "Contract Until",
      value: formatContractDate(player.contract_expiration_date),
    },
  ];
  const playerInfoFields = [
    {
      label: "Date of Birth",
      value: formatContractDate(player.date_of_birth || player.birth_date),
    },
    { label: "Age", value: formatValue(player.age) },
    { label: "Nationality", value: formatText(player.nationality) },
    { label: "Position", value: formatText(player.position) },
    { label: "Height", value: formatValue(player.height_cm, " cm") },
    {
      label: "Preferred Foot",
      value:
        player.preferred_foot && player.preferred_foot !== "Unknown"
          ? player.preferred_foot
          : "-",
    },
    {
      label: "Contract Until",
      value: formatContractDate(player.contract_expiration_date),
    },
    {
      label: "Current Club",
      value:
        clubName && clubPath ? (
          <Link
            to={clubPath}
            className="inline-flex items-center gap-2 text-cyan-300 transition-colors hover:text-cyan-200"
          >
            {renderClubLogo(clubLogoUrl)}
            <span>{clubName}</span>
          </Link>
        ) : (
          formatText(clubName)
        ),
    },
    { label: "League", value: formatText(clubLeague) },
  ];
  const nationalTeamFields = [
    { label: "Nationality", value: formatKnownText(player.nationality) },
    {
      label: "National Team",
      value: formatKnownText(player.national_team_name),
    },
    {
      label: "International Caps",
      value: formatInteger(player.international_caps),
    },
    {
      label: "International Goals",
      value: formatInteger(player.international_goals),
    },
  ];
  const positionGroup = getPositionGroup(player.position);
  const advancedStatDefinitions = {
    minutes: {
      label: "Minutes",
      value: formatInteger(advancedStats?.minutes),
    },
    clean_sheets: {
      label: "Clean Sheets",
      value: formatInteger(advancedStats?.clean_sheets),
    },
    saves: {
      label: "Saves",
      value: formatInteger(advancedStats?.saves),
    },
    save_percentage: {
      label: "Save %",
      value: formatPercent(advancedStats?.save_percentage),
    },
    goals_against: {
      label: "Goals Against",
      value: formatInteger(advancedStats?.goals_against),
    },
    pass_completion: {
      label: "Pass Completion",
      value: formatPercent(advancedStats?.pass_completion),
    },
    goals: {
      label: "Goals",
      value: formatInteger(advancedStats?.goals),
    },
    assists: {
      label: "Assists",
      value: formatInteger(advancedStats?.assists),
    },
    xg: {
      label: "xG",
      value: formatDecimal(advancedStats?.xg),
    },
    xa: {
      label: "xA",
      value: formatDecimal(advancedStats?.xa),
    },
    npxg: {
      label: "npxG",
      value: formatDecimal(advancedStats?.npxg),
    },
    shots: {
      label: "Shots",
      value: formatInteger(advancedStats?.shots),
    },
    shots_on_target: {
      label: "Shots On Target",
      value: formatInteger(advancedStats?.shots_on_target),
    },
    key_passes: {
      label: "Key Passes",
      value: formatInteger(advancedStats?.key_passes),
    },
    progressive_passes: {
      label: "Progressive Passes",
      value: formatInteger(advancedStats?.progressive_passes),
    },
    progressive_carries: {
      label: "Progressive Carries",
      value: formatInteger(advancedStats?.progressive_carries),
    },
    passes_into_final_third: {
      label: "Passes Into Final Third",
      value: formatInteger(advancedStats?.passes_into_final_third),
    },
    passes_into_penalty_area: {
      label: "Passes Into Penalty Area",
      value: formatInteger(advancedStats?.passes_into_penalty_area),
    },
    shot_creating_actions: {
      label: "SCA",
      value: formatInteger(advancedStats?.shot_creating_actions),
    },
    goal_creating_actions: {
      label: "GCA",
      value: formatInteger(advancedStats?.goal_creating_actions),
    },
    tackles: {
      label: "Tackles",
      value: formatInteger(advancedStats?.tackles),
    },
    interceptions: {
      label: "Interceptions",
      value: formatInteger(advancedStats?.interceptions),
    },
    blocks: {
      label: "Blocks",
      value: formatInteger(advancedStats?.blocks),
    },
    aerials_won: {
      label: "Aerial Won",
      value: formatInteger(advancedStats?.aerials_won),
    },
  };
  const advancedStatFields = getPositionAdvancedStatKeys(player.position)
    .map((fieldName) => {
      const definition = advancedStatDefinitions[fieldName];

      if (!definition) {
        return null;
      }

      return {
        ...definition,
        key: fieldName,
        description: ADVANCED_STAT_TOOLTIPS[fieldName],
      };
    })
    .filter(Boolean);
  const scenarioAnalysis =
    scenarioResult?.deterministic_analysis || scenarioResult;
  const scenarioSubScores = scenarioAnalysis?.sub_scores || null;
  const scenarioSubScoreItems = TRANSFER_SCENARIO_SUB_SCORE_LABELS.map(
    ([key, label]) => ({
      key,
      label,
      value: scenarioSubScores?.[key],
    }),
  );
  const scenarioClub =
    scenarioResult?.target_club_context ||
    scenarioResult?.scenario_context?.target_club_context ||
    scenarioResult?.target_club;
  const scenarioClubName =
    scenarioClub?.club_name || selectedScenarioClub?.club_name || scenarioTargetClub;
  const scenarioClubLeague =
    scenarioClub?.league || selectedScenarioClub?.league || "";
  const scenarioTargetClubName =
    selectedScenarioClub?.club_name || scenarioTargetClub;
  const isScenarioTargetClubEmpty = !scenarioTargetClubName.trim();
  const isScenarioCurrentClubTarget =
    Boolean(scenarioTargetClubName.trim()) &&
    (isCurrentScenarioClubName(scenarioTargetClubName) ||
      isCurrentScenarioClubOption(selectedScenarioClub));
  const isScenarioAnalyzeDisabled =
    scenarioLoading ||
    scenarioAiLoading ||
    isScenarioTargetClubEmpty ||
    isScenarioCurrentClubTarget;
  const isScenarioErrorWarning =
    scenarioError &&
    [
      "Please enter a target club.",
      "Player is already at this club.",
      "Target club not found.",
    ].includes(scenarioError);
  const scenarioSourceBadge =
    {
      openai: {
        label: "AI",
        className: "border-cyan-400/30 bg-cyan-400/10 text-cyan-200",
      },
      cache: {
        label: "Cached",
        className: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
      },
      fallback: {
        label: "Fallback",
        className: "border-amber-400/30 bg-amber-400/10 text-amber-200",
      },
    }[scenarioResult?.source] || null;
  const scenarioReportItems = [
    ["Recommendation", scenarioAnalysis?.recommendation],
    ["Summary", scenarioAnalysis?.summary],
    ["Tactical Fit", scenarioAnalysis?.tactical_fit],
    ["Financial Risk", scenarioAnalysis?.financial_risk],
    ["Contract Risk", scenarioAnalysis?.contract_risk],
    [
      "Squad Fit",
      scenarioSubScores?.squad_fit_score !== null &&
      scenarioSubScores?.squad_fit_score !== undefined
        ? `${formatInteger(scenarioSubScores.squad_fit_score)} / 100`
        : null,
    ],
    [
      "Culture Fit",
      scenarioSubScores?.culture_fit_score !== null &&
      scenarioSubScores?.culture_fit_score !== undefined
        ? `${formatInteger(scenarioSubScores.culture_fit_score)} / 100`
        : null,
    ],
  ];
  const scenarioMissingDataNotes = Array.from(new Set([
    ...(Array.isArray(scenarioAnalysis?.missing_data_notes)
      ? scenarioAnalysis.missing_data_notes
      : []),
    ...(Array.isArray(scenarioAnalysis?.risks)
      ? scenarioAnalysis.risks.filter((item) =>
          String(item).toLowerCase().includes("missing verified data"),
        )
      : []),
  ]));

  return (
    <div className="scout-theme min-h-screen overflow-hidden text-white">
      <div className="fixed inset-0 bg-gradient-to-br from-zinc-950 via-black to-black opacity-70"></div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-10">
          <Link
            to="/scouting"
            className="text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
          >
            ← Back to Scouting
          </Link>

          <div className="scout-badge scout-badge-cyan rounded-full px-4 py-2 text-sm font-semibold">
            AI SCOUT PROFILE
          </div>
        </div>

        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-[32px] p-10">
          <div className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,1fr)_380px]">
            <div className="flex flex-col gap-8 lg:flex-row">
              {playerImageUrl && (
                <div className="h-52 w-44 shrink-0 overflow-hidden rounded-3xl border border-white/10 bg-zinc-900 shadow-2xl">
                  <img
                    src={playerImageUrl}
                    alt={player.name}
                    className="h-full w-full object-cover"
                  />
                </div>
              )}

              <div className="min-w-0 flex-1">
                <h1 className="text-5xl font-black tracking-tight md:text-6xl">
                  {player.name}
                </h1>

                <div className="mt-4 flex flex-wrap items-center gap-2 text-lg text-zinc-400">
                  {clubName && clubPath ? (
                    <Link
                      to={clubPath}
                      className="inline-flex items-center gap-2 transition-colors hover:text-cyan-300"
                    >
                      {renderClubLogo(clubLogoUrl)}
                      <span>{clubName}</span>
                    </Link>
                  ) : (
                    <span>{clubName || "Unknown Club"}</span>
                  )}
                  <span className="text-zinc-600">&bull;</span>
                  <span>{clubLeague || "Unknown League"}</span>
                </div>

                <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {profileFields.map((field) => (
                    <div
                      key={field.label}
                      className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3"
                    >
                      <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
                        {field.label}
                      </p>
                      <p className="mt-1 font-semibold text-zinc-100">
                        {field.value}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="mt-6 flex flex-wrap gap-3">
                  {scoutTags.map((tag) => (
                    <span
                      key={tag}
                      className="scout-badge scout-badge-cyan rounded-full px-3 py-1 text-xs font-bold"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <button
                    onClick={analyzePlayerScore}
                    disabled={playerScoreLoading}
                    className="scout-secondary-button rounded-2xl px-6 py-4 font-black transition-all disabled:opacity-50"
                  >
                    {playerScoreLoading ? "Scoring..." : "Player Score"}
                  </button>

                  <button
                    onClick={openTransferScenarioModal}
                    disabled={scenarioLoading || scenarioAiLoading}
                    className="scout-primary-button rounded-2xl px-6 py-4 font-black transition-all disabled:opacity-50"
                  >
                    Transfer Scenario
                  </button>

                  <Link
                    to={`/compare?player1_id=${player.id}`}
                    className="scout-secondary-button rounded-2xl px-6 py-4 text-center font-black transition-all"
                  >
                    Compare Player
                  </Link>

                  {recommendation && (
                    <div
                      className={`flex items-center rounded-2xl px-5 py-4 text-sm font-black ${recommendation.className}`}
                    >
                      {recommendation.label}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-zinc-950/80 p-6">
              <div className="flex items-start gap-4">
                {clubLogoUrl && (
                  <img
                    src={clubLogoUrl}
                    alt=""
                    className="h-16 w-16 shrink-0 rounded-2xl bg-white object-contain p-2"
                  />
                )}

                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
                    Current Club
                  </p>

                  {clubName && clubPath ? (
                    <Link
                      to={clubPath}
                      className="mt-2 block truncate text-2xl font-black text-white transition-colors hover:text-cyan-300"
                    >
                      {clubName}
                    </Link>
                  ) : (
                    <h2 className="mt-2 text-2xl font-black text-white">
                      {clubName || "-"}
                    </h2>
                  )}

                  <p className="mt-1 truncate text-sm text-zinc-400">
                    {clubLeague || "-"}
                  </p>
                </div>
              </div>

              <div className="mt-8 space-y-4">
                <div className="flex items-center justify-between gap-4 border-b border-white/5 pb-4">
                  <span className="text-zinc-500">League</span>
                  <span className="text-right font-semibold text-zinc-100">
                    {clubLeague || "-"}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-4 border-b border-white/5 pb-4">
                  <span className="text-zinc-500">Country</span>
                  <span className="text-right font-semibold text-zinc-100">
                    {clubCountry || "-"}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-4 border-b border-white/5 pb-4">
                  <span className="text-zinc-500">Contract Until</span>
                  <span className="text-right font-semibold text-zinc-100">
                    {formatContractDate(player.contract_expiration_date)}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-4">
                  <span className="text-zinc-500">Current Market Value</span>
                  <span className="text-right text-2xl font-black text-cyan-300">
                    {formatMoney(player.market_value_m)}
                  </span>
                </div>
              </div>

              <div className="mt-8 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-cyan-300">
                  Player Score
                </p>
                <div className="mt-2 flex items-end justify-between gap-4">
                  <span
                    className={`text-5xl font-black ${getScoreTextClass(
                      playerScoreResult?.player_score,
                    )}`}
                  >
                    {playerScoreResult ? playerScoreResult.player_score : "--"}
                  </span>
                  <span className="pb-2 text-sm font-semibold text-zinc-400">
                    Club-independent
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-12">
            <div className="bg-black/40 rounded-3xl p-6 border border-white/5">
              <p className="text-zinc-400 mb-2">Market Value</p>
              <h3 className="text-3xl font-black">
                {formatMoney(player.market_value_m)}
              </h3>
            </div>

            <div className="bg-black/40 rounded-3xl p-6 border border-white/5">
              <p className="text-zinc-400 mb-2">Salary</p>
              <h3 className="text-3xl font-black">
                {formatMoney(player.salary_m)}
              </h3>
            </div>

            <div className="bg-black/40 rounded-3xl p-6 border border-white/5">
              <p className="text-zinc-400 mb-2">Age</p>
              <h3 className="text-3xl font-black">
                {player.age ? player.age : "-"}
              </h3>
            </div>

            <div className="bg-black/40 rounded-3xl p-6 border border-white/5">
              <p className="text-zinc-400 mb-2">Height</p>
              <h3 className="text-3xl font-black">
                {formatValue(player.height_cm, " cm")}
              </h3>
            </div>
          </div>

          <div className="mt-6 rounded-3xl border border-white/5 bg-black/40 p-6">
            <div className="mb-6">
              <h2 className="text-2xl font-black">Player Info</h2>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {playerInfoFields.map((field) => (
                <div
                  key={field.label}
                  className="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-zinc-950/70 px-4 py-3"
                >
                  <span className="text-sm text-zinc-500">{field.label}</span>
                  <span className="text-right text-sm font-semibold text-zinc-100">
                    {field.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-10 bg-black/40 rounded-3xl p-8 border border-white/5">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
              <div>
                <h2 className="text-3xl font-black">Market Value History</h2>
                <p className="text-zinc-400 mt-2">
                  Historical Transfermarkt valuation trend
                </p>
              </div>
            </div>

            {valuationsLoading ? (
              <div className="h-72 flex items-center justify-center text-zinc-400 animate-pulse">
                Loading valuation history...
              </div>
            ) : !valuations || valuations.history.length === 0 ? (
              <div className="h-72 flex items-center justify-center text-zinc-500">
                No valuation history found
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                  <div className="bg-zinc-900 rounded-2xl p-5 border border-white/5">
                    <p className="text-zinc-400 mb-2">Current Value</p>
                    <p className="text-2xl font-black">
                      {formatEuroRaw(valuations.current_value)}
                    </p>
                  </div>

                  <div className="bg-zinc-900 rounded-2xl p-5 border border-white/5">
                    <p className="text-zinc-400 mb-2">Peak Value</p>
                    <p className="text-2xl font-black">
                      {formatEuroRaw(valuations.peak_value)}
                    </p>
                  </div>
                </div>

                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={valuations.history}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: "#a1a1aa", fontSize: 12 }}
                      />
                      <YAxis
                        tickFormatter={(value) => formatEuroRaw(value)}
                        tick={{ fill: "#a1a1aa", fontSize: 12 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#09090b",
                          border: "1px solid rgba(255,255,255,0.1)",
                          borderRadius: "16px",
                          color: "#fff",
                        }}
                        formatter={(value) => [
                          formatEuroRaw(value),
                          "Market Value",
                        ]}
                        labelFormatter={(label) => `Date: ${label}`}
                      />
                      <Line
                        type="monotone"
                        dataKey="market_value"
                        stroke="#22d3ee"
                        strokeWidth={4}
                        dot={false}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </div>

          <div className="mt-10 bg-black/40 rounded-3xl p-8 border border-white/5">
            <div className="mb-8">
              <h2 className="text-3xl font-black">Career Transfer History</h2>
              <p className="text-zinc-400 mt-2">
                Club moves ordered by latest transfer date
              </p>
            </div>

            {transfersLoading ? (
              <div className="h-40 flex items-center justify-center text-zinc-400 animate-pulse">
                Loading transfer history...
              </div>
            ) : transfers.length === 0 ? (
              <div className="h-40 flex items-center justify-center text-zinc-500">
                No transfer history found
              </div>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-white/5">
                <div className="min-w-[980px]">
                  <div className="grid grid-cols-[110px_130px_minmax(220px,1fr)_minmax(220px,1fr)_150px_170px] bg-zinc-950/90 px-5 py-3 text-xs font-bold uppercase tracking-wide text-zinc-500">
                    <div>Season</div>
                    <div>Date</div>
                    <div>From Club</div>
                    <div>To Club</div>
                    <div>Market Value</div>
                    <div>Transfer Fee / Type</div>
                  </div>

                  <div className="divide-y divide-white/5">
                    {transfers.map((transfer) => (
                      <div
                        key={transfer.id}
                        className="grid grid-cols-[110px_130px_minmax(220px,1fr)_minmax(220px,1fr)_150px_170px] items-center px-5 py-4 text-sm text-zinc-300 transition-colors hover:bg-white/[0.03]"
                      >
                        <div className="font-semibold text-zinc-100">
                          {formatText(transfer.transfer_season)}
                        </div>

                        <div className="text-zinc-400">
                          {formatContractDate(transfer.transfer_date)}
                        </div>

                        {renderClubCell(
                          transfer.from_club_name,
                          transfer.from_club_country,
                          transfer.from_club_logo_url,
                        )}

                        {renderClubCell(
                          transfer.to_club_name,
                          transfer.to_club_country,
                          transfer.to_club_logo_url,
                        )}

                        <div className="font-semibold text-zinc-100">
                          {formatTransferMoney(transfer.market_value_in_eur)}
                        </div>

                        <div className="font-semibold text-cyan-300">
                          {formatTransferFee(transfer)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-4 mt-10">
            <div className="bg-black/40 rounded-3xl p-6 border border-white/5">
              <h2 className="text-2xl font-bold mb-6">Performance 24/25</h2>

              <div className="space-y-4 text-zinc-300">
                <div className="flex justify-between">
                  <span>Matches</span>
                  <span>{formatInteger(player.matches)}</span>
                </div>

                <div className="flex justify-between">
                  <span>Goals</span>
                  <span>{formatInteger(player.goals)}</span>
                </div>

                <div className="flex justify-between">
                  <span>Assists</span>
                  <span>{formatInteger(player.assists)}</span>
                </div>

                <div className="flex justify-between">
                  <span>Minutes</span>
                  <span>{formatInteger(player.minutes_played)}</span>
                </div>

                <div className="flex justify-between">
                  <span>Goals / 90</span>
                  <span>{formatDecimal(player.goals_per_90)}</span>
                </div>

                <div className="flex justify-between">
                  <span>Assists / 90</span>
                  <span>{formatDecimal(player.assists_per_90)}</span>
                </div>

                <div className="flex justify-between">
                  <span>Min / Goal</span>
                  <span>{formatDecimal(player.minutes_per_goal, 1)}</span>
                </div>

                <div className="flex justify-between">
                  <span>Yellow Cards</span>
                  <span>{formatInteger(player.yellow_cards)}</span>
                </div>

                <div className="flex justify-between">
                  <span>Red Cards</span>
                  <span>{formatInteger(player.red_cards)}</span>
                </div>

              </div>
            </div>

            <div className="bg-black/40 rounded-3xl p-6 border border-white/5">
              <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <h2 className="text-2xl font-bold">Advanced Stats 24/25</h2>
                <span className="w-fit rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase text-cyan-300">
                  {POSITION_GROUP_LABELS[positionGroup]}
                </span>
              </div>

              {advancedStatsLoading ? (
                <div className="flex h-40 items-center justify-center text-zinc-400 animate-pulse">
                  Loading advanced stats...
                </div>
              ) : (
                <div className="space-y-4 text-zinc-300">
                  {advancedStatFields.map((field) => (
                    <div
                      key={field.key}
                      className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-white/5 pb-3 last:border-b-0 last:pb-0"
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        <span className="truncate">{field.label}</span>
                        <StatInfoTooltip
                          title={field.label}
                          description={field.description}
                        />
                      </span>
                      <span className="text-right font-semibold text-zinc-100">
                        {field.value}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-black/40 rounded-3xl p-6 border border-white/5">
              <h2 className="text-2xl font-bold mb-6">Risk Analysis</h2>

              <div className="space-y-4 text-zinc-300">
                <div className="flex justify-between">
                  <span>Injury Days</span>
                  <span>{formatValue(player.injury_days)}</span>
                </div>

                <div className="flex justify-between">
                  <span>Age Risk</span>
                  <span>
                    {player.age ? (player.age > 30 ? "High" : "Low") : "-"}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span>Consistency</span>
                  <span>
                    {player.matches
                      ? player.matches >= 25
                        ? "Good"
                        : "Low"
                      : "-"}
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-black/40 rounded-3xl p-6 border border-white/5">
              <h2 className="text-2xl font-bold mb-6">National Team</h2>

              <div className="mb-6 flex items-center gap-4">
                {nationalTeamFlagUrl && (
                  <img
                    src={nationalTeamFlagUrl}
                    alt=""
                    className="h-12 w-12 shrink-0 rounded-full border border-white/10 bg-zinc-900 object-cover"
                  />
                )}

                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
                    Nationality
                  </p>
                  <p className="truncate text-lg font-black text-zinc-100">
                    {formatKnownText(player.nationality)}
                  </p>
                </div>
              </div>

              <div className="space-y-4 text-zinc-300">
                {nationalTeamFields.map((field) => (
                  <div
                    key={field.label}
                    className="flex justify-between gap-4"
                  >
                    <span>{field.label}</span>
                    <span className="text-right font-semibold text-zinc-100">
                      {field.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-10 bg-black/40 rounded-3xl p-8 border border-white/5">
            <div className="mb-8">
              <h2 className="text-3xl font-black">Similar Players</h2>
              <p className="text-zinc-400 mt-2">
                Position, profile, market value and performance similarity
              </p>
            </div>

            {similarPlayersLoading ? (
              <div className="h-40 flex items-center justify-center text-zinc-400 animate-pulse">
                Loading similar players...
              </div>
            ) : similarPlayers.length === 0 ? (
              <div className="h-40 flex items-center justify-center text-zinc-500">
                No similar players found
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                {similarPlayers.map((similarPlayer) => (
                  <Link
                    key={similarPlayer.id}
                    to={`/player/${similarPlayer.id}`}
                    className="group rounded-2xl border border-white/5 bg-zinc-950/70 p-4 transition-colors hover:border-cyan-400/30 hover:bg-white/[0.04]"
                  >
                    <div className="flex items-start gap-4">
                      <img
                        src={
                          similarPlayer.image_url &&
                          similarPlayer.image_url !== "https://..."
                            ? similarPlayer.image_url
                            : "https://placehold.co/100x100/111111/ffffff?text=Player"
                        }
                        alt={similarPlayer.name}
                        className="h-16 w-16 rounded-2xl bg-zinc-900 object-cover"
                      />

                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <h3 className="truncate font-black text-white group-hover:text-cyan-300">
                              {similarPlayer.name}
                            </h3>
                            <p className="mt-1 truncate text-sm text-zinc-500">
                              {similarPlayer.club || "-"}
                            </p>
                          </div>

                          <span className="shrink-0 rounded-full bg-cyan-400/10 px-2 py-1 text-xs font-black text-cyan-300">
                            {similarPlayer.similarity}% Match
                          </span>
                        </div>

                        <div className="mt-4 flex items-center justify-between gap-3 text-sm">
                          <span className="truncate text-zinc-400">
                            {similarPlayer.position || "-"}
                          </span>
                          <span className="font-bold text-zinc-100">
                            {formatMoney(similarPlayer.market_value_m)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {(playerScoreResult || playerScoreLoading || playerScoreError) && (
            <div className="mt-10 rounded-3xl border border-white/5 bg-black/40 p-8">
              <div className="mb-8">
                <p className="text-xs font-bold uppercase text-cyan-300">
                  Club-independent
                </p>
                <h2 className="mt-2 text-3xl font-black">Player Score</h2>
              </div>

              {playerScoreLoading && (
                <div className="text-zinc-400 animate-pulse">
                  Calculating player score...
                </div>
              )}

              {playerScoreError && (
                <div className="rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm font-semibold text-red-200">
                  {playerScoreError}
                </div>
              )}

              {playerScoreResult && (
                <div className="space-y-5">
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div className="rounded-2xl border border-white/5 bg-zinc-950/70 p-5">
                      <p className="text-sm text-zinc-400">Player Score</p>
                      <p
                        className={`mt-2 text-4xl font-black ${getScoreTextClass(
                          playerScoreResult.player_score,
                        )}`}
                      >
                        {playerScoreResult.player_score ?? "-"}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/5 bg-zinc-950/70 p-5">
                      <p className="text-sm text-zinc-400">Grade</p>
                      <p className="mt-2 text-2xl font-black text-zinc-100">
                        {playerScoreResult.grade || "-"}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/5 bg-zinc-950/70 p-5">
                      <p className="text-sm text-zinc-400">Profile</p>
                      <p className="mt-2 text-lg font-black text-zinc-100">
                        {playerScoreResult.player?.position || "-"}
                      </p>
                      <p className="mt-1 text-sm text-zinc-500">
                        {playerScoreResult.player?.age
                          ? `${playerScoreResult.player.age} years old`
                          : "-"}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/5 bg-zinc-950/70 p-5">
                    <p className="mb-2 text-sm font-bold uppercase text-zinc-500">
                      Summary
                    </p>
                    <p className="leading-7 text-zinc-300">
                      {playerScoreResult.summary || "-"}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="rounded-2xl border border-emerald-400/15 bg-emerald-500/5 p-5">
                      <h3 className="mb-4 text-lg font-black text-emerald-300">
                        Strengths
                      </h3>
                      <div className="space-y-3 text-sm text-zinc-300">
                        {(playerScoreResult.strengths || []).map((item) => (
                          <p key={item}>{item}</p>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-2xl border border-amber-400/15 bg-amber-500/5 p-5">
                      <h3 className="mb-4 text-lg font-black text-amber-300">
                        Risks
                      </h3>
                      <div className="space-y-3 text-sm text-zinc-300">
                        {(playerScoreResult.risks || []).map((item) => (
                          <p key={item}>{item}</p>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {isScenarioModalOpen &&
            createPortal(
            <div
              className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden px-3 py-5"
            >
              <div
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                onMouseDown={closeTransferScenarioModal}
              />
              <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="transfer-scenario-title"
                className="relative z-10 w-[92vw] max-w-[720px] overflow-visible rounded-2xl border border-cyan-400/20 bg-zinc-950/95 shadow-2xl shadow-black/60"
                onMouseDown={(event) => event.stopPropagation()}
              >
                <div className="flex shrink-0 items-start justify-between gap-4 border-b border-white/10 px-5 py-4 sm:px-6">
                  <div>
                    <p className="text-xs font-bold uppercase text-cyan-300">
                      Transfer Scenario
                    </p>
                    <h2
                      id="transfer-scenario-title"
                      className="mt-2 text-2xl font-black text-white sm:text-3xl"
                    >
                      Analyze Target Club Fit
                    </h2>
                  </div>

                  <button
                    type="button"
                    onClick={closeTransferScenarioModal}
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-sm font-black text-zinc-300 transition-colors hover:bg-white/10"
                    aria-label="Close transfer scenario modal"
                  >
                    X
                  </button>
                </div>

                <div className="overflow-visible px-5 py-5 sm:px-6">
                <form onSubmit={analyzeTransferScenario} className="space-y-4 rounded-2xl border border-white/10 bg-black/30 p-4">
                  <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-zinc-300">
                      Target Club
                    </span>
                    <div className="relative">
                      <input
                        value={scenarioTargetClub}
                        onChange={(event) => {
                          setScenarioTargetClub(event.target.value);
                          setSelectedScenarioClub(null);
                          setScenarioError("");
                          setScenarioResult(null);
                        }}
                        placeholder="Barcelona, Arsenal, Manchester City..."
                        className="w-full rounded-2xl border border-white/10 bg-black/40 px-4 py-4 text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-cyan-400/60"
                      />

                      {(clubSuggestionsLoading ||
                        clubSuggestions.length > 0 ||
                        (scenarioTargetClub.trim().length >= 2 &&
                          !selectedScenarioClub)) && (
                        <div className="custom-scrollbar absolute left-0 right-0 top-full z-50 mt-2 max-h-[220px] overflow-y-auto rounded-xl border border-cyan-500/20 bg-[#050707] shadow-lg shadow-black/40">
                          {clubSuggestionsLoading ? (
                            <div className="px-4 py-3 text-sm text-zinc-400">
                              Searching clubs...
                            </div>
                          ) : clubSuggestions.length > 0 ? (
                            clubSuggestions.map((club) => (
                              <button
                                key={club.club_id}
                                type="button"
                                onClick={() => {
                                  setSelectedScenarioClub(club);
                                  setScenarioTargetClub(club.club_name);
                                  setClubSuggestions([]);
                                  setScenarioError("");
                                  setScenarioResult(null);
                                }}
                                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-white/5"
                              >
                                {club.logo_url && (
                                  <img
                                    src={club.logo_url}
                                    alt=""
                                    className="h-8 w-8 shrink-0 rounded-full bg-zinc-900 object-contain"
                                  />
                                )}
                                <span className="min-w-0 flex-1">
                                  <span className="block truncate font-semibold text-zinc-100">
                                    {club.club_name}
                                  </span>
                                  <span className="block truncate text-xs text-zinc-500">
                                    {[club.league, club.country]
                                      .filter(Boolean)
                                      .join(" • ") || "-"}
                                  </span>
                                </span>
                              </button>
                            ))
                          ) : (
                            <div className="px-4 py-3 text-sm text-zinc-500">
                              No target club found
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    {isScenarioCurrentClubTarget && (
                      <span className="mt-2 block text-sm font-semibold text-amber-300">
                        Player is already at this club.
                      </span>
                    )}
                  </label>

                  <div className="flex flex-col gap-3 sm:flex-row">
                    <button
                      type="submit"
                      disabled={isScenarioAnalyzeDisabled}
                      className="scout-primary-button flex flex-1 items-center justify-center gap-2 rounded-2xl px-6 py-4 font-black transition-colors disabled:opacity-50"
                    >
                      {scenarioLoading && (
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-black/20 border-t-black" />
                      )}
                      {scenarioLoading ? "Analyzing..." : "Analyze"}
                    </button>
                    <button
                      type="button"
                      onClick={analyzeTransferScenarioAi}
                      disabled={isScenarioAnalyzeDisabled}
                      className="scout-secondary-button flex flex-1 items-center justify-center gap-2 rounded-2xl px-6 py-4 font-black transition-colors disabled:opacity-50"
                    >
                      {scenarioAiLoading && (
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-200/20 border-t-cyan-200" />
                      )}
                      {scenarioAiLoading ? "AI Analyzing..." : "AI Analyze"}
                    </button>
                  </div>
                </form>

                {scenarioError && (
                  <div
                    className={`mt-5 rounded-2xl border px-4 py-3 text-sm font-semibold ${
                      isScenarioErrorWarning
                        ? "border-amber-400/20 bg-amber-500/10 text-amber-200"
                        : "border-red-400/20 bg-red-500/10 text-red-200"
                    }`}
                  >
                    {scenarioError}
                  </div>
                )}

                {!scenarioResult && !scenarioLoading && !scenarioAiLoading && (
                  <div className="mt-5 rounded-2xl border border-cyan-400/10 bg-cyan-400/5 px-4 py-4 text-sm text-zinc-400">
                    Choose a target club to evaluate transfer fit.
                  </div>
                )}

                {(scenarioLoading || scenarioAiLoading) && (
                  <div className="mt-5 rounded-2xl border border-cyan-400/15 bg-black/30 p-5">
                    <div className="flex items-center gap-3 text-sm font-semibold text-cyan-200">
                      <span className="h-5 w-5 animate-spin rounded-full border-2 border-cyan-300/20 border-t-cyan-300" />
                      Analyzing transfer fit...
                    </div>
                    <div className="mt-5 space-y-3">
                      <div className="h-4 w-2/3 animate-pulse rounded-full bg-white/10" />
                      <div className="h-4 w-full animate-pulse rounded-full bg-white/10" />
                      <div className="h-4 w-4/5 animate-pulse rounded-full bg-white/10" />
                    </div>
                  </div>
                )}

                {scenarioResult && (
                  <div className="custom-scrollbar mt-6 max-h-[50vh] space-y-5 overflow-y-auto pr-1">
                    <div className="rounded-2xl border border-cyan-400/15 bg-black/40 p-5">
                      <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
                        <div className="flex shrink-0 flex-col items-center justify-center text-center">
                          <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
                            Fit Score
                          </p>
                          <div
                            className={`mt-3 flex h-28 w-28 items-center justify-center rounded-full border border-cyan-400/20 bg-cyan-400/10 text-5xl font-black ${getScoreTextClass(
                              scenarioAnalysis?.fit_score,
                            )}`}
                          >
                            {scenarioAnalysis?.fit_score ?? "-"}
                          </div>
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-black uppercase tracking-wide text-zinc-200">
                              {scenarioAnalysis?.grade || "-"}
                            </span>
                            {scenarioSourceBadge && (
                              <span
                                className={`rounded-full border px-3 py-1 text-xs font-black uppercase tracking-wide ${scenarioSourceBadge.className}`}
                              >
                                {scenarioSourceBadge.label}
                              </span>
                            )}
                          </div>
                          <h3 className="mt-3 truncate text-2xl font-black text-white">
                            {scenarioClubName || "-"}
                          </h3>
                          <p className="mt-1 text-sm text-zinc-500">
                            {scenarioClubLeague || "-"}
                          </p>
                        </div>
                      </div>
                    </div>

                    {scenarioResult.source === "fallback" && (
                      <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-200">
                        AI unavailable, deterministic fallback used.
                      </div>
                    )}

                    {scenarioSubScores && (
                      <div className="rounded-2xl border border-white/5 bg-black/40 p-5">
                        <p className="text-sm font-bold uppercase tracking-wide text-zinc-500">
                          Sub Scores
                        </p>
                        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                          {scenarioSubScoreItems.map(({ key, label, value }) => {
                            const hasValue =
                              value !== null &&
                              value !== undefined &&
                              value !== "";

                            return (
                              <div
                                key={key}
                                className="rounded-xl border border-white/5 bg-zinc-950/70 p-4"
                              >
                                <div className="mb-3 flex items-center justify-between gap-3">
                                  <span className="text-sm font-semibold text-zinc-200">
                                    {label}
                                  </span>
                                  <span
                                    className={`text-sm font-black ${getScoreTextClass(
                                      value,
                                    )}`}
                                  >
                                    {hasValue ? formatInteger(value) : "-"}
                                  </span>
                                </div>
                                <div className="h-2 overflow-hidden rounded-full bg-white/10">
                                  <div
                                    className={`h-full rounded-full ${getScoreBarClass(value)}`}
                                    style={{
                                      width: hasValue
                                        ? getScoreBarWidth(value)
                                        : "0%",
                                    }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    <div className="rounded-2xl border border-white/5 bg-black/40 p-5">
                      <p className="text-sm font-bold uppercase tracking-wide text-zinc-500">
                        AI Report
                      </p>
                      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                        {scenarioReportItems.map(([label, value]) => (
                          <div
                            key={label}
                            className={`rounded-xl border border-white/5 bg-zinc-950/70 p-4 ${
                              label === "Summary" ? "md:col-span-2" : ""
                            }`}
                          >
                            <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
                              {label}
                            </p>
                            <p className="mt-2 text-sm leading-6 text-zinc-200">
                              {value || "-"}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {scenarioMissingDataNotes.length > 0 && (
                      <div className="rounded-2xl border border-amber-400/15 bg-amber-500/5 px-4 py-3 text-sm text-amber-100/80">
                        <p className="font-bold uppercase tracking-wide text-amber-200">
                          Missing Data Notes
                        </p>
                        <div className="mt-2 space-y-2">
                          {scenarioMissingDataNotes.map((item) => (
                            <p key={item}>{item}</p>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/5 p-5">
                        <h3 className="mb-4 text-lg font-black text-emerald-300">
                          Strengths
                        </h3>
                        <div className="space-y-3 text-sm text-zinc-300">
                          {(scenarioAnalysis?.strengths || []).length > 0 ? (
                            (scenarioAnalysis?.strengths || []).map((item) => (
                              <p key={item}>{item}</p>
                            ))
                          ) : (
                            <p>-</p>
                          )}
                        </div>
                      </div>

                      <div className="rounded-2xl border border-amber-400/20 bg-red-500/5 p-5">
                        <h3 className="mb-4 text-lg font-black text-amber-300">
                          Risks
                        </h3>
                        <div className="space-y-3 text-sm text-zinc-300">
                          {(scenarioAnalysis?.risks || []).length > 0 ? (
                            (scenarioAnalysis?.risks || []).map((item) => (
                              <p key={item}>{item}</p>
                            ))
                          ) : (
                            <p>-</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                </div>
              </div>
            </div>,
            document.body,
          )}

          {(score || loadingAi) && (
            <div className="mt-10 bg-black/40 rounded-3xl p-8 border border-cyan-500/20">
              <h2 className="text-3xl font-black mb-6">AI Scout Report</h2>

              {loadingAi && (
                <div className="text-zinc-400 animate-pulse">
                  AI scout analysis is generating...
                </div>
              )}

              {score && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-zinc-900 rounded-2xl p-5">
                    <p className="text-zinc-400 mb-2">Performance</p>
                    <p className="text-3xl font-bold">
                      {score.scores.performance}
                    </p>
                  </div>

                  <div className="bg-zinc-900 rounded-2xl p-5">
                    <p className="text-zinc-400 mb-2">Tactical</p>
                    <p className="text-3xl font-bold">
                      {score.scores.tactical_fit}
                    </p>
                  </div>

                  <div className="bg-zinc-900 rounded-2xl p-5">
                    <p className="text-zinc-400 mb-2">Financial</p>
                    <p className="text-3xl font-bold">
                      {score.scores.financial}
                    </p>
                  </div>

                  <div className="bg-zinc-900 rounded-2xl p-5">
                    <p className="text-zinc-400 mb-2">Risk</p>
                    <p className="text-3xl font-bold">{score.scores.risk}</p>
                  </div>
                </div>
              )}

              {aiReport && (
                <div className="text-zinc-300 leading-8 whitespace-pre-line text-lg">
                  {aiReport}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PlayerPage;
