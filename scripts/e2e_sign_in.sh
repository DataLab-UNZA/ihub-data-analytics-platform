#!/usr/bin/env bash
# End-to-end test of sign-in, front to back (ADR-010): Next.js -> FastAPI, real servers.
#
# Checks Google sign-in up to Google's page, email-code sign-in, RBAC (menu, admin pages,
# CSV export), an administrator changing a role, silent token refresh, sign-out and
# deactivation, My account (profile, photo, email change), and Explore, charts and dashboards: about 95 checks. Nothing is mocked; codes are read from the API's console.
#
# 1. Start the API with console mail and a throwaway user store, logging to a file:
#      IHUB_ENV=development IHUB_MAIL_TRANSPORT=console IHUB_ALLOWED_EMAIL_DOMAIN='*' \
#      IHUB_AUTH_DB_PATH=/tmp/ihub-e2e.sqlite IHUB_BOOTSTRAP_ADMINS=e2e.admin@example.org \
#      IHUB_PUBLIC_URL=http://localhost:3100 \
#        uv run uvicorn ihub.api.app:app --port 8000 > /tmp/ihub-e2e-api.log 2>&1 &
#    (Google checks need IHUB_GOOGLE_CLIENT_ID and IHUB_GOOGLE_CLIENT_SECRET as well.)
# 2. Start the front end: cd web && npm run build && npx next start -p 3100 &
# 3. Run: API_LOG=/tmp/ihub-e2e-api.log scripts/e2e_sign_in.sh
#
# Use a fresh IHUB_AUTH_DB_PATH for every run. Takes about 40 seconds.
set -u
S=$(mktemp -d); W=${WEB_URL:-http://localhost:3100}; A=${API_URL:-http://localhost:8000}
API_LOG=${API_LOG:?set API_LOG to the log file of the API}
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf "  PASS  %s\n" "$1"; }
bad()  { FAIL=$((FAIL+1)); printf "  FAIL  %s  (%s)\n" "$1" "$2"; }
check(){ if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "got '$2', want '$3'"; fi; }
has()  { if echo "$2" | grep -q -- "$3"; then ok "$1"; else bad "$1" "missing '$3'"; fi; }
hasnt(){ if echo "$2" | grep -q -- "$3"; then bad "$1" "unexpected '$3'"; else ok "$1"; fi; }
status(){ curl -s -o /dev/null -w '%{http_code}' "$@"; }
loc()  { curl -s -o /dev/null -w '%{redirect_url}' "$@"; }
code_for(){ grep -A4 "To: $1" "$API_LOG" | grep -oE '^\s+[0-9]{6}$' | tail -1 | tr -d ' '; }
cookie(){ awk -v n="$2" '$6==n {print $7}' "$1" | tail -1; }
sign_in(){ # $1 jar, $2 email
  curl -s -o /dev/null -c "$1" -b "$1" -X POST "$W/auth/email" -d "email=$2&next=/overview"
  local c; c=$(code_for "$2")
  curl -s -o /dev/null -c "$1" -b "$1" -X POST "$W/auth/email/verify" -d "code=$c"
}
MJ=$S/member.jar; AJ=$S/admin.jar; rm -f "$MJ" "$AJ"
MEMBER=e2e.member@example.org; ADMIN=e2e.admin@example.org

echo "1. Signed-out visitors"
check "/overview redirects to sign-in" "$(loc $W/overview)" "$W/login"
check "/publications keeps its return path" "$(loc "$W/publications?q=malaria")" "$W/login?next=%2Fpublications%3Fq%3Dmalaria"
check "API research route needs a token" "$(status $A/api/overview)" "401"
check "API health stays public (Cloud Run probe)" "$(status $A/api/health)" "200"
check "/healthz stays public" "$(status $W/healthz)" "200"
LOGIN=$(curl -s $W/login)
has "sign-in page offers Google" "$LOGIN" "Sign in with Google"
has "sign-in page offers an email code" "$LOGIN" "Email me a sign-in code"
hasnt "sign-in page has no password field" "$LOGIN" 'type="password"'

echo "2. Google sign-in, first leg (Next.js -> API -> Google)"
H=$(curl -s -D - -o /dev/null "$W/auth/google?next=/topics")
has "redirects the browser to Google" "$H" "location: https://accounts.google.com/o/oauth2/v2/auth"
has "uses the configured client" "$H" "client_id="
CALLBACK=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$W/auth/google/callback")
has "Google returns to <site>/auth/google/callback" "$H" "redirect_uri=$CALLBACK"
has "uses PKCE S256" "$H" "code_challenge_method=S256"
has "keeps the flow in an httpOnly cookie on /auth/google" "$(echo "$H" | grep -i 'set-cookie: ihub_oauth')" "Path=/auth/google; .*HttpOnly"
FLOW=$(echo "$H" | grep -i 'set-cookie: ihub_oauth=' | sed -E 's/.*ihub_oauth=([^;]+).*/\1/')
check "a forged state is refused" "$(loc -b "ihub_oauth=$FLOW" "$W/auth/google/callback?code=x&state=forged")" "$W/login"
check "a callback without the flow cookie is refused" "$(loc "$W/auth/google/callback?code=x&state=y")" "$W/login"
check "a cancelled Google sign-in returns to sign-in" "$(loc "$W/auth/google/callback?error=access_denied")" "$W/login"

echo "3. Email code sign-in (member)"
check "requesting a code goes to the code screen" "$(loc -c $MJ -b $MJ -X POST $W/auth/email -d "email=$MEMBER&next=/publications")" "$W/verify-code"
has "the code screen masks the address" "$(curl -s -b $MJ $W/verify-code)" "e\*\*\*\*\*\*\*\*\*@example.org"
CODE=$(code_for $MEMBER)
check "a 6-digit code was sent" "${#CODE}" "6"
WRONG=000000; [ "$CODE" = "$WRONG" ] && WRONG=111111
check "a wrong code returns to the code screen" "$(loc -c $MJ -b $MJ -X POST $W/auth/email/verify -d "code=$WRONG")" "$W/verify-code"
has "it says how many attempts are left" "$(curl -s -b $MJ $W/verify-code)" "4 attempts left"
check "a cross-site form post is refused" "$(status -b $MJ -H 'Origin: https://evil.example' -X POST $W/auth/email/verify -d "code=$CODE")" "403"
H=$(curl -s -D - -o /dev/null -c $MJ -b $MJ -X POST $W/auth/email/verify -d "code-1=${CODE:0:1}&code-2=${CODE:1:1}&code-3=${CODE:2:1}&code-4=${CODE:3:1}&code-5=${CODE:4:1}&code-6=${CODE:5:1}")
has "the right code (six boxes) signs in and returns to /publications" "$H" "location: $W/publications"
has "access token cookie is httpOnly, SameSite=Lax" "$(echo "$H" | grep -i 'set-cookie: ihub_at=')" "HttpOnly; SameSite=lax"
has "refresh token cookie is httpOnly" "$(echo "$H" | grep -i 'set-cookie: ihub_rt=')" "HttpOnly"
check "the code works only once" "$(curl -s -o /dev/null -w '%{http_code}' -X POST $A/api/auth/email/verify -H 'content-type: application/json' -d "{\"email\":\"$MEMBER\",\"code\":\"$CODE\"}")" "400"

echo "4. Signed in as a member (RBAC)"
OV=$(curl -s -b $MJ $W/overview)
has "the overview shows its headline figures" "$OV" "Total outputs"
hasnt "the overview loaded its data" "$OV" "load this data"
has "the top bar shows the user" "$OV" "$MEMBER"
has "the account page shows the role" "$(curl -s -b $MJ $W/account)" ">Member<"
has "there is an account menu" "$OV" 'aria-label="Account menu"'
hasnt "members do not see the Settings menu" "$OV" ">Settings<"
check "signed-in users skip /login" "$(loc -b $MJ $W/login)" "$W/overview"
hasnt "members get no CSV export button" "$(curl -s -b $MJ $W/publications)" "/export/publications"
check "CSV export is refused for members (API 403)" "$(status -b $MJ $W/export/publications)" "403"
check "admin pages send members to access-restricted" "$(loc -b $MJ $W/admin/users)" "$W/access-restricted"

echo "5. Administrator changes the member's role"
sign_in $AJ $ADMIN
AD=$(curl -s -b $AJ $W/admin/users)
has "the admin sees the Settings menu" "$(curl -s -b $AJ $W/overview)" ">Settings<"
has "the users page lists the member" "$AD" "$MEMBER"
has "the users page shows the RBAC table" "$AD" "users:manage"
MID=$(curl -s -H "Authorization: Bearer $(cookie $AJ ihub_at)" $A/api/admin/users | python3 -c "import json,sys; print([u['id'] for u in json.load(sys.stdin) if u['email']=='$MEMBER'][0])")
check "a cross-site role change is refused" "$(status -b $AJ -H 'Origin: https://evil.example' -X POST "$W/admin-actions/users/$MID" -d role=admin)" "403"
check "promoting the member to analyst" "$(loc -c $AJ -b $AJ -X POST "$W/admin-actions/users/$MID" -d role=analyst)" "$W/admin/users"
has "the change is confirmed" "$(curl -s -b $AJ $W/admin/users)" "is now analyst"

echo "6. Silent refresh picks up the new role"
sed -i '/\tihub_at\t/d' $MJ   # the access token "expired"
OLD_RT=$(cookie $MJ ihub_rt)
PUB=$(curl -s -c $MJ -b $MJ $W/publications)
has "the page still loads (proxy refreshed the tokens)" "$PUB" "Publications"
has "the role is now Analyst" "$(curl -s -b $MJ $W/account)" ">Analyst<"
has "analysts get the CSV export button" "$PUB" "/export/publications"
check "CSV export now works" "$(status -b $MJ $W/export/publications)" "200"
NEW_RT=$(cookie $MJ ihub_rt)
if [ -n "$NEW_RT" ] && [ "$NEW_RT" != "$OLD_RT" ]; then ok "the refresh token was rotated"; else bad "the refresh token was rotated" "unchanged"; fi

echo "7. Sign out"
check "a cross-site sign-out is refused" "$(status -b $MJ -H 'Origin: https://evil.example' -X POST $W/auth/sign-out)" "403"
check "sign out returns to /login" "$(loc -c $MJ -b $MJ -X POST $W/auth/sign-out)" "$W/login"
has "the sign-in page confirms it" "$(curl -s -b $MJ $W/login)" "You are signed out."
check "pages need sign-in again" "$(loc -b $MJ $W/overview)" "$W/login"
check "the old refresh token is revoked in the API" "$(curl -s -o /dev/null -w '%{http_code}' -X POST $A/api/auth/refresh -H 'content-type: application/json' -d "{\"refresh_token\":\"$NEW_RT\"}")" "401"

echo "8. Deactivation"
check "the admin deactivates the member" "$(loc -c $AJ -b $AJ -X POST "$W/admin-actions/users/$MID" -d status=deactivated)" "$W/admin/users"
echo "  (waiting 31 s: one code per address every 30 s)"; sleep 31
curl -s -o /dev/null -c $MJ -b $MJ -X POST $W/auth/email -d "email=$MEMBER"
C2=$(code_for $MEMBER)
check "a deactivated member cannot sign in" "$(loc -c $MJ -b $MJ -X POST $W/auth/email/verify -d "code=$C2")" "$W/verify-code"
has "and is told why" "$(curl -s -b $MJ $W/verify-code)" "deactivated"
check "an admin cannot change their own role" "$(curl -s -o /dev/null -w '%{http_code}' -X PATCH "$A/api/admin/users/$(curl -s -H "Authorization: Bearer $(cookie $AJ ihub_at)" $A/api/auth/me | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')" -H "Authorization: Bearer $(cookie $AJ ihub_at)" -H 'content-type: application/json' -d '{"role":"member"}')" "409"

echo "9. My account (profile, photo, email change)"
UJ=$S/user.jar; USER=e2e.user@example.org; NEWMAIL=e2e.renamed@example.org
sign_in $UJ $USER
ACC=$(curl -s -b $UJ $W/account)
has "the account page shows the email" "$ACC" "$USER"
has "the header has the account menu" "$(curl -s -b $UJ $W/overview)" 'aria-label="Account menu"'
has "without a photo the top bar shows initials" "$(curl -s -b $UJ $W/overview)" 'class="avatar avatar--sm"'
check "saving name and phone" "$(loc -c $UJ -b $UJ -X POST $W/account-actions/profile -d 'name=E2E Test User&phone=%2B260 97 123 4567')" "$W/account"
ACC=$(curl -s -b $UJ $W/account)
has "the details are saved" "$ACC" "Your details are saved."
has "the phone is shown" "$ACC" "+260 97 123 4567"
has "the new name is in the top bar" "$ACC" "E2E Test User"
check "a bad phone number is refused" "$(loc -c $UJ -b $UJ -X POST $W/account-actions/profile -d 'phone=call me')" "$W/account"
has "with a reason" "$(curl -s -b $UJ $W/account)" "7 to 15 digits"
python3 -c "import base64,sys; sys.stdout.buffer.write(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='))" > $S/photo.png
printf '<svg xmlns="http://www.w3.org/2000/svg"/>' > $S/fake.png
check "uploading a PNG photo" "$(loc -c $UJ -b $UJ -X POST $W/account-actions/avatar -F "photo=@$S/photo.png;type=image/png")" "$W/account"
check "the photo is served to its owner" "$(curl -s -o /dev/null -w '%{http_code} %{content_type}' -b $UJ $W/me/avatar)" "200 image/png"
check "the photo is not served to visitors" "$(loc $W/me/avatar)" "$W/login?next=%2Fme%2Favatar"
has "the top bar now shows the photo" "$(curl -s -b $UJ $W/overview)" 'src="/me/avatar?v='
hasnt "the confirmation stays on the account page" "$(curl -s -b $UJ $W/overview)" "Your photo is updated."
curl -s -o /dev/null -c $UJ -b $UJ -X POST $W/account-actions/avatar -F "photo=@$S/fake.png;type=image/png"
has "an SVG disguised as PNG is refused" "$(curl -s -b $UJ $W/account)" "PNG, JPEG or WebP"
check "a cross-site photo upload is refused" "$(status -b $UJ -H 'Origin: https://evil.example' -X POST $W/account-actions/avatar -F "photo=@$S/photo.png")" "403"
check "removing the photo" "$(loc -c $UJ -b $UJ -X POST $W/account-actions/avatar -d remove=1)" "$W/account"
check "the photo is gone" "$(status -b $UJ $W/me/avatar)" "404"
check "asking to change the email" "$(loc -c $UJ -b $UJ -X POST $W/account-actions/email -d "email=$NEWMAIL")" "$W/account#email"
has "the page asks for the code sent to the new address" "$(curl -s -b $UJ $W/account)" "sent to <strong>$NEWMAIL</strong>"
C3=$(code_for $NEWMAIL)
check "a code went to the NEW address" "${#C3}" "6"
check "confirming with the code" "$(loc -c $UJ -b $UJ -X POST $W/account-actions/email/verify -d "code=$C3")" "$W/account#email"
has "the email is changed" "$(curl -s -b $UJ $W/account)" "Your email is now $NEWMAIL"
check "taking another user's email is refused" "$(loc -c $UJ -b $UJ -X POST $W/account-actions/email -d "email=$ADMIN")" "$W/account#email"
has "with a reason" "$(curl -s -b $UJ $W/account)" "Another account already uses"

echo "10. Explore, charts and dashboards (Superset-style)"
XJ=$S/explorer.jar; sign_in $XJ e2e.explorer@example.org
has "Explore opens with RUN and SAVE" "$(curl -s -b $XJ $W/explore)" ">RUN<"
Q='{"dataset":"publications","metrics":["count"],"groupby":["year"],"row_limit":5}'
has "a member can run a query through /bff" "$(curl -s -b $XJ -X POST $W/bff/explore/query -H 'content-type: application/json' -d "$Q")" '"row_count":5'
check "a member cannot save a chart" "$(status -b $XJ -X POST $W/bff/charts -H 'content-type: application/json' -d "{\"name\":\"x\",\"viz_type\":\"bar\",\"params\":$Q}")" "403"
check "the proxy only reaches allowed API areas" "$(status -b $XJ $W/bff/admin/users)" "404"
check "a cross-site write through the proxy is refused" "$(status -b $AJ -H 'Origin: https://evil.example' -X POST $W/bff/charts -H 'content-type: application/json' -d "{\"name\":\"x\",\"viz_type\":\"bar\",\"params\":$Q}")" "403"
check "visitors cannot use the proxy" "$(status -X POST $W/bff/explore/query -H 'content-type: application/json' -d "$Q")" "307"
CH=$(curl -s -b $AJ -X POST $W/bff/charts -H 'content-type: application/json' -d "{\"name\":\"E2E chart\",\"viz_type\":\"bar\",\"params\":$Q}")
has "an admin can save a chart" "$CH" '"can_edit":true'
CID=$(echo "$CH" | python3 -c 'import json,sys; print(json.load(sys.stdin)["chart_id"])')
has "the chart list shows it" "$(curl -s -b $AJ $W/charts)" "E2E chart"
check "the saved chart opens in Explore" "$(status -b $AJ "$W/explore?chart=$CID")" "200"
BD=$(curl -s -b $AJ -X POST $W/bff/dashboards -H 'content-type: application/json' -d '{"title":"E2E board"}')
BID=$(echo "$BD" | python3 -c 'import json,sys; print(json.load(sys.stdin)["dashboard_id"])')
check "a draft dashboard is hidden from others" "$(status -b $XJ $W/bff/dashboards/$BID)" "404"
curl -s -o /dev/null -b $AJ -X PATCH $W/bff/dashboards/$BID -H 'content-type: application/json' -d "{\"published\":true,\"items\":[{\"chart_id\":\"$CID\",\"width\":6,\"height\":8}]}"
has "a published dashboard is visible to members" "$(curl -s -b $XJ $W/dashboards/$BID)" "E2E board"
check "members cannot delete it" "$(status -b $XJ -X DELETE $W/bff/dashboards/$BID)" "403"

echo
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
