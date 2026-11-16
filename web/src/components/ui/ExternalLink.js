import Link from 'next/link';

/** Link that opens in a new tab, with a hidden hint for assistive technology. */
export default function ExternalLink({ href, children }) {
  return (
    <a className="link--external" href={href} target="_blank" rel="noopener noreferrer">
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}
