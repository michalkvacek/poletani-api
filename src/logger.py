import logging
import sys

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# Create handlers for logging to the standard output and a file
stdoutHandler = logging.StreamHandler(stream=sys.stdout)

# Set the log levels on the handlers
stdoutHandler.setLevel(logging.DEBUG)

# Create a log format using Log Record attributes
fmt = logging.Formatter(
    "%(name)s: %(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(process)d >>> %(message)s"
)

# Set the log format on each handler
stdoutHandler.setFormatter(fmt)

# Add each handler to the Logger object
log.addHandler(stdoutHandler)
