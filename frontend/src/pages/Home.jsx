import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function Home() {
  const [players, setPlayers] = useState([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/players")
      .then((res) => res.json())
      .then((data) => setPlayers(data))
      .catch((err) => console.error(err));
  }, []);

  const filteredPlayers = players.filter((player) =>
    player.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-6xl mx-auto px-8 py-10">
        <header className="flex items-center justify-between mb-20">
          <h1 className="text-3xl font-black tracking-tight">TRANSFER INDEX</h1>

          <div className="text-yellow-400 font-bold">Fenerbahçe Scout Mode</div>
        </header>

        <section className="text-center">
          <h2 className="text-6xl font-black mb-6">Oyuncu Ara</h2>

          <p className="text-zinc-400 mb-10">
            Fenerbahçe için transfer uygunluğunu analiz et.
          </p>

          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Oyuncu adı yaz..."
            className="w-full max-w-3xl bg-zinc-900 border border-zinc-700 rounded-2xl px-6 py-5 text-xl outline-none focus:border-yellow-500"
          />

          {search && (
            <div className="max-w-3xl mx-auto mt-6 bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden text-left">
              {filteredPlayers.map((player) => (
                <Link
                  key={player.id}
                  to={`/player/${player.id}`}
                  className="block px-6 py-4 hover:bg-zinc-800 transition"
                >
                  <div className="font-bold">{player.name}</div>
                  <div className="text-sm text-zinc-400">
                    {player.club} • {player.position} • {player.age} yaş
                  </div>
                </Link>
              ))}

              {filteredPlayers.length === 0 && (
                <div className="px-6 py-4 text-zinc-400">
                  Oyuncu bulunamadı.
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default Home;
