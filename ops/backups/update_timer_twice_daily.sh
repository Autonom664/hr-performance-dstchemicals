#!/bin/bash
set -euo pipefail

echo "Updating hr-backup timer to run twice daily (02:15 and 14:15)..."

# Update the systemd timer
sudo tee /etc/systemd/system/hr-backup.timer > /dev/null <<'EOF'
[Unit]
Description=Run HR Backup twice daily at 02:15 and 14:15

[Timer]
OnCalendar=*-*-* 02:15:00
OnCalendar=*-*-* 14:15:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Reload systemd and restart timer
sudo systemctl daemon-reload
sudo systemctl restart hr-backup.timer

echo "✅ Timer updated! Backup will now run at:"
echo "   - 02:15 (02:15 AM)"
echo "   - 14:15 (02:15 PM)"
echo ""
echo "Verifying..."
sudo systemctl list-timers hr-backup.timer
