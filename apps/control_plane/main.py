from app.main import app as domain_app
from services.agent_runtime.runtime import compose_agent_runtime

app = compose_agent_runtime(domain_app)
