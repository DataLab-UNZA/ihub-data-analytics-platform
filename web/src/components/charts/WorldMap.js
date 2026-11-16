import Link from 'next/link';
import { cx } from '@/lib/format';

/**
 * Simplified world map with one link per collaborating country.
 *
 * @param {Array<{name: string, x: string, y: string, large?: boolean}>} pins Positions as percentages.
 * @param {string} href Destination for each pin.
 * @param {boolean} wide Centre the map in a wider panel.
 */
export default function WorldMap({ pins, href, wide = false }) {
  return (
    <div className={cx('map', wide && 'map--wide')}>
      {/* The map is decorative; the pins carry the information. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="map__img" src="/img/world-map.svg" alt="" width="640" height="398" loading="lazy" />
      {pins.map((pin) => (
        <Link
          className={cx('map__pin', pin.large && 'map__pin--large')}
          key={pin.name}
          href={href}
          style={{ '--x': pin.x, '--y': pin.y }}
          aria-label={pin.label ?? pin.name}
        >
          <span className="map__dot" />
        </Link>
      ))}
    </div>
  );
}
