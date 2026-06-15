import { useEffect, useState } from "react";
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

function PlayerPage() {
  const { id } = useParams();

  const [player, setPlayer] = useState(null);
  const [score, setScore] = useState(null);
  const [aiReport, setAiReport] = useState(null);
  const [loadingAi, setLoadingAi] = useState(false);

  const [valuations, setValuations] = useState(null);
  const [valuationsLoading, setValuationsLoading] = useState(true);
  const [transfers, setTransfers] = useState([]);
  const [transfersLoading, setTransfersLoading] = useState(true);

  useEffect(() => {
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

  const renderClubCell = (clubName, country) => (
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
  );

  const getRecommendation = () => {
    if (!score) return null;

    const value = score.transfer_index;

    if (value >= 80) {
      return {
        label: "ELITE TARGET",
        className: "bg-green-500/20 text-green-400",
      };
    }

    if (value >= 65) {
      return {
        label: "STRONG OPTION",
        className: "bg-cyan-500/20 text-cyan-300",
      };
    }

    if (value >= 50) {
      return {
        label: "MONITOR",
        className: "bg-yellow-500/20 text-yellow-300",
      };
    }

    return {
      label: "HIGH RISK",
      className: "bg-red-500/20 text-red-400",
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

  if (!player) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center text-2xl">
        Loading player...
      </div>
    );
  }

  const recommendation = getRecommendation();
  const scoutTags = getScoutTags();

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      <div className="fixed inset-0 bg-gradient-to-br from-zinc-950 via-black to-black"></div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-10">
          <Link
            to="/scouting"
            className="text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
          >
            ← Back to Scouting
          </Link>

          <div className="px-4 py-2 rounded-full bg-cyan-500/20 text-cyan-300 text-sm font-semibold">
            AI SCOUT PROFILE
          </div>
        </div>

        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-[32px] p-10">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-10">
            <div className="flex flex-col md:flex-row md:items-center gap-8">
              <div className="w-44 h-44 rounded-3xl overflow-hidden border border-white/10 bg-zinc-900 shadow-2xl shrink-0">
                <img
                  src={
                    player.image_url && player.image_url !== "https://..."
                      ? player.image_url
                      : "https://placehold.co/400x400/111111/ffffff?text=Player"
                  }
                  alt={player.name}
                  className="w-full h-full object-cover"
                />
              </div>

              <div>
                <div className="inline-flex items-center px-4 py-2 rounded-full bg-yellow-500/20 text-yellow-300 text-sm font-semibold mb-6">
                  {player.position || "Unknown Position"}
                </div>

                <h1 className="text-5xl md:text-6xl font-black tracking-tight">
                  {player.name}
                </h1>

                <p className="mt-4 text-zinc-400 text-lg">
                  {player.club ? (
                    <Link
                      to={`/club/${encodeURIComponent(player.club)}`}
                      className="hover:text-cyan-300 transition-colors"
                    >
                      {player.club}
                    </Link>
                  ) : (
                    "Unknown Club"
                  )}{" "}
                  •{" "}
                  {player.league || "Unknown League"}
                </p>

                <div className="flex flex-wrap gap-3 mt-6">
                  <div className="px-4 py-2 rounded-2xl bg-white/5 border border-white/10 text-sm">
                    {player.nationality || "Unknown Nationality"}
                  </div>

                  <div className="px-4 py-2 rounded-2xl bg-white/5 border border-white/10 text-sm">
                    {player.height_cm ? `${player.height_cm} cm` : "-"}
                  </div>

                  <div className="px-4 py-2 rounded-2xl bg-white/5 border border-white/10 text-sm">
                    {player.preferred_foot &&
                    player.preferred_foot !== "Unknown"
                      ? `${player.preferred_foot} foot`
                      : "-"}
                  </div>
                </div>

                <div className="flex flex-wrap gap-3 mt-6">
                  {scoutTags.map((tag) => (
                    <span
                      key={tag}
                      className="px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 text-xs font-bold border border-cyan-500/20"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex flex-col items-center">
              <div className="w-64 h-64 rounded-full border-[12px] border-cyan-400 flex flex-col items-center justify-center bg-cyan-500/10 shadow-2xl shadow-cyan-500/20">
                <div className="text-7xl font-black text-cyan-300">
                  {score ? score.transfer_index : "--"}
                </div>

                <div className="mt-2 text-zinc-400 text-sm uppercase tracking-widest">
                  Transfer Index
                </div>
              </div>

              {recommendation && (
                <div
                  className={`mt-5 px-4 py-2 rounded-full text-sm font-black ${recommendation.className}`}
                >
                  {recommendation.label}
                </div>
              )}

              <button
                onClick={analyzeTransfer}
                disabled={loadingAi}
                className="mt-6 w-64 py-4 rounded-2xl bg-cyan-400 hover:bg-cyan-300 disabled:opacity-50 text-black font-black transition-all"
              >
                {loadingAi ? "Analyzing..." : "Analyze Transfer"}
              </button>

              <Link
                to={`/compare?player1_id=${player.id}`}
                className="mt-3 w-64 py-4 rounded-2xl bg-white/10 hover:bg-white/15 text-center font-black text-white transition-all"
              >
                Compare Player
              </Link>
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
                        )}

                        {renderClubCell(
                          transfer.to_club_name,
                          transfer.to_club_country,
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

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-10">
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
              <h2 className="text-2xl font-bold mb-6">Contract & Profile</h2>

              <div className="space-y-4 text-zinc-300">
                <div className="flex justify-between">
                  <span>Contract Until</span>
                  <span>
                    {formatContractDate(player.contract_expiration_date)}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span>Position</span>
                  <span>{player.position || "-"}</span>
                </div>

                <div className="flex justify-between">
                  <span>Club</span>
                  <span>
                    {player.club ? (
                      <Link
                        to={`/club/${encodeURIComponent(player.club)}`}
                        className="text-cyan-300 hover:text-cyan-200 transition-colors"
                      >
                        {player.club}
                      </Link>
                    ) : (
                      "-"
                    )}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span>Preferred Foot</span>
                  <span>{player.preferred_foot || "-"}</span>
                </div>
              </div>
            </div>
          </div>

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
