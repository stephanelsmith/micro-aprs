# cli/main_cli.py

import argparse
import logging
from backend import Backend

logger = logging.getLogger(__name__)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Radio Transmission CLI")
    args = parser.parse_args()  # No --carrier argument needed now

    # Initialize Backend
    backend = Backend("config.json")

    # Run Backend
    try:
        backend.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Exiting gracefully.")
        backend.shutdown()

if __name__ == "__main__":
    main()
