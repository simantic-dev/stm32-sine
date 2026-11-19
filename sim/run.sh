#!/usr/bin/env bash
# Run the unmodified stm32-sine firmware in the simulator, check the output, and draw the PNG.
# Needs `sim` on PATH (https://simantic.com) with STM32F103 support, and python3 with matplotlib for the plot.
# ELF: `make get-deps && make` in the repo root, then copy stm32_sine here as stm32_sine.elf (committed already).
set -euo pipefail
cd "$(dirname "$0")"
SIM=${SIM:-sim}
REC=$(mktemp -d)
trap 'rm -rf "$REC"' EXIT
$SIM run --scenario scenario.yaml --ascii --record "$REC" 2>&1 | grep -v "newer sim" | tee run.log
grep -qF "(usart3 → term) Set OK" run.log && echo "PASS  terminal answers set" || { echo "FAIL  terminal"; exit 1; }
! grep -qE "HardFault|panicked" run.log && echo "PASS  no HardFault/panic"
python3 plot.py "$REC" pwm.png run.log | tee measured.txt
