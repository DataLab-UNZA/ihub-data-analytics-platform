# OJS fixtures

## OAI-PMH: recorded

`JABS_*.xml` and `zjh_*.xml` were **recorded** from journals.unza.zm on November 11,
2026, then trimmed:

- JABS page 1 keeps its first three records and the real resumption token; page 2
  keeps two records and the empty token that ends the list. `completeListSize` was
  changed from 174 to 5 to match, because the harvester checks the count against it.
- zjh is a single page (no resumption token), trimmed to two records.

To record them again (the site leaves an intermediate certificate out of its chain, so
pass the one kept in `config/certs/`):

```bash
CA=config/certs/sectigo-public-server-authentication-ca-dv-r36.crt
cat "$(uv run python -c 'import certifi; print(certifi.where())')" "$CA" > /tmp/ca.pem
B=https://journals.unza.zm/index.php
curl --cacert /tmp/ca.pem -s "$B/JABS/oai?verb=Identify" > JABS_identify.xml
curl --cacert /tmp/ca.pem -s "$B/JABS/oai?verb=ListRecords&metadataPrefix=oai_dc" > JABS_list_records_page1.xml
```

## REST API: hand-made

`rest_issues.json` and `rest_issue_41.json` are **hand-made** in the OJS 3 REST API
shape (`/index.php/<journal>/api/v1/issues?isPublished=true` and `issues/<id>`) for an
example journal. Every UNZA journal answers OAI-PMH, so the REST fallback is not used
today, and on November 11, 2026 the site answered 404 to the REST API for every journal.
Never save a reply that was fetched with a token in it.
