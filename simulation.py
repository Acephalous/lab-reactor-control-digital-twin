#future simulation code
import asyncio
import json
from random import uniform
import time
from safety import AlkydSafetySystem

class SensorSimulator:
    def __init__(self, process_id: int, manager=None):
        self.process_id = process_id
        self.stage_start_time = time.time()
        self.baseline_external_temp = 25.0
        self.baseline_internal_temp = 25.0
        self.running = False
        self.sensor_history: list[dict] = []
        self.safety_history: list[dict] = []
        self.safety_monitor = AlkydSafetySystem()
        self.manager = manager

    async def simulate(self):
        self.running = True
        while self.running:
            elapsed_time = time.time() - self.stage_start_time
            sensor_data = {
                "external_temp": uniform(20.0, 100.0),
                "internal_temp": uniform(20.0, 100.0),
                "rpm": uniform(0, 500),
                "pressure": uniform(0, 10),
                "duration": int(elapsed_time)
            }
            await asyncio.sleep(5) 
            self.sensor_history.append(sensor_data)
            if len(self.sensor_history) > 500:
                self.sensor_history.pop(0)
            
            safety_result = self.safety_monitor.evaluate_temp_safety(
                internal_temp=sensor_data["internal_temp"],
                external_temp=sensor_data["external_temp"],
                stage=sensor_data.get("stage", 0),
                timestamp=sensor_data.get("timestamp", time.time())
            )            
            message = {
                "type": "sensor_update",
                "data": sensor_data
            }
            
            if safety_result:
                safety_dict = {
                    "level": safety_result.level,
                    "delta_T": safety_result.delta_temp,
                    "message": safety_result.message,
                    "action": safety_result.action,
                    "timestamp": safety_result.timestamp
                }
                message["safety"] = safety_dict
                self.safety_history.append(safety_dict)
                if len(self.safety_history) > 100:
                    self.safety_history.pop(0)
            
            if self.manager:
                await self.manager.broadcast(json.dumps(message))
    def stop(self):
        self.running = False