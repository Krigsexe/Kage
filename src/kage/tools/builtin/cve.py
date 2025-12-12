"""CVE monitoring tool."""

import json
import re
from pathlib import Path
from typing import Any

import httpx

from kage.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)


class CVECheckTool(BaseTool):
    """Check for known vulnerabilities in dependencies."""

    PYPI_ADVISORY_URL = "https://pypi.org/pypi/{package}/json"
    OSV_API_URL = "https://api.osv.dev/v1/query"

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="cve_check",
            description="Check for known security vulnerabilities in project dependencies using OSV database.",
            category=ToolCategory.SECURITY,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to project (looks for requirements.txt, pyproject.toml, package.json)",
                    required=False,
                ),
                ToolParameter(
                    name="package",
                    type="string",
                    description="Specific package to check (name:version format)",
                    required=False,
                ),
            ],
        )

    async def execute(
        self,
        path: str = ".",
        package: str = "",
    ) -> ToolResult:
        if package:
            # Check single package
            if ":" in package:
                name, version = package.split(":", 1)
            else:
                name, version = package, ""

            vulns = await self._check_package(name, version)

            if not vulns:
                return ToolResult(
                    success=True,
                    output=f"No known vulnerabilities found for {package}",
                    metadata={"package": package, "vulnerabilities": 0},
                )

            return ToolResult(
                success=True,
                output=self._format_vulns(name, vulns),
                metadata={"package": package, "vulnerabilities": len(vulns)},
            )

        # Check project dependencies
        project_path = Path(path).resolve()
        deps = self._parse_dependencies(project_path)

        if not deps:
            return ToolResult(
                success=False,
                output="",
                error="No dependency files found (requirements.txt, pyproject.toml, package.json)",
            )

        all_vulns = {}
        for name, version in deps.items():
            vulns = await self._check_package(name, version)
            if vulns:
                all_vulns[name] = vulns

        if not all_vulns:
            return ToolResult(
                success=True,
                output=f"No known vulnerabilities found in {len(deps)} dependencies.",
                metadata={"checked": len(deps), "vulnerable": 0},
            )

        # Format output
        lines = [f"[!] Found vulnerabilities in {len(all_vulns)} packages:\n"]
        for pkg_name, vulns in all_vulns.items():
            lines.append(self._format_vulns(pkg_name, vulns))
            lines.append("")

        return ToolResult(
            success=True,
            output="\n".join(lines),
            metadata={
                "checked": len(deps),
                "vulnerable": len(all_vulns),
                "total_vulns": sum(len(v) for v in all_vulns.values()),
            },
        )

    async def _check_package(self, name: str, version: str) -> list[dict]:
        """Check a package for vulnerabilities using OSV API."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {
                    "package": {
                        "name": name,
                        "ecosystem": "PyPI",
                    }
                }
                if version:
                    payload["version"] = version

                response = await client.post(
                    self.OSV_API_URL,
                    json=payload,
                )
                response.raise_for_status()

                data = response.json()
                return data.get("vulns", [])

        except httpx.HTTPError:
            return []

    def _parse_dependencies(self, path: Path) -> dict[str, str]:
        """Parse dependencies from project files."""
        deps = {}

        # requirements.txt
        req_file = path / "requirements.txt"
        if req_file.exists():
            for line in req_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    match = re.match(r'^([a-zA-Z0-9_-]+)([=<>!~]+(.*))?', line)
                    if match:
                        name = match.group(1).lower()
                        version = match.group(3) or ""
                        deps[name] = version

        # pyproject.toml
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomli
                data = tomli.loads(pyproject.read_text())
                dependencies = data.get("project", {}).get("dependencies", [])
                for dep in dependencies:
                    match = re.match(r'^([a-zA-Z0-9_-]+)', dep)
                    if match:
                        deps[match.group(1).lower()] = ""
            except ImportError:
                # tomli not available, try regex
                content = pyproject.read_text()
                for match in re.finditer(r'"([a-zA-Z0-9_-]+)[^"]*"', content):
                    deps[match.group(1).lower()] = ""

        # package.json
        package_json = path / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())
                for dep_type in ["dependencies", "devDependencies"]:
                    for name, version in data.get(dep_type, {}).items():
                        deps[name.lower()] = version.lstrip("^~")
            except json.JSONDecodeError:
                pass

        return deps

    def _format_vulns(self, package: str, vulns: list[dict]) -> str:
        """Format vulnerability information."""
        lines = [f"## {package}"]

        for vuln in vulns[:5]:  # Limit to 5 vulns per package
            vuln_id = vuln.get("id", "Unknown")
            summary = vuln.get("summary", "No description")
            severity = vuln.get("severity", [{}])[0].get("type", "Unknown")

            lines.append(f"  - {vuln_id}: {summary[:100]}")
            lines.append(f"    Severity: {severity}")

            # Affected versions
            affected = vuln.get("affected", [{}])[0]
            ranges = affected.get("ranges", [])
            if ranges:
                events = ranges[0].get("events", [])
                introduced = next((e.get("introduced") for e in events if "introduced" in e), "?")
                fixed = next((e.get("fixed") for e in events if "fixed" in e), "not fixed")
                lines.append(f"    Affected: {introduced} -> {fixed}")

        if len(vulns) > 5:
            lines.append(f"  ... and {len(vulns) - 5} more")

        return "\n".join(lines)
