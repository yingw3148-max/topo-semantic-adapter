"""CLI file loader: scan site folders and split command/echo pairs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# The delimiter used by the Huawei collection tool to separate command blocks.
DEFAULT_DELIMITER = "=========######HUAWEI#####========="


@dataclass(frozen=True)
class CommandBlock:
    """One command and its corresponding CLI output."""

    command: str
    output: str
    device_ip: str
    device_id: str
    site: str
    source_file: Path


class CLIFileLoader:
    """Load CLI collection files for a given site.

    Expected folder layout::

        {base_path}/{site_name}-配置/inspect/{device_ip}_{device_id}/CommonCollectResult

    Each ``CommonCollectResult`` file is split by ``delimiter`` into command/echo
    blocks. The first line of each block is treated as the command; the rest is
    the command output.
    """

    def __init__(
        self,
        site_name: str,
        base_path: str | Path,
        delimiter: str = DEFAULT_DELIMITER,
    ):
        self.site_name = site_name
        self.base_path = Path(base_path)
        self.delimiter = delimiter

    @property
    def inspect_dir(self) -> Path:
        # Production layouts sometimes name the site folder directly,
        # e.g. "湖北大学配置". Prefer that, otherwise fall back to the
        # "{site_name}-配置" convention used by earlier test fixtures.
        direct_site = self.base_path / self.site_name
        if direct_site.is_dir():
            return direct_site / "inspect"
        return self.base_path / f"{self.site_name}-配置" / "inspect"

    def iter_blocks(self) -> Iterator[CommandBlock]:
        """Yield every command/echo block found in the site."""
        if not self.inspect_dir.exists():
            return
        for device_dir in sorted(self.inspect_dir.iterdir()):
            if not device_dir.is_dir():
                continue
            yield from self.iter_device_blocks(device_dir)

    def iter_device_blocks(self, device_dir: Path) -> Iterator[CommandBlock]:
        """Yield command/echo blocks for a single device directory."""
        device_ip, device_id = self._parse_device_dir_name(device_dir.name)
        result_file = device_dir / "CommonCollectResult"
        if not result_file.is_file():
            return
        yield from self._split_file(result_file, device_ip, device_id)

    def _parse_device_dir_name(self, name: str) -> tuple[str, str]:
        if "_" in name:
            ip, dev_id = name.split("_", 1)
            return ip, dev_id
        return name, ""

    def _split_file(
        self, file_path: Path, device_ip: str, device_id: str
    ) -> Iterator[CommandBlock]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        parts = text.split(self.delimiter)
        for part in parts:
            part = part.strip("\r\n")
            if not part.strip():
                continue
            lines = part.splitlines()
            command = lines[0].strip()
            output = "\n".join(lines[1:]).strip("\r\n")
            yield CommandBlock(
                command=command,
                output=output,
                device_ip=device_ip,
                device_id=device_id,
                site=self.site_name,
                source_file=file_path,
            )
