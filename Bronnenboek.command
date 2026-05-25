#!/bin/bash
# Bronnenboek — start de lokale webserver en open de browser.
# Dubbelklikbaar vanuit Finder. Sleep me naar je Dock voor één klik.

cd "$(dirname "$0")" || exit 1

# Terminal-titel netter zetten
printf '\033]0;Bronnenboek\007'

# Achtergrond: wacht tot Flask reageert, open dan de browser
(
  for _ in $(seq 1 30); do
    if curl -fsS -o /dev/null http://127.0.0.1:5001/ 2>/dev/null; then
      open "http://localhost:5001/"
      exit 0
    fi
    sleep 0.5
  done
) &

# Start de server in dit venster.
# Sluit het venster (of Ctrl-C) om de server te stoppen.
exec /usr/bin/python3 server.py
