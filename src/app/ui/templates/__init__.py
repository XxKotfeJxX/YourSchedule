from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.ui.templates.template_tab import CompanyTemplatesTab

__all__ = ["CompanyTemplatesTab"]


def __getattr__(name: str):
    if name == "CompanyTemplatesTab":
        from app.ui.templates.template_tab import CompanyTemplatesTab

        return CompanyTemplatesTab
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
