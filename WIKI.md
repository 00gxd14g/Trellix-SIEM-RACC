# RACC Wiki

Welcome to the RACC (Rule & Alarm Control Center) Wiki. This documentation provides in-depth information about the system's architecture, usage, and development.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Architecture](#architecture)
3. [User Guide](#user-guide)
4. [Developer Guide](#developer-guide)

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.9+ (for manual backend setup)
- Node.js 18+ (for manual frontend setup)

### Installation
See the main [README](README.md) for detailed installation instructions.

## Architecture

RACC uses a microservices-inspired architecture:
- **Backend**: Flask-based REST API handling XML parsing, database operations, and export logic.
- **Frontend**: React application providing the user interface.
- **Database**: SQLite (default) or PostgreSQL for storing rules, alarms, and customer data.

### Key Components
- **Signature Mapping**: `backend/utils/signature_mapping.py` handles the translation of Trellix Signature IDs to Windows Event IDs.
- **XML Parsing**: `backend/utils/xml_utils.py` manages the parsing and generation of Trellix-compatible XML files.
- **Export Engine**: `backend/utils/export_utils.py` generates HTML and PDF reports using WeasyPrint and Mermaid.js.

## User Guide

### Managing Rules
- **Import**: Upload XML files containing rules.
- **Visualize**: Click on a rule to see its logic flow diagram.
- **Edit**: Modify rule properties and logic.

### Managing Alarms
- **Create**: Generate alarms from existing rules automatically.
- **Link**: Associate alarms with rules to track coverage.

### Reporting
- **Dashboard**: View high-level statistics and coverage metrics.
- **Exports**: Generate PDF or HTML reports for compliance and documentation.

## Developer Guide

### Project Structure
```
Trellix-RACC/
├── backend/
├── frontend/
├── screenshots/
└── .github/
```

### Contributing
Please read [CONTRIBUTING.md](CONTRIBUTING.md) (if available) and use the Issue Templates for reporting bugs or requesting features.
