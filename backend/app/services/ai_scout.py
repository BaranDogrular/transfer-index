import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class AIScoutService:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv(
            "OPENROUTER_MODEL",
            "openai/gpt-3.5-turbo"
        )

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

    def generate_report(self, player, score_data):
        prompt = f"""
Sen Fenerbahçe için çalışan elit seviye bir futbol scout ve veri analistisin.

Oyuncu Bilgileri:
- İsim: {player.name}
- Yaş: {player.age}
- Pozisyon: {player.position}
- Kulüp: {player.club}
- Gol: {player.goals}
- Asist: {player.assists}
- Maç: {player.matches}
- xG: {player.xg}
- xA: {player.xa}
- Piyasa Değeri: {player.market_value_m}M €
- Maaş: {player.salary_m}M €
- Sakatlık Günleri: {player.injury_days}
- Kontrat Süresi: {player.contract_years_left} yıl

Transfer Index Sonucu:
{score_data}

Görev:
Bu oyuncuyu özellikle Fenerbahçe transferi açısından analiz et.

Başlıklar:
1. Genel Profil
2. Fenerbahçe Taktik Uyumu
3. Hücum / Savunma Katkısı
4. Finansal Risk
5. Sakatlık ve Adaptasyon Riski
6. Transfer Kararı

Kurallar:
- Türkçe yaz
- Profesyonel scout raporu gibi yaz
- Fazla uzun yazma
- Net karar ver
- Son cümlede mutlaka şu formatta karar ver:
"Sonuç: Transfer önerilir / dikkatli izlenmeli / önerilmez."
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sen profesyonel futbol scoutusun.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.7,
                max_tokens=700,
                timeout=30,
            )

            return {
                "success": True,
                "report": response.choices[0].message.content,
            }

        except Exception as e:
            print("AI SCOUT ERROR:", str(e))

            return {
                "success": False,
                "report": self.fallback_report(player),
                "error": str(e),
            }

    def fallback_report(self, player):
        return f"""
# Scout Raporu Geçici Olarak Oluşturulamadı

{player.name} için AI scout analizi şu anda üretilemiyor.

Muhtemel sebepler:
- OpenRouter kredi limiti
- API bağlantı problemi
- Model erişim problemi

Sistem fallback modunda çalışıyor.

Sonuç: dikkatli izlenmeli.
"""