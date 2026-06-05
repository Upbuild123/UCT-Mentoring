import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import db
db.init_db()

import seed
seed.seed()
