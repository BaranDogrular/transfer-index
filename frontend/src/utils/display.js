const CLUB_NAME_OVERRIDES = {
  "Futbol Club Barcelona": "FC Barcelona",
  "Paris Saint-Germain Football Club": "Paris Saint-Germain",
  "Manchester City Football Club": "Manchester City",
  "Real Madrid Club de Futbol": "Real Madrid",
  "Real Madrid Club de Fútbol": "Real Madrid",
};

export const formatClubDisplayName = (name) => {
  if (name === null || name === undefined || name === "") {
    return "-";
  }

  const text = String(name).trim();

  if (!text || text === "-" || text.toLowerCase() === "unknown") {
    return "-";
  }

  if (CLUB_NAME_OVERRIDES[text]) {
    return CLUB_NAME_OVERRIDES[text];
  }

  return text
    .replace(/\s+Football Club$/i, "")
    .replace(/\s+Club de Futbol$/i, "")
    .replace(/\s+Club de Fútbol$/i, "")
    .replace(/\s+Futbol Club$/i, "")
    .replace(/\s+Football Association$/i, "")
    .trim();
};
