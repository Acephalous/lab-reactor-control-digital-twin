import time
from dataclasses import dataclass
from typing import List

@dataclass
class SafetyTempCheck:
    level: str
    delta_temp: float
    av: float
    message: str
    action: str
    timestamp: float

class AlkydSafetySystem:
    def __init__(self):
        self.safety_checks: List[SafetyTempCheck] = []
        self.last_check_time = 0
        self.current_stage = 0
        self.current_av = 0.0

    def evaluate_safety(self, external_temp: float, internal_temp: float, stage: int, av: float, timestamp: float, control: dict| None = None) -> SafetyTempCheck:
        self.last_check_time = timestamp
        self.current_stage = stage
        self.current_av = av

        delta_temp = internal_temp - external_temp

        thresholds = {
            1: (6, 12),
            2: (8, 15),
            3: (4, 8),
        }
        warning_th, critical_th = thresholds.get(stage, (5, 10))

        issues = []

        if control:
            target_internal = control.get("internal_temp")
            if target_internal is not None:
                dev = abs(internal_temp - target_internal)
                if dev > 20:
                    issues.append(("INFO", f"Internal temp {internal_temp:.1f}°C deviates {dev:.1f}°C from setpoint {target_internal}°C", "Check heating/cooling system immediately"))
                elif dev > 10:
                    issues.append(("INFO", f"Internal temp {internal_temp:.1f}°C deviates {dev:.1f}°C from setpoint {target_internal}°C", "Adjust heating/cooling"))

        if delta_temp > critical_th:
            issues.append(("CRITICAL", f"Critical ΔT of {delta_temp:.2f}°C", "Emergency shutdown and alert operators"))
        elif delta_temp > warning_th:
            issues.append(("WARNING", f"High ΔT of {delta_temp:.2f}°C", "Increase cooling and monitor closely"))

        av_thresholds = {
            1: (80, 90),
            2: (70, 80),
        }
        if stage in av_thresholds:
            av_warn, av_crit = av_thresholds[stage]
            if av > av_crit:
                issues.append(("CRITICAL", f"Extremely high acid value of {av:.2f}", "Emergency shutdown and alert operators"))
            elif av > av_warn:
                issues.append(("WARNING", f"High acid value of {av:.2f}", "Increase cooling and monitor closely"))

        if not issues:
            return SafetyTempCheck(
                level="SAFE",
                delta_temp=delta_temp,
                message=f"Safe: ΔT {delta_temp:.2f}°C, AV {av:.2f} at stage {stage}",
                av=av,
                action="Continue normal operation",
                timestamp=timestamp
            )

        level_priority = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}
        level = max((i[0] for i in issues), key=lambda l: level_priority.get(l, 0))
        action_map = {
            "CRITICAL": "Emergency shutdown and alert operators",
            "WARNING": "Increase cooling and monitor closely",
            "INFO": "Monitor and adjust as needed",
        }
        action = action_map[level]
        message = " | ".join(i[1] for i in issues) + f" at stage {stage}"

        return SafetyTempCheck(
            level=level,
            delta_temp=delta_temp,
            message=message,
            av=av,
            action=action,
            timestamp=timestamp
        )