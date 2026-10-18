#!/bin/bash
# High-Priority Wi-Fi Failover & Preemption Watchdog
# Priority 1: SRIGANESH_AP (Autoconnect Priority 100)
# Priority 2: Moto g96 5g  (Autoconnect Priority 50)
# Priority 3: BEST         (Autoconnect Priority 10)

PRIO_1="SRIGANESH_AP"
PRIO_2="Moto g96 5g"
FALLBACK="BEST"
TARGET="8.8.8.8"

FAIL_COUNT=0
FAIL_LIMIT=3
CHECK_PRIO1_COUNTER=0

while true; do
    # Get active connection name and device state
    ACTIVE=$(nmcli -t -f NAME,TYPE,DEVICE connection show --active 2>/dev/null | grep ':802-11-wireless:' | cut -d: -f1 | head -n1)
    DEV_STATE=$(nmcli -t -f DEVICE,STATE device 2>/dev/null | grep '^wlan0:' | cut -d: -f2)

    # 1. PREEMPTION: If on fallback (Moto g96 5g or BEST), check if Priority 1 (SRIGANESH_AP) is in range
    if [ "$ACTIVE" != "$PRIO_1" ]; then
        CHECK_PRIO1_COUNTER=$((CHECK_PRIO1_COUNTER + 1))
        # Check every 4 seconds
        if [ "$CHECK_PRIO1_COUNTER" -ge 4 ]; then
            CHECK_PRIO1_COUNTER=0
            if nmcli -t -f SSID dev wifi list 2>/dev/null | grep -Fqx "$PRIO_1"; then
                echo "[Watchdog] Priority 1 ($PRIO_1) detected in range. Preempting back to Priority 1..."
                if nmcli connection up "$PRIO_1" --wait 8 &>/dev/null; then
                    FAIL_COUNT=0
                    sleep 2
                    continue
                fi
            fi
        fi
    fi

    # 2. HEALTH CHECK
    if [ "$DEV_STATE" = "connected" ] && [ -n "$ACTIVE" ]; then
        if ping -c 1 -W 1 "$TARGET" &>/dev/null; then
            FAIL_COUNT=0
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    elif [[ "$DEV_STATE" =~ ^connecting ]]; then
        # Association / DHCP in progress, allow it to complete
        FAIL_COUNT=0
    else
        # Disconnected or failed state
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    # 3. FAILOVER TRIGGER
    if [ "$FAIL_COUNT" -ge "$FAIL_LIMIT" ]; then
        echo "[Watchdog] Connection unhealthy on '$ACTIVE' (state='$DEV_STATE', fail=$FAIL_COUNT). Triggering failover..."
        
        if [ "$ACTIVE" = "$PRIO_1" ]; then
            echo "[Watchdog] Priority 1 down. Switching instantly to Priority 2 ($PRIO_2)..."
            if ! nmcli connection up "$PRIO_2" --wait 8 &>/dev/null; then
                echo "[Watchdog] Priority 2 failed, falling back to $FALLBACK..."
                nmcli connection up "$FALLBACK" --wait 8 &>/dev/null
            fi
        elif [ "$ACTIVE" = "$PRIO_2" ]; then
            echo "[Watchdog] Priority 2 down. Checking Priority 1 ($PRIO_1)..."
            if ! nmcli connection up "$PRIO_1" --wait 8 &>/dev/null; then
                echo "[Watchdog] Priority 1 unavailable, falling back to $FALLBACK..."
                nmcli connection up "$FALLBACK" --wait 8 &>/dev/null
            fi
        else
            echo "[Watchdog] Attempting connection in priority order ($PRIO_1 -> $PRIO_2)..."
            if ! nmcli connection up "$PRIO_1" --wait 8 &>/dev/null; then
                if ! nmcli connection up "$PRIO_2" --wait 8 &>/dev/null; then
                    nmcli connection up "$FALLBACK" --wait 8 &>/dev/null
                fi
            fi
        fi
        
        FAIL_COUNT=0
        CHECK_PRIO1_COUNTER=0
        sleep 2
    fi

    sleep 1
done
