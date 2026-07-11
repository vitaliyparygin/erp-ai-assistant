from rag_benchmark.diagnostics.models import RegexStat

class UnusedRegexAnalyzer:

    @staticmethod
    def analyze(
        regex_stats: list[RegexStat],
    ) -> list[RegexStat]:

        return [
            stat
            for stat in regex_stats
            if not stat.matched
        ]