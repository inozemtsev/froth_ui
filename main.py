from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
import websockets
import os
import json
import rtsp
import cv2
import base64
import time
from collections import deque
import requests
import httpx
import random
from datetime import datetime

app = FastAPI()

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'
CAMERAS_FILE = 'cameras.json'
SERVER_URL = '104.236.90.59:55155'
API_SERVER_URL = '104.236.90.59'
API_PORT = '55156'

templates = Jinja2Templates(directory='templates')
app.mount("/static", StaticFiles(directory="static"), name="static")



with open(CAMERAS_FILE, 'r') as f:
    cameras = json.load(f)


@app.get("/", response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse('index.html', {'cameras': cameras, 'request': request})


@app.get("/result")
async def main(camera_id: str, request: Request):
    camera = cameras[str(camera_id)]
    name = camera['name']
    url = camera['url']
    client_ip = str(request.client)
    ts = str(datetime.now().timestamp())
    session = str(base64.encodebytes(bytes(client_ip + ts, encoding='utf8')))[-33:-1]
    return templates.TemplateResponse('result.html', {'name': name, 'server_url': SERVER_URL, 'id': camera_id, 'request': request, 'session': session})

async def api_request(client, endpoint, data, host='localhost', port=8999, method='post'):
    addr = f'http://{host}:{port}/{endpoint}'
    func = getattr(client, method)
    resp = await func(addr, json=data)

    return resp.json()


@app.websocket("/cameras/{camera_id}/ws/{session}")
async def ws_endpoint(websocket: WebSocket, camera_id: str):
    await websocket.accept()
    url = cameras[camera_id]['url']
    
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    try:
        num = 0
        frames = deque(maxlen=10000)
        while cap.isOpened():
            num += 1

            ret, frame = cap.read()
            retval, buffer = cv2.imencode('.jpg', frame)
            encoded = str(base64.b64encode(buffer))[2:-1]

            # if (num % 24) != 0:
            #     continue

            frames.append(encoded)

            single_image = {'image': encoded}

            async with httpx.AsyncClient() as client:
                color = await api_request(client, 'calculate_color', single_image, host=API_SERVER_URL, port=API_PORT)
                count = await api_request(client, 'calculate_count', single_image, host=API_SERVER_URL, port=API_PORT)
                status = await api_request(client, 'calculate_status', single_image, host=API_SERVER_URL, port=API_PORT)

                if len(frames) > 1:
                    last_two = {'images': [frames[-2], encoded]}
                    direction = await api_request(client, 'calculate_direction', last_two, host=API_SERVER_URL, port=API_PORT)
                    speed = await api_request(client, 'calculate_speed', last_two, host=API_SERVER_URL, port=API_PORT)
                else:
                    direction = {}
                    speed = {}

            json_resp = {
                'data': encoded,
                'color': color,
                **direction,
                **speed,
                **count,
                **status
            }
            # else:
            #     json_resp = {
            #         'data': encoded
            #     }
            await websocket.send_json(json_resp)
                
    
    finally:
        cap.release()
