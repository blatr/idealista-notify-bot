#!/usr/bin/env python3
"""Unified launcher for both web app and Telegram bot."""

import subprocess
import sys
import signal
import os

def main():
    """Launch both services."""
    processes = []

    # Start web app
    webapp_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    processes.append(webapp_proc)
    print("Started web app on http://localhost:8000")

    # Start bot
    bot_proc = subprocess.Popen(
        [sys.executable, "bot.py"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    processes.append(bot_proc)
    print("Started Telegram bot")

    def cleanup(signum, frame):
        print("\nShutting down...")
        for proc in processes:
            proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Wait for any process to exit
    try:
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        cleanup(None, None)


if __name__ == "__main__":
    main()
