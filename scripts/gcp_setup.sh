#!/usr/bin/env bash
# One-off Google Cloud set-up for the iHub Data Analytics Platform.
#
# Run once in Cloud Shell, signed in as the project owner
# (lighton.phiri@unza.ac.zm). It is safe to re-run: steps that already exist
# are skipped. Nothing secret is created or printed: GitHub Actions
# authenticates with Workload Identity Federation, so there are no
# service-account keys. See docs/DEPLOYMENT.md and ADR-002.
#
#   bash scripts/gcp_setup.sh [PROJECT_ID]
set -uo pipefail

PROJECT_ID="${1:-ihub-data-analytics-platform}"
PROJECT_NAME="iHub Data Analytics Platform"
REGION="africa-south1"            # Johannesburg, Tier 1 pricing
AR_REPO="ihub"
GITHUB_REPO="DataLab-UNZA/ihub-data-analytics-platform"
RUNTIME_SA="ihub-app-runtime"
DEPLOY_SA="github-deployer"
POOL="github"
PROVIDER="github-oidc"
BUDGET_USD=5

step() { printf '\n==> %s\n' "$*"; }

step "Billing account"
BILLING_ACCOUNT="$(gcloud billing accounts list --filter=open=true --format='value(name)' | head -n1)"
BILLING_ACCOUNT="${BILLING_ACCOUNT#billingAccounts/}"
[ -n "$BILLING_ACCOUNT" ] || { echo "No open billing account found."; exit 1; }
CURRENCY="$(gcloud billing accounts describe "$BILLING_ACCOUNT" --format='value(currencyCode)')"
echo "billing account: $BILLING_ACCOUNT ($CURRENCY)"

step "Project $PROJECT_ID"
if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME" || exit 1
fi
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT" >/dev/null
gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

step "APIs"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  cloudresourcemanager.googleapis.com billingbudgets.googleapis.com

step "Artifact Registry repository $AR_REPO (keeps the 3 newest images)"
gcloud artifacts repositories describe "$AR_REPO" --location="$REGION" >/dev/null 2>&1 ||
  gcloud artifacts repositories create "$AR_REPO" --repository-format=docker \
    --location="$REGION" --description="iHub app container images"
cat > /tmp/ihub-cleanup.json <<'JSON'
[
  {"name": "keep-3-newest", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 3}},
  {"name": "delete-older", "action": {"type": "Delete"}, "condition": {"tagState": "ANY", "olderThan": "1d"}}
]
JSON
gcloud artifacts repositories set-cleanup-policies "$AR_REPO" --location="$REGION" \
  --policy=/tmp/ihub-cleanup.json --no-dry-run >/dev/null

step "Service accounts"
for sa in "$RUNTIME_SA" "$DEPLOY_SA"; do
  gcloud iam service-accounts describe "$sa@$PROJECT_ID.iam.gserviceaccount.com" >/dev/null 2>&1 ||
    gcloud iam service-accounts create "$sa" --display-name="$sa"
done
RUNTIME_EMAIL="$RUNTIME_SA@$PROJECT_ID.iam.gserviceaccount.com"
DEPLOY_EMAIL="$DEPLOY_SA@$PROJECT_ID.iam.gserviceaccount.com"
sleep 10  # let new service accounts propagate before granting roles
for role in roles/run.admin roles/artifactregistry.writer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$DEPLOY_EMAIL" \
    --role="$role" --condition=None >/dev/null
done
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_EMAIL" \
  --member="serviceAccount:$DEPLOY_EMAIL" --role=roles/iam.serviceAccountUser >/dev/null

step "Workload Identity Federation (only $GITHUB_REPO on main)"
gcloud iam workload-identity-pools describe "$POOL" --location=global >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools create "$POOL" --location=global --display-name="GitHub Actions"
gcloud iam workload-identity-pools providers describe "$PROVIDER" --location=global \
  --workload-identity-pool="$POOL" >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --location=global \
    --workload-identity-pool="$POOL" --display-name="GitHub OIDC" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository=='$GITHUB_REPO' && assertion.ref=='refs/heads/main'"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_EMAIL" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL/attribute.repository/$GITHUB_REPO" >/dev/null

step "Budget alert"
if [ "$CURRENCY" = "USD" ]; then
  if ! gcloud billing budgets list --billing-account="$BILLING_ACCOUNT" \
       --format='value(displayName)' | grep -qx "iHub monthly budget"; then
    gcloud billing budgets create --billing-account="$BILLING_ACCOUNT" \
      --display-name="iHub monthly budget" --budget-amount="${BUDGET_USD}USD" \
      --filter-projects="projects/$PROJECT_ID" --credit-types-treatment=exclude-all-credits \
      --threshold-rule=percent=0.1 --threshold-rule=percent=0.5 \
      --threshold-rule=percent=1.0 --threshold-rule=percent=1.0,basis=forecasted-spend
  fi
else
  echo "Billing currency is $CURRENCY, not USD: create the budget in $CURRENCY instead."
fi

step "Values for GitHub repository variables"
echo "GCP_PROJECT_ID=$PROJECT_ID"
echo "GCP_REGION=$REGION"
echo "GCP_WIF_PROVIDER=projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL/providers/$PROVIDER"
echo "GCP_DEPLOY_SA=$DEPLOY_EMAIL"
echo "GCP_RUNTIME_SA=$RUNTIME_EMAIL"
echo "SETUP COMPLETE"
