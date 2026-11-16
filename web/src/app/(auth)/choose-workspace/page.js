import AuthPage from '@/components/auth/AuthPage';
import Button from '@/components/ui/Button';
import ChoiceGroup from '@/components/ui/ChoiceGroup';

export const metadata = {
  title: 'Choose a workspace',
  description: 'Choose which organisation workspace to open.',
};

const WORKSPACES = [
  { value: 'unza', title: 'University of Zambia', description: 'Executive · Research pilot', chevron: true },
  { value: 'ministry', title: 'Ministry workspace', description: 'Analyst · Example workspace', chevron: true },
];

export default function ChooseWorkspacePage() {
  return (
    <AuthPage title="Choose a workspace" lead="Continue to an organisation you can access.">
      <form className="auth-form" action="/overview" method="get">
        <ChoiceGroup legend="Workspace" name="workspace" items={WORKSPACES} defaultValue="unza" />
        <p className="auth-form__fine mt-4">You can switch workspaces from the top bar.</p>
        <Button className="mt-12" type="submit">
          Continue
        </Button>
      </form>
    </AuthPage>
  );
}
