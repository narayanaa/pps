class ParsingStage:
    def __init__(self, parser):
        self.parser = parser

    def should_process(self, doc):
        """Default: process the document unless overridden."""
        return True

    def process(self, doc):
        """Abstract method to process the document."""
        raise NotImplementedError
