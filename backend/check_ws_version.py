import websockets
print(f"Websockets version: {websockets.version.version}")
try:
    import websockets.client
    print("websockets.client exists")
except ImportError:
    print("websockets.client does not exist")
