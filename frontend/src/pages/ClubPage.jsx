import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

const API_BASE_URL = "http://127.0.0.1:8000";

function isMissing(value) {
  return value === null || value === undefined || value === "";
}

function formatValue(value) {
  if (isMissing(value)) {
    return "-";
  }

  return value;
}

function formatInteger(value) {
  if (isMissing(value)) {
    return "-";
  }

  const numberValue = Number(value);

  if (!Number.isFinite(numberValue)) {
    return "-";
  }

  return numberValue.toLocaleString();
}

function formatDecimal(value) {
  if (isMissing(value)) {
    return "-";
  }

  const numberValue = Number(value);

  if (!Number.isFinite(numberValue)) {
    return "-";
  }

  return numberValue.toFixed(1);
}

function formatMoney(value) {
  if (isMissing(value)) {
    return "-";
  }

  const numberValue = Number(value);

  if (!Number.isFinite(numberValue) || numberValue === 0) {
    return "-";
  }

  return `€${numberValue.toFixed(2)}M`;
}

export default function ClubPage() {
  const { clubIdOrName } = useParams();
  const [club, setClub] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadClub = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(
          `${API_BASE_URL}/clubs/${encodeURIComponent(clubIdOrName)}`,
        );

        if (!response.ok) {
          throw new Error("Club not found");
        }

        const data = await response.json();
        setClub(data);
      } catch (loadError) {
        console.error(loadError);
        setClub(null);
        setError("Club could not be loaded");
      } finally {
        setLoading(false);
      }
    };

    loadClub();
  }, [clubIdOrName]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-2xl text-white">
        Loading club...
      </div>
    );
  }

  if (error || !club) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black px-6 text-white">
        <div className="rounded-3xl border border-white/10 bg-white/5 p-8 text-center">
          <p className="text-xl font-bold">{error || "Club not found"}</p>
          <Link
            to="/scouting"
            className="mt-5 inline-flex text-cyan-400 hover:text-cyan-300"
          >
            Back to Scouting
          </Link>
        </div>
      </div>
    );
  }

  const summaryCards = [
    { label: "Squad Size", value: formatInteger(club.squad_count) },
    { label: "Average Age", value: formatDecimal(club.average_age) },
    { label: "Total Market Value", value: formatMoney(club.total_market_value) },
    { label: "League", value: formatValue(club.league) },
  ];

  return (
    <div className="min-h-screen bg-black px-6 py-10 text-white">
      <div className="mx-auto max-w-7xl">
        <div className="mb-10 flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div>
            <Link
              to="/scouting"
              className="mb-6 inline-flex font-semibold text-cyan-400 hover:text-cyan-300"
            >
              ← Back to Scouting
            </Link>

            <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
              {club.logo_url ? (
                <img
                  src={club.logo_url}
                  alt={club.club_name || "Club logo"}
                  className="h-24 w-24 rounded-3xl bg-white object-contain p-3"
                />
              ) : (
                <div className="flex h-24 w-24 items-center justify-center rounded-3xl border border-white/10 bg-white/5 text-3xl font-black text-zinc-500">
                  {(club.club_name || "-").slice(0, 1)}
                </div>
              )}

              <div>
                <h1 className="text-5xl font-black">{club.club_name || "-"}</h1>

                <p className="mt-3 text-lg text-zinc-400">
                  {formatValue(club.country)} · {formatValue(club.league)}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-sm font-bold text-cyan-300">
            CLUB PROFILE
          </div>
        </div>

        <div className="mb-8 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-4">
          {summaryCards.map((card) => (
            <div
              key={card.label}
              className="rounded-3xl border border-white/10 bg-white/5 p-6"
            >
              <p className="mb-2 text-zinc-400">{card.label}</p>
              <p className="text-3xl font-black">{card.value}</p>
            </div>
          ))}
        </div>

        <div className="overflow-x-auto rounded-3xl border border-white/10 bg-white/5">
          <table className="w-full min-w-[760px]">
            <thead className="border-b border-white/10 bg-zinc-950/80">
              <tr className="text-left text-sm uppercase tracking-wide text-zinc-500">
                <th className="px-6 py-4">Player</th>
                <th className="px-6 py-4">Position</th>
                <th className="px-6 py-4">Age</th>
                <th className="px-6 py-4">Market Value</th>
              </tr>
            </thead>

            <tbody>
              {club.players?.length > 0 ? (
                club.players.map((player) => (
                  <tr
                    key={player.id}
                    className="border-b border-white/5 transition-colors last:border-b-0 hover:bg-white/[0.03]"
                  >
                    <td className="px-6 py-5">
                      <Link
                        to={`/player/${player.id}`}
                        className="flex items-center gap-4"
                      >
                        <img
                          src={
                            player.image_url && player.image_url !== "https://..."
                              ? player.image_url
                              : "https://placehold.co/80x80/111111/ffffff?text=Player"
                          }
                          alt={player.name}
                          className="h-12 w-12 rounded-xl bg-zinc-900 object-cover"
                        />

                        <span className="font-bold text-white hover:text-cyan-300">
                          {formatValue(player.name)}
                        </span>
                      </Link>
                    </td>
                    <td className="px-6 py-5 text-zinc-300">
                      {formatValue(player.position)}
                    </td>
                    <td className="px-6 py-5 text-zinc-300">
                      {formatInteger(player.age)}
                    </td>
                    <td className="px-6 py-5 font-bold text-cyan-300">
                      {formatMoney(player.market_value_m)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="px-6 py-10 text-center text-zinc-500">
                    No squad data found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
