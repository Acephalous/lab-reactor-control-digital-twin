import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json, time, random, math, sys

BROKER = "localhost"
PROCESS_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1
INTERVAL = 5

STAGES = [
    {"ext": 80.0,  "int": 70.0,  "duration": 120, "rpm": 150},  # 0: heat-up
    {"ext": 180.0, "int": 170.0, "duration": 300, "rpm": 200},  # 1: alcoholysis
    {"ext": 230.0, "int": 220.0, "duration": 600, "rpm": 220},  # 2: esterification
    {"ext": 60.0,  "int": 55.0,  "duration": 180, "rpm": 100},  # 3: cool-down
]

AV_START   = 95.0
AV_END     = 8.0

ext_temp  = 25.0   
int_temp  = 24.0  
stage_idx = 0
stage_elapsed = 0.0
total_elapsed  = 0.0
total_duration = sum(s["duration"] for s in STAGES)

def noise(scale: float) -> float:
    return random.gauss(0, scale)

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))

def current_av(elapsed: float) -> float:
    """AV drops exponentially — fast at first, slow toward end."""
    t = min(elapsed / total_duration, 1.0)
    return AV_START + (AV_END - AV_START) * (1 - math.exp(-4 * t)) / (1 - math.exp(-4))

client = mqtt.Client(CallbackAPIVersion.VERSION2)
client.connect(BROKER, 1883)

print(f"Publisher started — process {PROCESS_ID}, {len(STAGES)} stages")

while stage_idx < len(STAGES):
    stage = STAGES[stage_idx]
    target_ext = stage["ext"]
    target_int = stage["int"]
    target_rpm = stage["rpm"]

    ext_temp += (target_ext - ext_temp) * 0.15 + noise(0.3)

    int_temp += (ext_temp - 3.0 - int_temp) * 0.10 + noise(0.4)

    pressure = 1.0 + (int_temp / 100.0) * 0.8 + noise(0.05)

    rpm = target_rpm + noise(3.0)

    av = current_av(total_elapsed) + noise(0.3)

    payload = json.dumps({
        "external_temp": round(ext_temp, 2),
        "internal_temp": round(int_temp, 2),
        "rpm":           round(rpm, 1),
        "av":            round(max(av, AV_END), 2),
        "pressure":      round(max(pressure, 0.1), 3),
    })

    client.publish(f"reactor/{PROCESS_ID}/sensors", payload)
    print(f"[Stage {stage_idx+1}] ext={ext_temp:.1f}°C  int={int_temp:.1f}°C  "
          f"AV={av:.1f}  P={pressure:.2f}bar  rpm={rpm:.0f}")

    time.sleep(INTERVAL)
    stage_elapsed  += INTERVAL
    total_elapsed  += INTERVAL

    if stage_elapsed >= stage["duration"]:
        stage_idx    += 1
        stage_elapsed = 0.0
        if stage_idx < len(STAGES):
            print(f"→ Advancing to stage {stage_idx + 1}")

print("All stages complete.")