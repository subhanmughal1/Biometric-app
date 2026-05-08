import os,logging
from main import DATA_DIR

class Logger:
    # Utility class for centralized application logging.
    _initialized = False
    _initialized_filename = None
    _initialized_level = None
    _file_handlers = set()

    @staticmethod
    def initialize(log_file='log.log', level=logging.INFO):
        # Initialize the logging configuration.
        filename = os.path.join(DATA_DIR, log_file)
        log_format = '%(asctime)s - %(levelname)s - %(message)s'

        if not Logger._initialized:
            logging.basicConfig(
                level=level,
                filename= filename,
                filemode='a',
                format=log_format,
            )
            Logger._initialized = True
            Logger._initialized_filename = filename
            Logger._initialized_level = level
            Logger._file_handlers.add(filename)
            return

        if filename in Logger._file_handlers:
            return

        root_logger = logging.getLogger()
        handler = logging.FileHandler(filename, mode='a')
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(handler)
        Logger._file_handlers.add(filename)

    @staticmethod
    def info(message):
        # Log an info-level message.
        logging.info(message)

    @staticmethod
    def warning(message):
        # Log a warning-level message.
        logging.warning(message)

    @staticmethod
    def error(message):
        # Log an error-level message.
        logging.error(message)

    @staticmethod
    def debug(message):
        # Log a debug-level message.
        logging.debug(message)

    @staticmethod
    def critical(message):
        # Log a critical-level message.
        logging.critical(message)
