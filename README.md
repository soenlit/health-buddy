# Health Buddy

Personal health data tracking and analysis.

## Setup

1. Create a `.env` file from the following template:
   ```env
   CLOUDFLARE_TUNNEL_TOKEN=your_token_here
   WEBHOOK_TOKEN=your_secure_webhook_token
   DATABASE_URL=postgresql://health_user:health_pass@db:5432/health_db
   ```
2. Deploy using Docker Compose:
   ```bash
   docker-compose up -d
   ```

## Webhook Configuration

In Health Auto Export, set the URL to:
`https://your-public-domain.com/api/health/webhook?token=your_webhook_token`
