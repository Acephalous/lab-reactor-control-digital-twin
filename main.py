from typing import Dict, List
from collections import defaultdict

from fastapi import Form, Query, Request
import os
import asyncio
import mysql.connector
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from safety import AlkydSafetySystem, SafetyTempCheck
from simulation import SensorSimulator

templates = Jinja2Templates(directory="templates")

app = FastAPI()

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="lab_reactor_management"
)
mycursor = mydb.cursor(dictionary=True)

sensor_history: list[Dict] = []
safety_history: list[SafetyTempCheck] = []

safety_monitor = AlkydSafetySystem()

active_simulators: Dict[int, SensorSimulator] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(connection)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("body.html", {"request": request})

@app.get("/reactor", response_class=HTMLResponse)
def reactor(request: Request):
    cur = mydb.cursor(dictionary=True)

    cur.execute("SELECT * FROM process")
    process = cur.fetchall()
    cur.execute("SELECT * FROM stage")
    stages = cur.fetchall()
    cur.execute("SELECT * FROM control_data")
    control_data = cur.fetchall()

    cur.close()

    return templates.TemplateResponse("reactor.html", {
        "request": request,
        "process": process,
        "stages": stages,
        "control_data": control_data,
    })

@app.post("/add_process")
async def add_process(name: str = Form("..."), type: str = Form("...")):
    sql = "INSERT INTO process (name, type) VALUES (%s, %s)"
    mycursor.execute(sql, (name, type))
    mydb.commit()
    return RedirectResponse(url="/reactor", status_code=303)

@app.get("/open_process", response_class=HTMLResponse)
async def open_process(
    request: Request,
    process_id: int = Query(None),
):
    mycursor.execute("SELECT * FROM process WHERE id = %s", (process_id,))
    process = mycursor.fetchone()

    mycursor.execute("SELECT * FROM stage WHERE process_id = %s", (process_id,))
    stages = mycursor.fetchall()

    mycursor.execute("SELECT * FROM control_data WHERE stage_id IN (SELECT id FROM stage WHERE process_id = %s)", (process_id,))
    control_data = mycursor.fetchall()

    mycursor.execute("SELECT * FROM experimental_data WHERE stage_id IN (SELECT id FROM stage WHERE process_id = %s)", (process_id,))
    experimental_data = mycursor.fetchall()

    simulator = active_simulators.get(process_id)
    input_data = simulator.sensor_history if simulator else []

    return templates.TemplateResponse("process_card.html", {
        "request": request,
        "process": process,
        "stages": stages,
        "control_data": control_data,
        "experimental_data": experimental_data,
        "input_data": input_data,
    })

@app.post("/add_stage")
async def add_stage(name: str = Form("..."), process_id: int = Form(...), external_temp: float = Form(...), internal_temp: float = Form(...), duration: int = Form(...)):
    sql = "INSERT INTO stage (name, process_id) VALUES (%s, %s)"
    mycursor.execute(sql, (name, process_id))
    new_stage_id = mycursor.lastrowid

    sql = "INSERT INTO control_data (external_temp, internal_temp, duration, stage_id) VALUES (%s, %s, %s, %s)"
    mycursor.execute(sql, (external_temp, internal_temp, duration, new_stage_id))

    mydb.commit()
    return RedirectResponse(url=f"/open_process?process_id={process_id}", status_code=303)

@app.post("/delete_process")
async def delete_process(process_id: int = Form(...)):
    mycursor.execute("DELETE FROM process WHERE id = %s", (process_id,))
    mycursor.execute("DELETE FROM stage WHERE process_id = %s", (process_id,))
    mycursor.execute("DELETE FROM control_data WHERE stage_id IN (SELECT id FROM stage WHERE process_id = %s)", (process_id,))
    mycursor.execute("DELETE FROM experimental_data WHERE stage_id IN (SELECT id FROM stage WHERE process_id = %s)", (process_id,))
    mydb.commit()
    return RedirectResponse(url="/reactor", status_code=303)

@app.get("/control_data")
async def get_control_data(process_id: int):
    mycursor.execute("SELECT * FROM control_data WHERE stage_id IN (SELECT id FROM stage WHERE process_id = %s)", (process_id,))
    control_data = mycursor.fetchall()
    return control_data

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Message from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("A client disconnected.")

@app.post("/start_simulation")
async def start_sensor_simulation(request: Request):
    body = await request.json()
    process_id = int(body["process_id"])
    if process_id in active_simulators:
        active_simulators[process_id].stop()

    simulator = SensorSimulator(process_id, manager)
    active_simulators[process_id] = simulator
    asyncio.create_task(simulator.simulate())
    return {"message": "Sensor simulation started"}

@app.post("/stop_simulation")
async def stop_sensor_simulation(request: Request):
    body = await request.json()
    process_id = int(body["process_id"])
    simulator = active_simulators.pop(process_id, None)
    if simulator is None:
        return {"message": "No active simulation for this process"}
    simulator.stop()
    return {"message": "Sensor simulation stopped"}
