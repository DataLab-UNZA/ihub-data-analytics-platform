import { cx } from '@/lib/format';
import Card from './Card';
import Grid from './Grid';

/**
 * Single key figure.
 *
 * @param {boolean} titled Larger bold heading (used on summary strips).
 * @param {boolean} neutral Grey note instead of the green "positive" note.
 * @param {'positive'|'negative'|'neutral'} tone Colour of the note (overrides `neutral`).
 */
export function Kpi({ label, value, note, titled = false, neutral = false, tone }) {
  const noteTone = tone ?? (neutral ? 'neutral' : undefined);
  return (
    <Card as="article" className={cx('kpi', titled && 'kpi--titled')}>
      <h2 className="kpi__label">{label}</h2>
      <p className="kpi__value">{value}</p>
      <p className={cx('kpi__note', noteTone && `kpi__note--${noteTone}`)}>{note}</p>
    </Card>
  );
}

/** Row of four key figures. `items` are Kpi props. */
export default function KpiGrid({ items, titled = false, label = 'Key figures' }) {
  return (
    <Grid as="section" variant="kpi" aria-label={label}>
      {items.map((item) => (
        <Kpi key={item.label} titled={titled} {...item} />
      ))}
    </Grid>
  );
}
