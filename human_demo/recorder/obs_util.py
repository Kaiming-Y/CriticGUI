"""OBS configuration comes from environment variables; stop returns the exact clip."""
import os
from pathlib import Path
from obswebsocket import obsws, requests


def connect_to_obs():
    client = obsws(os.getenv('OBS_HOST', 'localhost'), int(os.getenv('OBS_PORT', '4455')),
                   os.getenv('OBS_PASSWORD', ''))
    client.connect()
    return client


def start_recording(client):
    if client.call(requests.GetRecordStatus()).getOutputActive():
        raise RuntimeError('OBS is already recording. Stop that recording first.')
    response = client.call(requests.StartRecord())
    if not response.status:
        raise RuntimeError('OBS could not start recording')


def stop_recording(client):
    response = client.call(requests.StopRecord())
    if not response.status:
        raise RuntimeError('OBS could not stop recording')
    path = Path(response.getOutputPath())
    if not path.is_file():
        raise FileNotFoundError(f'OBS clip not accessible on this machine: {path}')
    return path


def disconnect(client):
    client.disconnect()
