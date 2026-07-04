from backend.app.simulation.service import SimulationService
from backend.app.storage.repository import ResultRepository


repository = ResultRepository()
simulation_service = SimulationService(repository=repository)
