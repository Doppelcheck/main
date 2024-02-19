import dataclasses

from tools.plugins.abstract import InterfaceDataConfig, Parameters


@dataclasses.dataclass
class ParametersGoogle(Parameters):
    # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list

    cx: str
    key: str
    c2coff: int | None = None
    cr: str | None = None
    dateRestrict: str | None = None
    exactTerms: str | None = None
    excludeTerms: str | None = None
    fileType: str | None = None
    filter: str = "1"
    gl: str | None = None
    highRange: str | None = None
    hl: str | None = None
    hq: str | None = None
    linkSite: str | None = None
    lowRange: str | None = None
    lr: str | None = None
    # num: int = 10
    orTerms: str | None = None
    rights: str | None = None
    safe: str = 'off'
    siteSearch: str | None = None
    siteSearchFilter: str | None = None
    sort: str | None = "date"  # changed default for news focus
    start: int = 1


@dataclasses.dataclass
class InterfaceGoogle(InterfaceDataConfig):
    parameters: ParametersGoogle
    provider: str = dataclasses.field(default="Google", init=False)


