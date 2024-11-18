import asyncio
import websockets
import requests
import random
import json
from aiohttp import web

connected_clients = set()
message_queue = asyncio.Queue()

async def handle_websocket(websocket, path):
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            await message_queue.put(message)
    finally:
        connected_clients.remove(websocket)

async def handle_request():
    while True:   
        message = await message_queue.get()
        
        if isinstance(message, dict) and 'pokemon_id' in message:
            pokemon_id = message['pokemon_id']
        else:
            pokemon_id = random.randint(1, 898)
        url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
        if response.status_code == 200:
            pokemon_data = response.json()
            name = pokemon_data['name']
            height = pokemon_data['height']
            weight = pokemon_data['weight']
            sprites = pokemon_data['sprites']

            animated_sprite = sprites.get('versions', {}).get('generation-v', {}).get('black-white', {}).get('animated', {}).get('front_default')
            sprite_url = animated_sprite or sprites.get('front_default')

            result = {
                "pokeid": pokemon_id,
                "name": name,
                "height": height,
                "weight": weight,
                "sprite_url": sprite_url
            }
        else:
            result = {"error": "Erreur lors de la récupération des données du Pokémon."}

        message = json.dumps(result)

        if connected_clients:
            await asyncio.wait([asyncio.create_task(client.send(message)) for client in connected_clients])
        message_queue.task_done()

async def handle_http_request(request):
    pokemon_id=request.query.get('pokemon_id')
    if pokemon_id is not None:
        try:
            pokemon_id=int(pokemon_id)
        except ValueError:
            return web.Response(text="Invalid Pokemon ID", status=400)
        await message_queue.put({"pokemon_id": pokemon_id})
    return web.Response(text="Pokemon request successfully received")

async def main():
    websocket_server = websockets.serve(handle_websocket, "localhost", 8765)

    app = web.Application()
    app.router.add_get('/request-pokemon', handle_http_request)
    runner = web.AppRunner(app)
    await runner.setup()
    http_server = web.TCPSite(runner, 'localhost', 8080)

    await asyncio.gather(websocket_server, http_server.start(), handle_request())

asyncio.run(main())
