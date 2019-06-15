import logging
from colorlog import ColoredFormatter


def setup_logger() -> logging.getLogger():
    """Return a logger with a default ColoredFormatter."""
    formatter = ColoredFormatter(
        "{white}{asctime} - {blue}{module:^20s}{white} - | {log_color}"
        "{levelname:10s}{reset} {message_log_color}<<  {message:^69s}  >>  ",
        style='{',
        datefmt='%H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        },
        secondary_log_colors={
            'message': {
                'DEBUG': 'bold_cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        }
    )

    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger


def main():
    """Create and use a logger."""
    logger = setup_logger()

    logger.debug('a debug message')
    logger.info('an info message')
    logger.warning('a warning message')
    logger.error('an error message')
    logger.critical('a critical message')


# setup_logger()

if __name__ == '__main__':
    main()
