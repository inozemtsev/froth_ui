from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
import os
import json
import rtsp
import cv2
import base64
import time

app = FastAPI()

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'
CAMERAS_FILE = 'cameras.json'
SERVER_URL = '104.236.90.59:55155'

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
    return templates.TemplateResponse('result.html', {'name': name, 'server_url': SERVER_URL, 'id': camera_id, 'request': request})


@app.websocket("/cameras/{camera_id}/ws")
async def ws_endpoint(websocket: WebSocket, camera_id: str):
    await websocket.accept()
    url = cameras[camera_id]['url']
    
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    while cap.isOpened():
        ret, frame = cap.read()
        retval, buffer = cv2.imencode('.jpg', frame)
        encoded = str(base64.b64encode(buffer))[2:-1]

        await websocket.send_json({'data': encoded})
    
    # finally:
    #     cap.release()