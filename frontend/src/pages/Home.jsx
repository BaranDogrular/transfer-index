import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { Link } from "react-router-dom";

export default function Home() {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(false);

  // SEARCH
  const searchPlayers = async (searchTerm) => {
    if (!searchTerm.trim()) {
      setPlayers([]);
      return;
    }

    try {
      setLoading(true);

      const response = await fetch("http://127.0.0.1:8000/players");

      const data = await response.json();

      const filtered = data.players.filter((player) =>
        player.name.toLowerCase().includes(searchTerm.toLowerCase()),
      );

      setPlayers(filtered);
    } catch (error) {
      console.error("SEARCH ERROR:", error);
    } finally {
      setLoading(false);
    }
  };

  // SEARCH EFFECT
  useEffect(() => {
    const timeout = setTimeout(() => {
      searchPlayers(query);
    }, 300);

    return () => clearTimeout(timeout);
  }, [query]);

  return (
    <div className="relative min-h-screen overflow-hidden bg-black text-white">
      {/* VIDEO */}
      <video
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        className="
          absolute
          top-0
          left-0
          w-full
          h-full
          object-cover
          brightness-110
        "
      >
        <source src="/videos/stadium-night.mp4" type="video/mp4" />
      </video>

      {/* OVERLAY */}
      <div className="absolute inset-0 bg-black/45"></div>

      {/* GRADIENT */}
      <div
        className="
        absolute
        inset-0
        bg-gradient-to-b
        from-black/10
        via-black/40
        to-black/80
      "
      ></div>

      {/* NAVBAR */}
      <div
        className="
        absolute
        top-0
        left-0
        w-full
        z-20
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
                hover:text-white
                transition-colors
              "
            >
              Scouting
            </Link>

            <button
              className="
              hover:text-white
              transition-colors
            "
            >
              AI Reports
            </button>

            <button
              className="
              hover:text-white
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
        z-10
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
            bg-cyan-500/20
            text-cyan-300
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
            <span className="text-cyan-400"> Index</span>
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
                bg-black/80
                backdrop-blur-xl
                border
                border-white/10
                rounded-2xl
                overflow-hidden
                z-50
              "
              >
                {loading ? (
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
                          {player.club}
                        </p>
                      </div>

                      <span
                        className="
                        text-cyan-400
                        text-sm
                        font-semibold
                      "
                      >
                        {player.position}
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
                bg-cyan-400
                hover:bg-cyan-300
                text-black
                font-black
                transition-all
                shadow-2xl
                shadow-cyan-500/20
              "
            >
              Open Scouting Workspace
            </Link>

            <button
              className="
              px-8
              py-4
              rounded-2xl
              border
              border-white/20
              bg-white/5
              hover:bg-white/10
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
    </div>
  );
}
