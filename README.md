# Health Buddy

Personal health data tracking and analysis.

> **Note**: The core of this project is autonomous AI analysis. Manual dashboard building is secondary; we leverage existing solutions for visualization to focus on the Insight Engine.

## Setup

1. Create a `.env` file from the following template:
   ```env
   CLOUDFLARE_TUNNEL_TOKEN=your_token_here
   WEBHOOK_TOKEN=your_secure_webhook_token
   DATABASE_URL=postgresql://health_user:health_pass@db:5432/health_db
   # Dashboard Auth (from health-auto-export-server)
   API_KEY=sk-your_secure_api_key
   ```
2. Deploy using Docker Compose:
   ```bash
   docker-compose up -d
   ```

## Architecture & Endpoints

This project provides two main endpoints for data ingestion from Health Auto Export:

1. **AI Insight Endpoint**: `https://your-domain.com/api/health/webhook?token=your_token`
   - Receives data for our internal `insight_engine.py` which processes results for the Digital Twin.
2. **Dashboard Endpoint**: `https://your-domain.com/api/data` (via `hae-server`)
   - Compatible with the [health-auto-export-server](https://github.com/HealthyApps/health-auto-export-server) for Grafana visualization.

## Webhook Configuration

In Health Auto Export, you can configure dual exports or switch between these based on whether you need deep analysis or visual dashboards.

## Data Format Reference

This project uses **Health Auto Export V2 JSON format**. When modifying data ingestion code, refer to the official documentation:

- [Export Format Overview](https://help.healthyapps.dev/en/health-auto-export/export-format/)
- [Workout Fields](https://help.healthyapps.dev/en/health-auto-export/export-format/workouts/)

Key conventions in V2:
- Numeric fields use a `{ "qty": number, "units": string }` wrapper (e.g. `activeEnergyBurned`, heart rate values)
- `heartRate` is an object with `min`, `avg`, `max` — each a qty/units object
- `duration` is in **seconds**
- Dates use format `yyyy-MM-dd HH:mm:ss Z` (e.g. `2024-02-06 14:30:00 -0800`)
