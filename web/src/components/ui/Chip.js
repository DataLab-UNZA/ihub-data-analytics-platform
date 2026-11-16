/** Removable filter chip. */
export default function Chip({ children, srLabel = 'Remove', onClick }) {
  return (
    <button className="chip" type="button" onClick={onClick}>
      {children} <span aria-hidden="true">×</span>
      <span className="sr-only">{srLabel}</span>
    </button>
  );
}
