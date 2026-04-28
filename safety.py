import time
from dataclasses import dataclass
from typing import List

@dataclass
class SafetyTempCheck:
    level: str
    delta_temp: float
    message: str
    action: str
    timestamp: float

class AlkydSafetySystem:
    def __init__(self):
        self.safety_checks: List[SafetyTempCheck] = []
        self.last_check_time = 0
        self.current_stage = 0

    def evaluate_temp_safety(self, external_temp: float, internal_temp: float, stage: int, timestamp: float) -> SafetyTempCheck:
        if timestamp - self.last_check_time < 10:
            return SafetyTempCheck(
                level="INFO",
                delta_temp=internal_temp - external_temp,
                message=f"Recent check at stage {self.current_stage}, skipping redundant evaluation",
                action="No action needed",
                timestamp=timestamp
            )
        
        self.last_check_time = timestamp
        self.current_stage = stage

        delta_temp = internal_temp - external_temp

        thresholds = {
            1: (6, 12),
            2: (8, 15),
            3: (4, 8),
        }
        warning_th, critical_th = thresholds.get(stage, (5, 10))

        if delta_temp > critical_th:
            return SafetyTempCheck(
                level="CRITICAL",
                delta_temp=delta_temp,
                message=f"Critical temperature difference of {delta_temp:.2f}°C at stage {stage}",
                action="Emergency shutdown and alert operators",
                timestamp=timestamp
            )
        elif delta_temp > warning_th:
            return SafetyTempCheck(
                level="WARNING",
                delta_temp=delta_temp,
                message=f"Warning: temperature difference of {delta_temp:.2f}°C at stage {stage}",
                action="Increase cooling and monitor closely",
                timestamp=timestamp
            )
        else:             
            return SafetyTempCheck(
                level="SAFE",
                delta_temp=delta_temp,
                message=f"Safe temperature difference of {delta_temp:.2f}°C at stage {stage}",
                action="Continue normal operation",
                timestamp=timestamp
            )