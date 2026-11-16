/**
 * Country names and map positions for the collaboration map.
 * Positions are approximate centroids as [longitude, latitude]; countries missing here
 * are still listed by name but get no pin.
 */
const CENTROIDS = {
  ZM: [27.8, -13.1], US: [-98.5, 39.8], GB: [-2.5, 54.0], ZA: [24.7, -29.0], AU: [134.5, -25.7],
  CN: [104.2, 35.9], IN: [78.9, 22.0], DE: [10.4, 51.2], FR: [2.2, 46.6], NL: [5.3, 52.1],
  CA: [-106.3, 56.1], BR: [-51.9, -14.2], KE: [37.9, 0.0], TZ: [34.9, -6.4], UG: [32.3, 1.4],
  MW: [34.3, -13.3], ZW: [29.2, -19.0], MZ: [35.5, -18.7], BW: [24.7, -22.3], NA: [18.5, -22.0],
  NG: [8.7, 9.1], GH: [-1.0, 7.9], ET: [40.5, 9.1], EG: [30.8, 26.8], SE: [18.6, 60.1],
  NO: [8.5, 60.5], DK: [9.5, 56.3], CH: [8.2, 46.8], BE: [4.5, 50.5], IT: [12.6, 41.9],
  ES: [-3.7, 40.5], JP: [138.3, 36.2], KR: [127.8, 35.9], TH: [100.99, 15.9], CD: [21.8, -4.0],
  RW: [29.9, -1.9], AO: [17.9, -11.2], LS: [28.2, -29.6], SZ: [31.5, -26.5], FI: [25.7, 61.9],
};

const regionNames = new Intl.DisplayNames(['en-GB'], { type: 'region' });

export function countryName(code) {
  try {
    return regionNames.of(code) ?? code;
  } catch {
    return code;
  }
}

/** Converts a country code to map pin coordinates in percent, or null when unknown. */
export function mapPosition(code) {
  const point = CENTROIDS[code];
  if (!point) {
    return null;
  }
  const [lon, lat] = point;
  const round = (value) => `${Math.round(value * 10) / 10}%`;
  return { x: round(((lon + 180) / 360) * 100), y: round(((83 - lat) / 166) * 100) };
}
