"""Client for the Atlos API (https://docs.atlos.org/technical/api/)."""

import os
from collections.abc import Iterator
from typing import Any

import requests

DEFAULT_BASE_URL = "https://platform.atlos.org"


class AtlosError(Exception):
    """Raised when the Atlos API returns an error."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class Atlos:
    """Project-scoped client for the Atlos API v2.

    Incidents are referenced by their slug (e.g. ``AD12H45``), everything else
    (source material, artifacts) by its ID.
    """

    def __init__(
        self,
        api_token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30,
    ):
        self.api_url = f"{base_url.rstrip('/')}/api/v2"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_token}"

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        response = self.session.request(
            method,
            f"{self.api_url}/{endpoint}",
            timeout=self.timeout,
            **kwargs,
        )
        if not response.ok:
            raise AtlosError(response.status_code, response.text)
        return response.json()

    def _paginate(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> Iterator[dict[str, Any]]:
        """Yield every result of a GET endpoint, following ``next`` cursors."""
        params = dict(params or {})
        while True:
            page = self._request("GET", endpoint, params=params)
            yield from page.get("results", [])
            cursor = page.get("next")
            if not cursor:
                return
            params["cursor"] = cursor

    # Incidents

    def get_incidents(
        self, filters: dict[str, Any] | None = None
    ) -> Iterator[dict[str, Any]]:
        """Yield all incidents in the project, most recently modified first.

        ``filters`` uses the same format as the in-platform search page URL,
        e.g. ``{"attr_status[]": ["To Do", "Cancelled"]}``.
        """
        return self._paginate("incidents", filters)

    def get_incident(self, slug: str) -> dict[str, Any] | None:
        """Return the incident with the given slug, or None if not found.

        The API has no endpoint for a single incident, so this scans all
        incidents. A project prefix (``CIV-7X7YFH``) is accepted and ignored.
        """
        slug = slug.rsplit("-", 1)[-1].upper()
        for incident in self.get_incidents():
            if str(incident.get("slug", "")).upper() == slug:
                return incident
        return None

    def create_incident(
        self,
        description: str,
        sensitive: list[str],
        status: str | None = None,
        restrictions: list[str] | None = None,
        tags: list[str] | None = None,
        urls: list[str] | None = None,
        **attributes: Any,
    ) -> Any:
        """Create an incident.

        ``sensitive`` is ``["Not Sensitive"]`` or any combination of
        ``"Graphic Violence"``, ``"Deceptive or Misleading"`` and
        ``"Personal Information Visible"``. Any other core or custom attribute
        can be passed as a keyword argument; custom attributes use their ID as
        the key, so pass them with ``**{"<attribute-id>": value}``.
        """
        if len(description) < 8:
            raise ValueError("description must be at least 8 characters long")
        payload: dict[str, Any] = {"description": description, "sensitive": sensitive}
        optional = {
            "status": status,
            "restrictions": restrictions,
            "tags": tags,
            "urls": urls,
        }
        payload.update({k: v for k, v in optional.items() if v is not None})
        payload.update(attributes)
        return self._request("POST", "incidents/new", json=payload)

    def update_attribute(
        self,
        slug: str,
        attribute: str,
        value: str | list[str],
        message: str | None = None,
    ) -> Any:
        """Update an incident attribute.

        ``attribute`` is a core attribute name (e.g. ``status``) or a custom
        attribute ID. ``value`` is a string for text/single-select attributes
        and a list of strings for multi-select ones. ``message`` is added as a
        comment on the change.
        """
        payload: dict[str, Any] = {"value": value}
        if message is not None:
            payload["message"] = message
        return self._request("POST", f"update/{slug}/{attribute}", json=payload)

    # Updates and comments

    def get_updates(self, slug: str | None = None) -> Iterator[dict[str, Any]]:
        """Yield all updates (including comments), most recent first.

        If ``slug`` is given, only updates for that incident are returned.
        """
        return self._paginate("updates", {"slug": slug} if slug else None)

    def add_comment(self, slug: str, message: str) -> Any:
        """Add a comment to the incident with the given slug."""
        return self._request("POST", f"add_comment/{slug}", params={"message": message})

    # Source material

    def get_source_materials(self) -> Iterator[dict[str, Any]]:
        """Yield all source material in the project, most recently modified first."""
        return self._paginate("source_material")

    def get_source_material(self, source_material_id: str) -> Any:
        """Return the source material with the given ID."""
        return self._request("GET", f"source_material/{source_material_id}")

    def create_source_material(
        self, slug: str, url: str | None = None, archive: bool | None = None
    ) -> Any:
        """Create source material in the incident with the given slug.

        Without ``url``/``archive``, an empty piece of source material is
        created, to which artifacts can be uploaded later.
        """
        params: dict[str, Any] = {}
        if url is not None:
            params["url"] = url
        if archive is not None:
            params["archive"] = archive
        return self._request("POST", f"source_material/new/{slug}", params=params)

    def set_source_material_metadata(
        self, source_material_id: str, namespace: str, metadata: dict[str, Any]
    ) -> Any:
        """Set metadata in a namespace, overwriting any existing metadata there."""
        return self._request(
            "POST",
            f"source_material/metadata/{source_material_id}/{namespace}",
            json={"metadata": metadata},
        )

    def upload_file(
        self, source_material_id: str, path: str, title: str | None = None
    ) -> Any:
        """Upload a file as an artifact of the given source material."""
        params = {"title": title} if title is not None else None
        with open(path, "rb") as f:
            return self._request(
                "POST",
                f"source_material/upload/{source_material_id}",
                params=params,
                files={"file": (os.path.basename(path), f)},
            )
