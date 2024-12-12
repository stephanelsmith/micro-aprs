# cli/main_cli.py

import argparse
import logging
from backend import Backend

logger = logging.getLogger(__name__)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Radio Transmission CLI")
    parser.add_argument('--carrier', action='store_true', help="Start in carrier-only mode")
    args = parser.parse_args()

    # Initialize Backend
    backend = Backend("config.json")

    # Handle carrier-only mode if specified
    if args.carrier:
        logger.info("Starting in carrier-only mode via CLI.")
        backend.queues['message_queue'].put("CARRIER_ONLY")

    # Run Backend
    try:
        backend.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Exiting gracefully.")
        backend.shutdown()

if __name__ == "__main__":
    main()
