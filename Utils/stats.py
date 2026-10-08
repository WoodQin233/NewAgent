"""流水线统计：每步用时 + token 消耗的收集与展示。

使用方式：
    stats = RunStats()
    t0 = time.perf_counter()
    outline = analyzer.analyze(doc)
    u = analyzer.client.last_usage
    stats.record("AI大纲生成", time.perf_counter() - t0,
                 u.input_tokens, u.output_tokens, u.total_tokens)
    print(stats.summary())
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class StepStats:
    """单个流水线步骤的统计。"""

    name: str
    elapsed_sec: float
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class RunStats:
    """一次完整运行的统计，支持逐步累加并输出汇总表。"""

    steps: List[StepStats] = field(default_factory=list)

    def record(
        self,
        name: str,
        elapsed_sec: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
    ) -> None:
        """记录一步的耗时与 token 用量。"""
        self.steps.append(
            StepStats(
                name=name,
                elapsed_sec=elapsed_sec,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            )
        )

    # ── 汇总属性 ─────────────────────────────────────────────

    @property
    def total_elapsed(self) -> float:
        return sum(s.elapsed_sec for s in self.steps)

    @property
    def total_input_tokens(self) -> int:
        return sum(s.input_tokens for s in self.steps)

    @property
    def total_output_tokens(self) -> int:
        return sum(s.output_tokens for s in self.steps)

    @property
    def total_tokens(self) -> int:
        return sum(s.total_tokens for s in self.steps)

    # ── 输出 ────────────────────────────────────────────────

    def summary(self) -> str:
        """返回可读的汇总表字符串。"""
        lines: List[str] = []
        lines.append("")
        lines.append("═══ 运行统计 ═══")
        header = f"{'步骤':<14}{'耗时(s)':>10}{'输入tokens':>14}{'输出tokens':>14}{'总tokens':>12}"
        lines.append(header)
        lines.append("─" * len(header))
        for s in self.steps:
            lines.append(
                f"{s.name:<14}"
                f"{s.elapsed_sec:>10.2f}"
                f"{s.input_tokens:>14,}"
                f"{s.output_tokens:>14,}"
                f"{s.total_tokens:>12,}"
            )
        lines.append("─" * len(header))
        lines.append(
            f"{'合计':<14}"
            f"{self.total_elapsed:>10.2f}"
            f"{self.total_input_tokens:>14,}"
            f"{self.total_output_tokens:>14,}"
            f"{self.total_tokens:>12,}"
        )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()
