# DSpace (IRIMS) OAI-PMH fixtures

`identify.xml`, `list_records_page1.xml`, `list_records_page2.xml` and `list_sets.xml`
were **recorded** from UNZA's IRIMS (DSpace-CRIS) at
`https://rims.unza.ac.zm/server/oai/request` on November 11, 2026, then trimmed:

- page 1 keeps its first three records and the real resumption token (`oai_dc////100`);
- page 2 keeps one record and one deleted record, and ends with an empty token;
- `completeListSize` was changed from 8792 to 5 to match the trimmed pages, because the
  harvester checks the number of records received against it;
- `list_sets.xml` keeps the first three sets and drops its resumption token.

`no_records_match.xml` and `cannot_disseminate_format.xml` are hand-made, standard OAI-PMH
error replies (the live repository does not produce them on request).

To record them again:

```bash
E=https://rims.unza.ac.zm/server/oai/request
curl -s "$E?verb=Identify" > identify.xml
curl -s "$E?verb=ListSets" > list_sets.xml
curl -s "$E?verb=ListRecords&metadataPrefix=oai_dc" > list_records_page1.xml
curl -s "$E?verb=ListRecords&resumptionToken=oai_dc////100" > list_records_page2.xml
```
