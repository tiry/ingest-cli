
## Goal:

I want to build a CLI in python that will allows to import documents (files and meta-data) from a local filesystem to a REST API/

I want the CLI to be built using:

 - python 3 and a venv (needs to be created and activated)
 - using click as a CLI framework
 - pytest for testing
 - pyproject.toml

## Pipeline

The while import process can be seen as a multi-steps pipeline:

 - read documemnts
    - for example read rows in a CSV file
        - columns are meta-data
        - one columns can point to a file that will be loaded as Blob
 - mapping
    - at this step we want to be able to transform document one by one as needed
        - receive as input a python dict
        - return the modified python dict
 - call remove API to import the document
    - upload blob if any
    - create document

## Ingestion API

The Ingestion API that needs to be called as the last step of the pipeline is defined using the openapi manifest in openapi/insight-ingestion-merged-components.yaml.

For Authentication, we will use the clientID and ClientSecret to get an Access Token.

## Configuration:

The CLI will use a yaml configuration file that will allow to define:

 - EnvironmentID: ID of the HxI environment that connector would connect with
 - SourceID: UUID identifying the source sytstem
 - ClientID : Client ID of the HxI environment
 - ClientSecret
 - SystemIntegrationID

 - INGEST_ENDPOINT: https://ingestion.insight.experience.hyland.com/
 - AUTH_ENDPOINT = "https://auth.hyland.com/connect/token"




