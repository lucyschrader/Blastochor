import logging
# Read more about this
# https://www.loggly.com/ultimate-guide/python-logging-basics/
# https://realpython.com/python-logging/

logging.basicConfig(level=logging.DEBUG,
                    filename="src/logging/blastochor.log",
                    filemode="w",
                    format="%(asctime)s - %(name)s - %(process)d - %(levelname)s - %(message)s")

logging.debug("This is a debug message")
logging.info("This is an info message")
logging.warning("This is a warning message")
logging.error("This is an error message")
logging.critical("This is a critical message")