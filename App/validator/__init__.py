"""布局校验器包

L1 几何(geometry) + L2 风格(style_rules) + 参数级修复(repair) + 报告门禁(report)
+ L3 视觉评审(visual_judge,可降级)。
"""
from App.validator.geometry import validate as validate_geometry
from App.validator.report import DeckReport, PageReport
from App.validator.repair import repair as repair_issues
from App.validator.style_rules import validate as validate_style
from App.validator.visual_judge import judge_deck

__all__ = ["validate_geometry", "validate_style", "repair_issues",
           "DeckReport", "PageReport", "judge_deck"]
