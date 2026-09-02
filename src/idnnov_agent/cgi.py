"""CGI entry point hosted by DSM's web stack."""
import os, sys
from .api import handle

def main():
    try: size = min(int(os.environ.get("CONTENT_LENGTH", "0")), 65537)
    except ValueError: size = 65537
    response = handle(os.environ, sys.stdin.buffer.read(size))
    labels = {200:"OK",400:"Bad Request",403:"Forbidden",405:"Method Not Allowed",413:"Payload Too Large",415:"Unsupported Media Type"}
    print(f"Status: {response.status} {labels.get(response.status, 'Error')}\r\nContent-Type: application/json\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n\r\n{response.body}", end="")

if __name__ == "__main__": main()
