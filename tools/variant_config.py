"""Shared variant metadata for builds, tests and immutable archives."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_ID = "dev.int0x19.watchface.terminal"


def properties():
    values = {}
    for raw in (ROOT / "watchface/variants.properties").read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


@dataclass(frozen=True)
class Variant:
    name: str
    application_id: str
    version: str
    version_code: int
    display_name: str
    base_version: str

    @property
    def base(self):
        return ROOT / "versions" / self.base_version

    @property
    def wff(self):
        source = "compact" if self.name == "compact" else "main"
        return ROOT / f"watchface/src/{source}/res/raw/watchface.xml"

    @property
    def previews(self):
        return self.base if self.name == "compact" else ROOT / "docs"

    @property
    def metadata(self):
        return ROOT / f"watchface/build/outputs/apk/{self.name}/debug/output-metadata.json"

    @property
    def aab(self):
        return ROOT / f"watchface/build/outputs/bundle/{self.name}Release/watchface-{self.name}-release.aab"


def variants():
    config = properties()
    return tuple(Variant(name=name, application_id=config[f"{name}.applicationId"],
                         version=config[f"{name}.versionName"], version_code=int(config["versionCode"]),
                         display_name=config[f"{name}.displayName"], base_version=config[f"{name}.baseVersion"])
                 for name in ("compact", "large"))
