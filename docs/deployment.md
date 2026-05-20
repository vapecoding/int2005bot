# Deployment

This project uses GitHub as the source of truth.

The correct flow is:

1. Change files locally.
2. Commit the changes locally.
3. Push the commit to GitHub.
4. Deploy to the VPS by pulling the pushed commit from GitHub.

Do not copy code directly from the local machine to the server for normal deploys.

## Repository

GitHub repository:

```text
https://github.com/vapecoding/int2005bot
```

The repository is public. Secrets must never be committed.

Ignored local/server files:

```text
.env
.venv/
__pycache__/
.DS_Store
```

## Server

SSH alias:

```bash
ssh sprintbox-2005int
```

App directory:

```text
/home/botdeploy/int2005bot
```

Systemd service:

```text
int2005bot
```

Useful commands:

```bash
sudo systemctl status int2005bot
sudo journalctl -u int2005bot -f
sudo systemctl restart int2005bot
```

## Deploy

From the project directory on the local machine:

```bash
git status
git add .
git commit -m "Describe the change"
git push origin main
./scripts/deploy.sh
```

The deploy script refuses to deploy if:

- there are uncommitted local changes;
- the local `main` commit has not been pushed to GitHub.

On the server, the script:

1. fetches `origin/main` from GitHub;
2. resets the server working tree to that GitHub commit;
3. installs Python dependencies from `requirements.txt`;
4. checks `bot.py` syntax;
5. restarts the `int2005bot` service.

## First-Time Server Setup Notes

The VPS has a dedicated deploy user:

```text
botdeploy
```

The bot runs from:

```text
/home/botdeploy/int2005bot
```

The server keeps its own `.env` file with secrets. That file is not in GitHub.

