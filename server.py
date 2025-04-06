from mcp.server.fastmcp import FastMCP
from mcp.types import Resource
from mcp.server.stdio import stdio_server
import requests
from dotenv import load_dotenv
import os
import base64
import json

from pydantic import AnyUrl

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

async def get_spotify_headers():
    "This retrieves the headers to be used for spotify requests"
    access_token = get_spotify_access_token()
    return {"Authorization": f"Bearer {access_token}"}

@mcp.resource("config://phone_device_id", name="phone_device_id", mime_type="text/plain")
async def get_phone_device_id() -> str:
    "Spotify device id for my phone"
    return phone_device_id

@mcp.resource(uri="config://laptop_device_id", name="laptop_device_id", mime_type="text/plain")
async def get_laptop_device_id() -> str:
    "Spotify device id for my laptop"
    return laptop_device_id


@mcp.tool(name="read_device_id", description="Takes in the name of a device to retrieve the spotify device ID for. Currently accepting 'laptop' or 'phone'")
async def read_device_id(device: str) -> str:
    """
    Takes in the name of a device to retrieve the spotify device ID for
    Currently accepting laptop or phone
    """
    if device == "phone":
        return await get_phone_device_id()
    elif device == "laptop":
        return await get_laptop_device_id()
    
    raise ValueError("Resource not found")


@mcp.tool()
async def pause_spotify_playback():
    "Pauses the playback for spotify on the given device - requires headers from get_spotify_headers()"
    spotify_pause_url= "https://api.spotify.com/v1/me/player/pause"
    headers = await get_spotify_headers()

    response = requests.put(url=spotify_pause_url, headers=headers, verify=cert_path)
    if response.status_code != 200:
        return json.loads(response.content)
    return True

@mcp.tool()
async def resume_spotify_playback():
    "Resumes the playback for spotify on the given device - requires headers from get_spotify_headers()"
    spotify_resume_url= "https://api.spotify.com/v1/me/player/play"
    headers = await get_spotify_headers()

    response = requests.put(url=spotify_resume_url, headers=headers, verify=cert_path)
    if response.status_code != 200:
        return json.loads(response.content)
    return True
    
@mcp.tool()
async def transfer_spotify_playback(device_id: str):
    """
        Transfers the playback for spotify from whatever device it is on to the passed device - requires headers from get_spotify_headers()
        Return 'Error - device was not found if unable to transfer'
    """
    spotify_resume_url= "https://api.spotify.com/v1/me/player"
    headers = await get_spotify_headers()

    response = requests.put(url=spotify_resume_url, headers=headers, data=json.dumps({"device_ids": [device_id]}), verify=cert_path)
    if response.status_code != 200:
        return json.loads(response.content)

if __name__ == "__main__":
    mcp.run(transport='stdio')