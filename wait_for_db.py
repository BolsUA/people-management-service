import time
import socket
import os

def wait_for_db(host: str, port: int):
    while True:
        try:
            # Try to establish a socket connection to the database
            with socket.create_connection((host, port), timeout=5):
                print("Database connection established!")
                return
        except (OSError, ConnectionRefusedError):
            print("Waiting for database connection...")
            time.sleep(5)

if __name__ == "__main__":
    # Get the database host and port from environment variables
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", 5432))

    wait_for_db(db_host, db_port)
