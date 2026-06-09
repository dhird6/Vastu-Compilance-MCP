from app.api.deps import get_pipeline
from app.api.deps_correction import get_ghost_engine, get_layout_generator, get_corrected_layout_builder
from app.api.deps_intelligent import get_intelligent_pipeline


def pytest_runtest_setup():
    # Ensure each test gets a fresh pipeline (isolated rule/knowledge state).
    get_pipeline.cache_clear()
    get_ghost_engine.cache_clear()
    get_layout_generator.cache_clear()
    get_corrected_layout_builder.cache_clear()
    get_intelligent_pipeline.cache_clear()
