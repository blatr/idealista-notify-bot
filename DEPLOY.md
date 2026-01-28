# Deployment Guide: arcanery.org/crm

## Prerequisites
- Hetzner server with Docker installed
- Domain arcanery.org pointed to server IP in Cloudflare

## Step 1: Cloudflare DNS Setup

In Cloudflare dashboard for arcanery.org:
1. Add an **A record**: `@` → `<your-hetzner-server-ip>` (Proxied/Orange cloud)
2. SSL/TLS mode: **Full** (not Full Strict)

## Step 2: Server Setup

SSH into your Hetzner server:

```bash
# Install Docker if not already installed
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Clone or upload your project
git clone <your-repo> ~/apartment-crm
cd ~/apartment-crm

# Create .env file
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SCRAPFLY_API_KEY=your_scrapfly_key
EOF

# Create data directory
mkdir -p data
```

## Step 3: Deploy

```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d --build

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Step 4: Verify

1. Open https://arcanery.org/crm
2. You should see the Kanban board
3. Test creating a card

## Useful Commands

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f webapp
docker-compose -f docker-compose.prod.yml logs -f bot

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Stop services
docker-compose -f docker-compose.prod.yml down

# Update deployment
git pull
docker-compose -f docker-compose.prod.yml up -d --build
```

## Backup Data

The SQLite database is in `./data/listings.db`:

```bash
# Backup
cp data/listings.db data/listings.db.backup

# Or download to local machine
scp user@server:~/apartment-crm/data/listings.db ./backup/
```

## Troubleshooting

**502 Bad Gateway**:
- Check if webapp container is running: `docker ps`
- Check webapp logs: `docker-compose -f docker-compose.prod.yml logs webapp`

**Can't access /crm**:
- Verify nginx config: `docker-compose -f docker-compose.prod.yml exec nginx nginx -t`
- Check Cloudflare SSL mode is "Full"

**Bot not working**:
- Check .env file has correct tokens
- Check bot logs: `docker-compose -f docker-compose.prod.yml logs bot`
