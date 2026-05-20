import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


class AIScoutService:
    def generate_report(self, player, score_data):
        prompt = f"""
Sen elit bir futbol scoutusun.

Oyuncu:
- İsim: {player.name}
- Pozisyon: {player.position}
- Kulüp: {player.club}
- Yaş: {player.age}
- Gol: {player.goals}
- Asist: {player.assists}
- xG: {player.xg}
- xA: {player.xa}
- Market Value: {player.market_value_m}M €
- Maaş: {player.salary_m}M €
- Sakatlık Günleri: {player.injury_days}

Transfer Index:
{score_data}

Bu oyuncunun Fenerbahçe için transfer uygunluğunu profesyonel scout gibi analiz et.
Kısa, net ve profesyonel yaz.
"""

        response = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {"role": "system", "content": "Sen profesyonel futbol scoutusun."},
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message.content