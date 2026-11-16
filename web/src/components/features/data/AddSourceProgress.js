import Card from '@/components/ui/Card';
import Steps from '@/components/ui/Steps';
import { ADD_SOURCE_STEPS } from '@/data/data-ops';

/** Heading card with the four-step indicator shown on every add-source screen. */
export default function AddSourceProgress({ current }) {
  return (
    <Card className="mb-24" aria-labelledby="progress-title">
      <h2 className="card__title" id="progress-title">
        Add source · {current} of {ADD_SOURCE_STEPS.length}
      </h2>
      <Steps steps={ADD_SOURCE_STEPS} current={current} />
    </Card>
  );
}
