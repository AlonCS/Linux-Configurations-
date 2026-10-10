#!/usr/bin/python3
"""One GPU query per overlay interval; no background GPU polling."""
import subprocess
import math

def format_metrics(output):
    rows = output.strip().splitlines()
    if not rows:
        raise ValueError('No GPU data')
    fields = [v.strip() for v in rows[0].split(',')]
    if len(fields) != 4:
        raise ValueError('Unexpected GPU data')
    def number(value):
        try:
            n = float(value)
            return n if math.isfinite(n) else None
        except ValueError:
            return None
    usage, temperature, used, total = map(number, fields)
    usage_text = f'{usage:.0f}%' if usage is not None else '—'
    temperature_text = f'{temperature:.0f}°C' if temperature is not None else '—'
    return f'${{color D8DEE9}}GPU load${{alignr}}${{color 8B9DAF}}{usage_text} · {temperature_text}${{color}}'


if __name__ == '__main__':
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total',
                                 '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=0.8, check=True)
        print(format_metrics(result.stdout))
    except (OSError, subprocess.SubprocessError, ValueError):
        print('${color D8DEE9}GPU load${alignr}${color 8B969F}unavailable${color}')
