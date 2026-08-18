# VCO Edge APN Extraction

A Python utility that connects to a VeloCloud Orchestrator (VCO), retrieves all enterprises and their Edges, extracts the configured **APN (Access Point Name)** from cellular interfaces, and exports the results to a CSV file.

## Overview

The script follows this workflow:

```text
Connect to VCO308
      │
      ▼
Get Enterprises
      │
      ▼
For each Enterprise
      │
      ├── Get all Edges
      │
      └── For each Edge
             │
             ▼
      Get Edge Configuration
             │
             ▼
      Find deviceSettings
             │
             ▼
      Find Cellular Interface
             │
             ▼
          Extract APN
             │
        ┌────┴────┐
        ▼         ▼
    APN Found   No APN
        │         │
        ▼         ▼
   Add Result   Skip
        │
        └──────► Next Edge
                  │
                  ▼
            Write CSV
```

## What the Script Does

1. Connects to the configured **VCO308** instance.
2. Retrieves all enterprises/tenants.
3. Iterates through each enterprise.
4. Retrieves all Edges belonging to the enterprise.
5. Retrieves the configuration for each Edge.
6. Searches the configuration for `deviceSettings`.
7. Identifies the cellular interface.
8. Extracts the configured APN.
9. Adds Edges with an APN to the results.
10. Exports the collected information to a CSV file.

## Requirements

* Python 3.x
* Access to the VCO
* Valid VCO credentials
* API access to the VCO
* Network connectivity to the VCO

Install any required Python dependencies with:

```bash
pip install -r requirements.txt
```

## Configuration

Before running the script, configure the VCO connection details and authentication credentials.

Example:

```python
VCO_URL = "https://<vco-hostname>"
USERNAME = "<username>"
PASSWORD = "<password>"
```

> **Security:** Do not commit usernames, passwords, API tokens, or other credentials to GitHub. Use environment variables or another secure secrets-management mechanism.

## Output

The script generates a CSV containing the Edges where an APN was successfully identified.

Typical information may include:

| Enterprise | Edge       | Edge ID | APN         |
| ---------- | ---------- | ------: | ----------- |
| Customer A | Branch-001 |   12345 | internet    |
| Customer A | Branch-002 |   12346 | corp.apn    |
| Customer B | Site-001   |   12347 | private.apn |

Edges where no APN is configured are skipped.

## Running the Script

```bash
python <script_name>.py
```

The resulting CSV can then be opened in Excel or imported into other tools for reporting and analysis.

## Use Cases

This script can be useful for:

* Auditing cellular APN configurations
* Identifying Edges with specific APNs
* Validating APN configuration across multiple enterprises
* Generating configuration reports
* Supporting SD-WAN migration or configuration audits

## Notes

* The script processes all enterprises and Edges accessible to the authenticated user.
* Edges without a configured cellular APN are not included in the output.
* The exact configuration structure can vary between VeloCloud software versions, so API/configuration changes may require updates to the extraction logic.# Telstra_APN
