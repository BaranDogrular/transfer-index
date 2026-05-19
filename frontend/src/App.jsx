import { useEffect, useState } from "react";

const emptyPlayer = {
  name: "",
  age: "",
  position: "",
  club: "",
  goals: "",
  assists: "",
  matches: "",
  xg: "",
  xa: "",
  market_value_m: "",
  salary_m: "",
  injury_days: "",
  contract_years_left: "",
};

function App() {
  const [players, setPlayers] = useState([]);
  const [scores, setScores] = useState({});
  const [newPlayer, setNewPlayer] = useState(emptyPlayer);

  const fetchPlayers = () => {
    fetch("http://127.0.0.1:8000/players")
      .then((res) => res.json())
      .then((data) => setPlayers(data))
      .catch((err) => console.error(err));
  };

  useEffect(() => {
    fetchPlayers();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;

    setNewPlayer((prev) => ({
      ...prev,
      [name]: isNaN(Number(value)) || value === "" ? value : Number(value),
    }));
  };

  const createPlayer = async (e) => {
    e.preventDefault();

    await fetch("http://127.0.0.1:8000/players", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(newPlayer),
    });

    setNewPlayer(emptyPlayer);
    fetchPlayers();
  };

  const deletePlayer = async (playerId) => {
    await fetch(`http://127.0.0.1:8000/players/${playerId}`, {
      method: "DELETE",
    });

    fetchPlayers();
  };

  const analyzeTransfer = async (playerId) => {
    const response = await fetch(
      `http://127.0.0.1:8000/players/${playerId}/transfer-score`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          team_name: "Fenerbahçe",
          needed_position: "LW",
          max_market_value_m: 20,
          max_salary_m: 4,
          preferred_age_min: 22,
          preferred_age_max: 29,
        }),
      },
    );

    const data = await response.json();
    setScores((prev) => ({ ...prev, [playerId]: data }));
  };

  return (
    <div className="min-h-screen bg-black text-white p-10">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-6xl font-bold mb-10">Transfer Index</h1>

        <form
          onSubmit={createPlayer}
          className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 mb-10"
        >
          <h2 className="text-2xl font-bold mb-6">Oyuncu Ekle</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.keys(emptyPlayer).map((field) => (
              <input
                key={field}
                name={field}
                value={newPlayer[field]}
                onChange={handleChange}
                placeholder={
                  {
                    name: "Oyuncu Adı",
                    age: "Yaş",
                    position: "Pozisyon",
                    club: "Kulüp",
                    goals: "Gol",
                    assists: "Asist",
                    matches: "Maç",
                    xg: "xG",
                    xa: "xA",
                    market_value_m: "Piyasa Değeri (€M)",
                    salary_m: "Maaş (€M)",
                    injury_days: "Sakatlık Günü",
                    contract_years_left: "Kontrat Süresi",
                  }[field]
                }
                className="bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 outline-none focus:border-yellow-500"
              />
            ))}
          </div>

          <button className="mt-6 bg-yellow-500 hover:bg-yellow-400 text-black font-bold px-8 py-3 rounded-2xl">
            Oyuncu Ekle
          </button>
        </form>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {players.map((player) => (
            <div
              key={player.id}
              className="bg-zinc-900 rounded-3xl p-6 border border-zinc-800 hover:border-yellow-500 transition"
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold">{player.name}</h2>
                  <p className="text-zinc-400">{player.club}</p>
                </div>

                <div className="bg-yellow-500 text-black px-3 py-1 rounded-full font-bold">
                  {player.position}
                </div>
              </div>

              <div className="space-y-2 text-zinc-300">
                <p>Yaş: {player.age}</p>
                <p>Gol: {player.goals}</p>
                <p>Asist: {player.assists}</p>
                <p>xG: {player.xg}</p>
                <p>Piyasa Değeri: €{player.market_value_m}M</p>
                <p>Maaş: €{player.salary_m}M</p>
              </div>

              <button
                onClick={() => analyzeTransfer(player.id)}
                className="w-full mt-6 bg-yellow-500 hover:bg-yellow-400 text-black font-bold py-3 rounded-2xl transition"
              >
                Transfer Analizi
              </button>

              <button
                onClick={() => deletePlayer(player.id)}
                className="w-full mt-3 bg-red-600 hover:bg-red-500 text-white font-bold py-3 rounded-2xl transition"
              >
                Oyuncuyu Sil
              </button>

              {scores[player.id] && (
                <div className="mt-6 bg-zinc-800 rounded-2xl p-4">
                  <h3 className="text-xl font-bold mb-3">Transfer Sonucu</h3>
                  <p>Skor: {scores[player.id].transfer_index}</p>
                  <p>Risk: {scores[player.id].risk_level}</p>
                  <div className="mt-4 space-y-2 text-sm text-zinc-300">
                    <p>
                      Performans: {scores[player.id].scores.performance}/100
                    </p>
                    <p>
                      Taktik Uyum: {scores[player.id].scores.tactical_fit}/100
                    </p>
                    <p>Finansal: {scores[player.id].scores.financial}/100</p>
                    <p>Risk Skoru: {scores[player.id].scores.risk}/100</p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
