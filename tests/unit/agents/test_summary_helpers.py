from types import SimpleNamespace


class FakeChain:
    async def ainvoke(self, _):
        return SimpleNamespace(
            content="Final answer",
            usage_metadata={
                "total_tokens": 15,
            },
        )


class FakePrompt:
    def __or__(self, _):
        return FakeChain()
