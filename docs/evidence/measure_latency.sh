#!/usr/bin/env bash
# MO-1: 5 runs; each run = 1 warm-up request + 20 timed requests, reported as their median.
# usage: measure_latency.sh URL TOKEN
set -euo pipefail
url=$1
token=$2

for run in 1 2 3 4 5; do
    curl -s -o /dev/null -H "Authorization: Token $token" "$url"
    times=$(for _ in $(seq 20); do
        curl -s -o /dev/null -w '%{time_total}\n' -H "Authorization: Token $token" "$url"
    done | sort -n)
    median=$(echo "$times" | awk '{ t[NR] = $1 } END { printf "%.1f", (t[10] + t[11]) / 2 * 1000 }')
    min=$(echo "$times" | head -1 | awk '{ printf "%.1f", $1 * 1000 }')
    max=$(echo "$times" | tail -1 | awk '{ printf "%.1f", $1 * 1000 }')
    echo "run $run: median ${median} ms (min ${min}, max ${max}, n=20)"
done
