from app.api.deps import get_pipeline


def pytest_runtest_setup():
    # Ensure each test gets a fresh pipeline (isolated rule/knowledge state).
    get_pipeline.cache_clear()
