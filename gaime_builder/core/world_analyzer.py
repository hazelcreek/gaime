"""
World Analyzer - AI-powered holistic analysis of generated worlds.

Provides two analysis passes:
1. Playability Analysis: Is the game winnable and consistent?
2. Narrative Analysis: Is the story coherent and motivated?

Each pass analyzes the world holistically, then applies targeted fixes.
"""

import logging
from dataclasses import dataclass, field

from app.engine.validator import WorldValidator
from app.models.world import WorldData

logger = logging.getLogger(__name__)


@dataclass
class AnalysisIssue:
    """A single issue found during analysis"""
    severity: str  # "critical", "high", "medium", "low"
    category: str  # "playability" or "narrative"
    location: str  # e.g., "locations/cafe_alley/exits/down"
    description: str
    suggested_fix: str


@dataclass
class AnalysisResult:
    """Result of an analysis pass"""
    issues: list[AnalysisIssue] = field(default_factory=list)
    summary: str = ""

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "high")


@dataclass
class FixResult:
    """Result of an AI fix pass"""
    fixes_applied: list[str] = field(default_factory=list)
    yaml_updated: bool = False
    summary: str = ""


class WorldAnalyzer:
    """
    AI-powered world analyzer for playability and narrative quality.

    Uses LLM to:
    1. Holistically analyze the world for issues
    2. Generate targeted fixes based on analysis
    """

    def __init__(
        self,
        world_data: WorldData,
        world_id: str,
        design_brief: dict | None = None,
        yaml_content: dict | None = None,
    ):
        """
        Initialize the analyzer.

        Args:
            world_data: Parsed WorldData from YAML
            world_id: World identifier for logging
            design_brief: Original design brief for context
            yaml_content: Raw YAML content for modification
        """
        self.world_data = world_data
        self.world_id = world_id
        self.design_brief = design_brief
        self.yaml_content = yaml_content or {}

    async def analyze_playability(self) -> AnalysisResult:
        """
        Analyze the world for playability issues.

        Checks for:
        - Flag collision (same flag set multiple times)
        - Circular dependencies (key behind lock it opens)
        - Unreachable critical items
        - NPC-guarded items without mechanical gating
        - Missing NPC placements
        - Exit direction consistency
        - Victory condition achievability
        """
        from gaime_builder.core.llm_client import get_completion, parse_json_response
        from gaime_builder.core.prompt_loader import get_loader

        logger.info(f"Analyzing playability for world '{self.world_id}'...")

        try:
            prompt_template = get_loader().get_prompt(
                "world_builder", "playability_analysis_prompt.txt"
            )

            # Build world context
            context = self._build_world_context()

            prompt = prompt_template.format(
                world_name=self.world_data.world.name,
                theme=self.world_data.world.theme,
                tone=self.world_data.world.tone,
                world_context=context,
                design_brief=self._format_design_brief(),
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are a game designer analyzing text adventure worlds for playability issues.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await get_completion(
                messages,
                temperature=0.3,  # Lower temp for analytical tasks
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            data = parse_json_response(response, strict=True)
            return self._parse_analysis_result(data, "playability")

        except Exception as e:
            logger.error(f"Playability analysis failed: {e}")
            return AnalysisResult(
                issues=[],
                summary=f"Analysis failed: {e}",
            )

    async def fix_playability(self, analysis: AnalysisResult) -> FixResult:
        """
        Apply AI-generated fixes for playability issues.

        Args:
            analysis: Result from analyze_playability()

        Returns:
            FixResult with applied fixes
        """
        from gaime_builder.core.llm_client import get_completion, parse_json_response
        from gaime_builder.core.prompt_loader import get_loader

        if not analysis.has_issues:
            return FixResult(summary="No playability issues to fix")

        logger.info(
            f"Fixing {len(analysis.issues)} playability issue(s) for '{self.world_id}'..."
        )

        try:
            prompt_template = get_loader().get_prompt(
                "world_builder", "playability_fix_prompt.txt"
            )

            # Build issues summary
            issues_text = self._format_issues(analysis.issues)

            prompt = prompt_template.format(
                world_name=self.world_data.world.name,
                theme=self.world_data.world.theme,
                tone=self.world_data.world.tone,
                world_yaml=self._format_yaml_for_prompt(),
                issues=issues_text,
                design_brief=self._format_design_brief(),
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are a game designer fixing playability issues in text adventure worlds.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await get_completion(
                messages,
                temperature=0.5,
                max_tokens=8192,
                response_format={"type": "json_object"},
            )

            data = parse_json_response(response, strict=True)
            return self._apply_yaml_fixes(data)

        except Exception as e:
            logger.error(f"Playability fix failed: {e}")
            return FixResult(summary=f"Fix failed: {e}")

    async def analyze_narrative(self) -> AnalysisResult:
        """
        Analyze the world for narrative quality issues.

        Checks for:
        - Item placement motivation (WHY is item here?)
        - NPC behavior consistency (dialogue rules vs mechanics)
        - Environmental storytelling connections
        - Backstory gaps
        - Tone/theme consistency
        """
        from gaime_builder.core.llm_client import get_completion, parse_json_response
        from gaime_builder.core.prompt_loader import get_loader

        logger.info(f"Analyzing narrative for world '{self.world_id}'...")

        try:
            prompt_template = get_loader().get_prompt(
                "world_builder", "narrative_analysis_prompt.txt"
            )

            context = self._build_world_context()

            prompt = prompt_template.format(
                world_name=self.world_data.world.name,
                theme=self.world_data.world.theme,
                tone=self.world_data.world.tone,
                world_context=context,
                design_brief=self._format_design_brief(),
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are a narrative designer analyzing text adventure worlds for story quality.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await get_completion(
                messages,
                temperature=0.4,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            data = parse_json_response(response, strict=True)
            return self._parse_analysis_result(data, "narrative")

        except Exception as e:
            logger.error(f"Narrative analysis failed: {e}")
            return AnalysisResult(
                issues=[],
                summary=f"Analysis failed: {e}",
            )

    async def fix_narrative(self, analysis: AnalysisResult) -> FixResult:
        """
        Apply AI-generated fixes for narrative issues.

        Args:
            analysis: Result from analyze_narrative()

        Returns:
            FixResult with applied fixes
        """
        from gaime_builder.core.llm_client import get_completion, parse_json_response
        from gaime_builder.core.prompt_loader import get_loader

        if not analysis.has_issues:
            return FixResult(summary="No narrative issues to fix")

        logger.info(
            f"Fixing {len(analysis.issues)} narrative issue(s) for '{self.world_id}'..."
        )

        try:
            prompt_template = get_loader().get_prompt(
                "world_builder", "narrative_fix_prompt.txt"
            )

            issues_text = self._format_issues(analysis.issues)

            prompt = prompt_template.format(
                world_name=self.world_data.world.name,
                theme=self.world_data.world.theme,
                tone=self.world_data.world.tone,
                world_yaml=self._format_yaml_for_prompt(),
                issues=issues_text,
                design_brief=self._format_design_brief(),
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are a narrative designer improving story quality in text adventure worlds.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await get_completion(
                messages,
                temperature=0.6,  # Higher temp for creative work
                max_tokens=8192,
                response_format={"type": "json_object"},
            )

            data = parse_json_response(response, strict=True)
            return self._apply_yaml_fixes(data)

        except Exception as e:
            logger.error(f"Narrative fix failed: {e}")
            return FixResult(summary=f"Fix failed: {e}")

    def _build_world_context(self) -> str:
        """Build a comprehensive world context for analysis"""
        lines = []

        # Victory condition
        victory = self.world_data.world.victory
        if victory:
            lines.append("## Victory Condition")
            lines.append(f"- Location: {victory.location}")
            lines.append(f"- Flag: {victory.flag}")
            lines.append(f"- Item: {victory.item}")
            lines.append("")

        # Locations with exits, items, NPCs
        lines.append("## Locations")
        for loc_id, location in self.world_data.locations.items():
            lines.append(f"### {loc_id} ({location.name})")
            lines.append(f"Atmosphere: {location.atmosphere}")

            # Location requirements (flag gating)
            if location.requires and location.requires.flag:
                lines.append(f"**REQUIRES FLAG: {location.requires.flag}**")

            # Exits with details about gating
            if location.exits:
                for direction, exit_def in location.exits.items():
                    exit_info = f"{direction}→{exit_def.destination}"
                    if exit_def.hidden:
                        req = exit_def.find_condition.get("requires_flag") if exit_def.find_condition else None
                        exit_info += f" [HIDDEN, requires_flag: {req}]"
                    if exit_def.locked:
                        if exit_def.requires_key:
                            exit_info += f" [LOCKED, requires_key: {exit_def.requires_key}]"
                        elif exit_def.find_condition:
                            req = exit_def.find_condition.get("requires_flag")
                            exit_info += f" [LOCKED, requires_flag: {req}]"
                        else:
                            exit_info += " [LOCKED, no unlock method!]"
                    lines.append(f"  Exit: {exit_info}")

            # Items (with find_condition flags)
            if location.item_placements:
                for item_id, placement in location.item_placements.items():
                    item_info = item_id
                    if placement.find_condition:
                        req_flag = placement.find_condition.get("requires_flag")
                        if req_flag:
                            item_info = f"{item_id} (requires_flag: {req_flag})"
                    lines.append(f"  Item: {item_info}")

            # NPCs
            if location.npc_placements:
                npcs_str = ", ".join(location.npc_placements.keys())
                lines.append(f"NPCs: {npcs_str}")

            # Interactions
            if location.interactions:
                for int_id, interaction in location.interactions.items():
                    sets = f" → sets_flag:{interaction.sets_flag}" if interaction.sets_flag else ""
                    gives = f" → gives:{interaction.gives_item}" if interaction.gives_item else ""
                    lines.append(f"  Interaction: {int_id}{sets}{gives}")

            lines.append("")

        # NPCs
        lines.append("## NPCs")
        for npc_id, npc in self.world_data.npcs.items():
            lines.append(f"- {npc_id} ({npc.name}): {npc.personality}")

        # Items
        lines.append("")
        lines.append("## Items")
        for item_id, item in self.world_data.items.items():
            desc = item.examine_description or item.scene_description or ""
            lines.append(f"- {item_id} ({item.name}): {desc[:80]}...")

        return "\n".join(lines)

    def _format_design_brief(self) -> str:
        """Format design brief for prompts"""
        if not self.design_brief:
            return "Design brief not available"

        import json
        return json.dumps(self.design_brief, indent=2)

    def _format_yaml_for_prompt(self) -> str:
        """Format YAML content for the fix prompt"""
        import yaml

        if not self.yaml_content:
            # Build from world_data if not provided
            return "YAML content not available - use world context"

        return yaml.dump(self.yaml_content, default_flow_style=False, sort_keys=False)

    def _format_issues(self, issues: list[AnalysisIssue]) -> str:
        """Format issues for the fix prompt"""
        lines = []
        for i, issue in enumerate(issues, 1):
            lines.append(f"{i}. [{issue.severity.upper()}] {issue.description}")
            lines.append(f"   Location: {issue.location}")
            lines.append(f"   Suggested: {issue.suggested_fix}")
            lines.append("")
        return "\n".join(lines)

    def _parse_analysis_result(self, data: dict, category: str) -> AnalysisResult:
        """Parse LLM response into AnalysisResult"""
        issues = []

        for issue_data in data.get("issues", []):
            issues.append(
                AnalysisIssue(
                    severity=issue_data.get("severity", "medium"),
                    category=category,
                    location=issue_data.get("location", "unknown"),
                    description=issue_data.get("description", ""),
                    suggested_fix=issue_data.get("suggested_fix", ""),
                )
            )

        return AnalysisResult(
            issues=issues,
            summary=data.get("summary", ""),
        )

    def _apply_yaml_fixes(self, data: dict) -> FixResult:
        """Apply fixes from LLM response to YAML content"""
        fixes_applied = []

        # The LLM returns patches for each YAML file
        patches = data.get("patches", {})

        for file_type, file_patches in patches.items():
            if file_type == "locations" and "locations" in self.yaml_content:
                for loc_id, loc_patch in file_patches.items():
                    if loc_id in self.yaml_content["locations"]:
                        self._deep_merge(
                            self.yaml_content["locations"][loc_id], loc_patch
                        )
                        fixes_applied.append(f"Updated location: {loc_id}")

            elif file_type == "items" and "items" in self.yaml_content:
                for item_id, item_patch in file_patches.items():
                    if item_id in self.yaml_content["items"]:
                        self._deep_merge(
                            self.yaml_content["items"][item_id], item_patch
                        )
                        fixes_applied.append(f"Updated item: {item_id}")

            elif file_type == "npcs" and "npcs" in self.yaml_content:
                for npc_id, npc_patch in file_patches.items():
                    if npc_id in self.yaml_content["npcs"]:
                        self._deep_merge(
                            self.yaml_content["npcs"][npc_id], npc_patch
                        )
                        fixes_applied.append(f"Updated NPC: {npc_id}")

            elif file_type == "world" and "world" in self.yaml_content:
                self._deep_merge(self.yaml_content["world"], file_patches)
                fixes_applied.append("Updated world settings")

        return FixResult(
            fixes_applied=fixes_applied,
            yaml_updated=len(fixes_applied) > 0,
            summary=data.get("summary", f"Applied {len(fixes_applied)} fix(es)"),
        )

    def _deep_merge(self, target: dict, patch: dict) -> None:
        """Deep merge patch into target dict"""
        for key, value in patch.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
