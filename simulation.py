#future simulation code
import asyncio
import json
from random import uniform
import time
from safety import AlkydSafetySystem
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import asyncio, json, time

class MQTTSimulator:
    def __init__(self, process_id: int, manager, control_data: list | None = None,
                 broker: str = "localhost"):
        self.process_id = process_id
        self.manager = manager
        self.control_data = control_data or []
        self.current_stage_index = 0
        self.stage_start_time = time.time()
        self.sensor_history: list[dict] = []
        self.safety_history: list[dict] = []
        self.safety_monitor = AlkydSafetySystem()
        self.running = False
        self._loop: asyncio.AbstractEventLoop | None = None

        self._topic = f"reactor/{process_id}/sensors"
        self._client = mqtt.Client(CallbackAPIVersion.VERSION2)
        self._client.on_message = self._on_message
        self._client.on_connect = self._on_connect
        self._client.loop_start()           
        self._client.connect(broker, 1883)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Subscribe after connection is confirmed."""
        client.subscribe(self._topic)

    def _on_message(self, client, userdata, msg):
        """Called by paho in its own thread — schedule onto the asyncio loop."""
        data = json.loads(msg.payload.decode())
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._handle(data), self._loop)

    async def _handle(self, data: dict):
        now = time.time()
        if self.control_data:
            elapsed = now - self.stage_start_time
            stage_duration = self.control_data[self.current_stage_index].get("duration", 60)
            if elapsed >= stage_duration:
                next_idx = self.current_stage_index + 1
                if next_idx >= len(self.control_data):
                    self.running = False
                    await self.manager.broadcast(json.dumps({"type": "simulation_complete"}))
                    return
                self.current_stage_index = next_idx
                self.stage_start_time = now

        data["stage"] = self.current_stage_index
        data["duration"] = int(now - self.stage_start_time)

        self.sensor_history.append(data)
        if len(self.sensor_history) > 500:
            self.sensor_history.pop(0)

        control = self.control_data[self.current_stage_index] if self.control_data else None
        safety_result = self.safety_monitor.evaluate_safety(
            internal_temp=data["internal_temp"],
            external_temp=data["external_temp"],
            av=data.get("av", 0.0),
            stage=self.current_stage_index,
            timestamp=now,
            control=control
        )

        message: dict = {"type": "sensor_update", "data": data}
        if safety_result:
            safety_dict = {
                "level": safety_result.level,
                "delta_T": safety_result.delta_temp,
                "message": safety_result.message,
                "action": safety_result.action,
                "timestamp": safety_result.timestamp,
            }
            message["safety"] = safety_dict
            self.safety_history.append(safety_dict)

        await self.manager.broadcast(json.dumps(message))

    async def simulate(self):
        self.running = True
        self._loop = asyncio.get_running_loop()
        while self.running:
            await asyncio.sleep(1)
        self._client.loop_stop()

    def stop(self):
        self.running = False
        self._client.loop_stop()

'''class SensorSimulator:
    def __init__(self, process_id: int, manager=None, control_data: list | None = None):
        self.process_id = process_id
        self.baseline_external_temp = 25.0
        self.baseline_internal_temp = 25.0
        self.running = False
        self.sensor_history: list[dict] = []
        self.safety_history: list[dict] = []
        self.safety_monitor = AlkydSafetySystem()
        self.manager = manager
        self.control_data = control_data or []
        self.current_stage_index = 0
        self.stage_start_time = time.time()

    async def simulate(self):
        self.running = True
        while self.running:
            now = time.time()
            elapsed_in_stage = now - self.stage_start_time

            if self.control_data:
                stage_duration = self.control_data[self.current_stage_index].get("duration", 60)
                if elapsed_in_stage >= stage_duration:
                    next_index = self.current_stage_index + 1
                    if next_index >= len(self.control_data):
                        self.running = False
                        if self.manager:
                            await self.manager.broadcast(json.dumps({"type": "simulation_complete"}))
                        break
                    self.current_stage_index = next_index
                    self.stage_start_time = now
                    elapsed_in_stage = 0

            stage_index = self.current_stage_index
            elapsed_time = now - self.stage_start_time
            sensor_data = {
                "external_temp": uniform(20.0, 100.0),
                "internal_temp": uniform(20.0, 100.0),
                "rpm": uniform(0, 500),
                "av": uniform(0, 100),
                "pressure": uniform(0, 10),
                "stage": stage_index,
                "duration": int(elapsed_time)
            }
            await asyncio.sleep(5) 
            self.sensor_history.append(sensor_data)
            if len(self.sensor_history) > 500:
                self.sensor_history.pop(0)
            
            stage_index = sensor_data.get("stage", 0)
            control = self.control_data[stage_index] if self.control_data and stage_index < len(self.control_data) else None
            safety_result = self.safety_monitor.evaluate_safety(
                internal_temp=sensor_data["internal_temp"],
                external_temp=sensor_data["external_temp"],
                av=sensor_data["av"] if "av" in sensor_data else 0.0,
                stage=stage_index,
                timestamp=sensor_data.get("timestamp", time.time()),
                control=control
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
        self.running = False'''