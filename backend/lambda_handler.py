from mangum import Mangum
from main import app

# Lambda handler
handler = Mangum(app, lifespan="off")
