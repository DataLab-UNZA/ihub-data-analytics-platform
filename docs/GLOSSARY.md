
# Project Glossary

This glossary explains terms used throughout the iHub Data Analytics Platform.

## CI

Continuous integration (CI) automatically checks proposed changes, including formatting, linting and tests. In this project, the lint-and-test workflow runs on pull requests.

## Connector

A connector retrieves data from an external source and makes it available to the platform. Connectors are implemented in `src/ihub/connectors/` and configured in `config/sources.yml`.

## dbt

dbt (data build tool) transforms data using SQL models and tests. This project keeps its transformation models in `transform/models/`, including staging, intermediate and mart layers.

## Deployment

Deployment publishes the application to its hosting environment. The project's deployment process is documented in `DEPLOYMENT.md` and runs through GitHub Actions.

## Dimension table

A dimension table stores descriptive information used to organise and filter facts, such as a researcher or publication attribute. Dimension models belong in the dbt marts under `transform/models/marts/`.

## DOI

A Digital Object Identifier (DOI) is a persistent identifier for a digital scholarly work. DOI normalisation and related publication fields are handled in the research transformation models under `transform/models/`.

## DSpace

DSpace is a repository platform used by institutions to preserve and provide access to digital scholarly material. The project's DSpace connector belongs in `src/ihub/connectors/`, with source configuration in `config/sources.yml`.

## DuckDB

DuckDB is the analytical database used locally by the platform. The ingestion process creates `data/ihub.duckdb`, which stores data for transformations and queries.

## Fact table

A fact table records measurable events or observations and links to descriptive dimensions. Fact models are part of the analytical marts in `transform/models/marts/`.

## Intermediate

Intermediate models combine or prepare staging data for downstream marts. They are stored in `transform/models/intermediate/`.

## Mart

A mart is a curated dataset designed for analysis and reporting. The project's analytical models are stored in `transform/models/marts/`, including the research mart.

## OAI-PMH

The Open Archives Initiative Protocol for Metadata Harvesting (OAI-PMH) is a protocol for collecting repository metadata. It is relevant to the DSpace connector in `src/ihub/connectors/`.

## OJS

Open Journal Systems (OJS) is software for managing and publishing scholarly journals. Its connector belongs in `src/ihub/connectors/`, with configuration in `config/sources.yml`.

## Open access

Open access means scholarly work is available online without a subscription or payment barrier for readers. Open-access publication information is represented in research data and its models under `transform/models/`.

## ORCID iD

An ORCID iD is a persistent identifier that distinguishes a researcher from others. ORCID integration is handled by a connector in `src/ihub/connectors/` and source configuration in `config/sources.yml`.

## Raw

Raw data is the source data collected before analytical transformations. The ingestion code in `src/ihub/ingest.py` and the local database `data/ihub.duckdb` are part of this project's raw-data flow.

## Star schema

A star schema organises analytical data around a central fact table linked to dimension tables. It is used in the project's mart models in `transform/models/marts/`.

## Staging

Staging models clean and standardise source data while keeping it close to its original structure. They are stored in `transform/models/staging/`.
