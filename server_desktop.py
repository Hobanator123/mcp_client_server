from mcp.server.fastmcp import FastMCP
import requests
from dotenv import load_dotenv
import os
import base64
import json
import time

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
refresh_token = os.getenv("REFRESH_TOKEN")
cert_path = os.getenv("CERT_PATH")
phone_device_id = os.getenv("PHONE_DEVICE_ID")
laptop_device_id = os.getenv("LAPTOP_DEVICE_ID")

mcp = FastMCP("ryan_test_server")

def get_spotify_access_token():
    token_request_url = f"https://accounts.spotify.com/api/token"

    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')

    token_request_headers = {"Authorization": f"Basic {auth_base64}"}
    token_request_body = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    response = requests.post(url=token_request_url, headers=token_request_headers, data=token_request_body, verify=cert_path)
    return json.loads(response.content).get("access_token")

@mcp.resource("config://phone_device_id")
async def get_phone_device_id() -> str:
    "Spotify device id for my phone"
    return phone_device_id

@mcp.resource("config://laptop_device_id")
async def get_laptop_device_id() -> str:
    "Spotify device id for my laptop"
    return laptop_device_id

@mcp.tool()
async def get_spotify_headers():
    "This retrieves the headers to be used for spotify requests"
    access_token = get_spotify_access_token()
    return {"Authorization": f"Bearer {access_token}"}


@mcp.tool()
async def pause_spotify_playback(headers: dict, device_id: str):
    "Pauses the playback for spotify on the given device - requires headers from get_spotify_headers()"
    spotify_pause_url= "https://api.spotify.com/v1/me/player/pause"
    response = requests.put(url=spotify_pause_url, headers=headers, data=json.dumps({"device_id": device_id}), verify=cert_path)
    if response.status_code != 204:
        # raise json.loads(response.content)
        print(response.status_code)


@mcp.tool()
async def resume_spotify_playback(headers: dict, device_id: str):
    "Resumes the playback for spotify on the given device - requires headers from get_spotify_headers()"
    spotify_resume_url= "https://api.spotify.com/v1/me/player/play"
    response = requests.put(url=spotify_resume_url, headers=headers, data=json.dumps({"device_id": device_id}), verify=cert_path)
    if response.status_code != 204:
        # raise json.loads(response.content)
        print(response.status_code)


@mcp.tool()
async def transfer_spotify_playback(headers: dict, device_id: str):
    """
        Transfers the playback for spotify from whatever device it is on to the passed device - requires headers from get_spotify_headers()
        Return 'Error - device was not found if unable to transfer'
    """
    spotify_resume_url= "https://api.spotify.com/v1/me/player"
    response = requests.put(url=spotify_resume_url, headers=headers, data=json.dumps({"device_ids": [device_id]}), verify=cert_path)
    if response.status_code == 404:
        return "Error - device was not found"
