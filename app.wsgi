import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/home/siidcul/ukdis/")

from app import server as application
