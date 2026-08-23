from fastapi import Depends, HTTPException, status

from backend.app.ai.intent_dispatcher import IntentDispatcher
from backend.app.ai.prompt_manager import PromptManager
from backend.app.ai.quickml_client import QuickMLClient
from backend.app.ai.quickml_service import QuickMLService
from backend.app.api.dependencies import get_repository
from backend.app.core.graph.services.graph_service import GraphService
from backend.app.core.graph.services.hotspot_service import HotspotService
from backend.app.core.graph.services.network_service import NetworkService
from backend.app.core.graph.services.offender_service import OffenderService
from backend.app.core.graph.services.similarity_service import SimilarityService
from backend.app.db.catalyst import CatalystRestDatastore
from backend.app.db.in_memory import InMemoryBackendRepository


def get_quickml_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
) -> QuickMLService:
    """Construct a fully configured QuickMLService using the shared graph repository.

    If OAuth credentials are absent or misconfigured, raises HTTP 503 immediately
    rather than letting a RuntimeError propagate as HTTP 500.
    """
    try:
        datastore = CatalystRestDatastore.from_env()
    except (RuntimeError, ValueError, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"QuickML provider is not configured: {exc}",
        ) from exc

    client = QuickMLClient(
        datastore=datastore,
    )

    prompt_manager = PromptManager()

    graph_repo = repo.graph_repository

    intent_dispatcher = IntentDispatcher(
        graph_service=GraphService(graph_repo),
        hotspot_service=HotspotService(graph_repo),
        network_service=NetworkService(graph_repo),
        offender_service=OffenderService(graph_repo),
        similarity_service=SimilarityService(graph_repo),
    )

    return QuickMLService(
        client=client,
        prompt_manager=prompt_manager,
        intent_dispatcher=intent_dispatcher,
    )