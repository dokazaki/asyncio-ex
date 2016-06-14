# asyncio-ex
Python v3.5.1 asyncio examples

Prototypes to work out management of several tasks.
Uses asyncio streams and queues.
Type hinting!
Works on Windows.

Clients:
* make persistent TCP connections and expect:
* make requests that receive responses
* receive asynchronous alert messages

Server:
* client handler puts client requests on a queue
* dummy responder processes queued requests by pausing, then returning
the request to the original sender
* dummy alert generator randomly sends messages to all connected clients
