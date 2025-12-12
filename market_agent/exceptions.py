class MarketAgentError(Exception):
    pass


class DataLoadError(MarketAgentError):
    pass


class GenerationError(MarketAgentError):
    pass
