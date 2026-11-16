import Link from 'next/link';

/** Step indicator for multi-step flows. `current` is 1-based. */
export default function Steps({ steps, current }) {
  return (
    <ol className="steps" aria-label="Progress">
      {steps.map((step, index) => {
        const position = index + 1;
        const isCurrent = position === current;
        return (
          <li className="steps__item" key={step.label} aria-current={isCurrent ? 'step' : undefined}>
            {position < current && step.href ? (
              <Link href={step.href}>
                {position}. {step.label}
              </Link>
            ) : (
              <>
                {position}. {step.label}
              </>
            )}
          </li>
        );
      })}
    </ol>
  );
}
