"""ServiceNow Table API reads, extracted from Day 5.

The caller supplies a session with authentication configured. Tests can supply
a mock session; the client has no switches for deliberately failing requests.
"""

from urllib.parse import parse_qs, urlsplit

import requests

from .models import IncidentModel


FIELDS = "number,short_description,priority,state,assigned_to,sys_id"
OPEN_INCIDENTS_QUERY = "active=true^ORDERBYDESCsys_created_on^ORDERBYsys_id"


class ServiceNowClient:
    def __init__(self, instance: str, session: requests.Session) -> None:
        url = urlsplit(instance)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.path not in ("", "/")
            or url.query
            or url.fragment
        ):
            raise ValueError("SN_INSTANCE must be an HTTPS instance URL with no API or UI path.")
        self.base_url = instance.rstrip("/") + "/api/now/table"
        self.session = session

    def _request(self, path: str, params: dict[str, str | int]) -> requests.Response:
        response = self.session.get(
            f"{self.base_url}/{path}",
            params=params,
            timeout=30,
            allow_redirects=False,
        )
        response.raise_for_status()
        if response.is_redirect:
            raise ValueError("ServiceNow redirected the request. Check SN_INSTANCE.")
        return response

    def _incident_page(self, query: str, limit: int, offset: int) -> requests.Response:
        if not 1 <= limit <= 1000:
            raise ValueError("Page size must be between 1 and 1000.")
        return self._request(
            "incident",
            {
                "sysparm_query": query,
                "sysparm_limit": limit,
                "sysparm_offset": offset,
                "sysparm_fields": FIELDS,
                "sysparm_display_value": "false",
            },
        )

    @staticmethod
    def _validate_records(response: requests.Response) -> list[IncidentModel]:
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("result"), list):
            raise ValueError("Expected a ServiceNow response containing a 'result' list.")
        return [IncidentModel.model_validate(record) for record in payload["result"]]

    def get_incidents(self, query: str, limit: int = 5) -> list[IncidentModel]:
        """Return one page, preserving the Day 5 helper's purpose."""
        return self._validate_records(self._incident_page(query, limit, 0))

    def get_all_incidents(
        self, query: str = OPEN_INCIDENTS_QUERY, page_size: int = 100
    ) -> list[IncidentModel]:
        """Read every page so the report isn't limited to the first five records."""
        incidents = []
        offset = 0
        while True:
            response = self._incident_page(query, page_size, offset)
            page = self._validate_records(response)
            incidents.extend(page)
            next_link = response.links.get("next")
            if next_link:
                # Use only the next offset, never send credentials to a link's host.
                parameters = parse_qs(urlsplit(next_link["url"]).query)
                try:
                    next_offset = int(parameters["sysparm_offset"][0])
                except (KeyError, IndexError, ValueError):
                    raise ValueError("ServiceNow returned an invalid pagination link.") from None
                if next_offset <= offset:
                    raise ValueError("ServiceNow pagination did not advance.")
                offset = next_offset
            elif len(page) == page_size:
                # Also handle servers that omit pagination headers.
                offset += page_size
            else:
                break
        return incidents
