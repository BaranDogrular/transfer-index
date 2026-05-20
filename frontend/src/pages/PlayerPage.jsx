import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

function PlayerPage() {
  const { id } = useParams();

  const [player, setPlayer] = useState(null);
  const [score, setScore] = useState(null);
  const [aiReport, setAiReport] = useState(null);
  const [loadingAi, setLoadingAi] = useState(false);

  useEffect(() => {
    fetch(`http://127.0.0.1:8000/players/${id}`)
      .then((res) => res.json())
      .then((data) => setPlayer(data))
      .catch((err) => console.error(err));
  }, [id]);

  const analyzeTransfer = async () => {
    setScore(null);
    setAiReport(null);
    setLoadingAi(true);

    const scoreResponse = await fetch(
      `http://127.0.0.1:8000/players/${id}/transfer-score`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
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
    setScore(scoreData);

    const aiResponse = await fetch(
      `http://127.0.0.1:8000/players/${id}/ai-report`,
      {
        method: "POST",
      },
    );

    const aiData = await aiResponse.json();
    setAiReport(aiData.report);
    setLoadingAi(false);
  };

  if (!player) {
    return (
      <div className="min-h-screen bg-black text-white p-10">Yükleniyor...</div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-7xl mx-auto px-8 py-10">
        <Link
          to="/"
          className="text-yellow-400 font-bold hover:text-yellow-300"
        >
          ← Ana Sayfa
        </Link>

        <div className="mt-8 bg-zinc-900 border border-zinc-800 rounded-3xl p-8">
          <div className="flex justify-between items-start mb-10">
            <div>
              <h1 className="text-6xl font-black mb-3">{player.name}</h1>

              <p className="text-zinc-400 text-lg">
                {player.club} • {player.position} • {player.age} yaş
              </p>
            </div>

            <div className="bg-yellow-500 text-black px-5 py-2 rounded-full font-black">
              {player.position}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="bg-zinc-950 rounded-3xl p-6">
              <h2 className="text-2xl font-bold mb-5">Oyuncu Profili</h2>

              <div className="space-y-3 text-zinc-300">
                <p>Yaş: {player.age}</p>
                <p>Kulüp: {player.club}</p>
                <p>Pozisyon: {player.position}</p>
                <p>Piyasa Değeri: €{player.market_value_m}M</p>
                <p>Maaş: €{player.salary_m}M</p>
                <p>Kontrat: {player.contract_years_left} yıl</p>
              </div>
            </div>

            <div className="bg-zinc-950 rounded-3xl p-6">
              <h2 className="text-2xl font-bold mb-5">Performans</h2>

              <div className="space-y-3 text-zinc-300">
                <p>Maç: {player.matches}</p>
                <p>Gol: {player.goals}</p>
                <p>Asist: {player.assists}</p>
                <p>xG: {player.xg}</p>
                <p>xA: {player.xa}</p>
              </div>
            </div>

            <div className="bg-zinc-950 rounded-3xl p-6">
              <h2 className="text-2xl font-bold mb-5">Risk Analizi</h2>

              <div className="space-y-3 text-zinc-300">
                <p>Sakatlık Günü: {player.injury_days}</p>
                <p>Yaş Riski: {player.age > 30 ? "Yüksek" : "Düşük"}</p>
                <p>Maç Sürekliliği: {player.matches >= 25 ? "İyi" : "Düşük"}</p>
              </div>
            </div>
          </div>

          <button
            onClick={analyzeTransfer}
            className="mt-8 w-full bg-yellow-500 hover:bg-yellow-400 text-black font-black py-5 rounded-3xl text-xl transition"
          >
            Fenerbahçe Transfer Index Hesapla
          </button>

          {(score || loadingAi) && (
            <div className="mt-8 bg-zinc-950 border border-yellow-500/30 rounded-3xl p-8">
              <h2 className="text-3xl font-black mb-4">
                Fenerbahçe Transfer Index
              </h2>

              {score && (
                <>
                  <div className="text-7xl font-black text-yellow-400 mb-5">
                    {score.transfer_index}/100
                  </div>

                  <p className="text-red-400 mb-8 text-lg">
                    {score.risk_level}
                  </p>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-zinc-900 rounded-2xl p-5">
                      <p className="text-zinc-400 mb-2">Performans</p>
                      <p className="text-3xl font-bold">
                        {score.scores.performance}
                      </p>
                    </div>

                    <div className="bg-zinc-900 rounded-2xl p-5">
                      <p className="text-zinc-400 mb-2">Taktik Uyum</p>
                      <p className="text-3xl font-bold">
                        {score.scores.tactical_fit}
                      </p>
                    </div>

                    <div className="bg-zinc-900 rounded-2xl p-5">
                      <p className="text-zinc-400 mb-2">Finansal</p>
                      <p className="text-3xl font-bold">
                        {score.scores.financial}
                      </p>
                    </div>

                    <div className="bg-zinc-900 rounded-2xl p-5">
                      <p className="text-zinc-400 mb-2">Risk</p>
                      <p className="text-3xl font-bold">{score.scores.risk}</p>
                    </div>
                  </div>
                </>
              )}

              <div className="mt-8 bg-zinc-900 rounded-3xl p-6">
                <h3 className="text-2xl font-bold mb-4">AI Scout Yorumu</h3>

                {loadingAi && (
                  <p className="text-zinc-400">
                    AI scout raporu hazırlanıyor...
                  </p>
                )}

                {aiReport && (
                  <p className="text-zinc-300 leading-8 whitespace-pre-line">
                    {aiReport}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PlayerPage;
