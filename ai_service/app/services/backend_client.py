"""
backend_client.py

This module is responsible for communicating with the Backend API.
The AI service NEVER talks to the database directly.
All database operations go through this client.

Responsibilities:
- Handle authentication headers (JWT access token)
- Send requests to backend endpoints
- Retry on temporary failures
- Handle timeouts and backend errors safely
"""

import json
import time
import requests
from typing import Optional, Dict, Any


class BackendAPIClient:
    """
    BackendAPIClient is a thin and safe wrapper over backend REST APIs.

    This class:
    - Attaches Authorization headers
    - Sends multipart/form-data requests
    - Retries requests on network/server failure
    """

    def __init__(
        self,
        base_url: str,
        access_token: str,
        timeout: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.5
    ):
        """
        Initialize backend client.

        Parameters:
        - base_url: Backend API base URL (e.g. https://medicalai.pythonanywhere.com/api)
        - access_token: JWT access token for Authorization
        - timeout: Request timeout in seconds
        - max_retries: Number of retry attempts on failure
        - retry_delay: Delay (seconds) between retries
        """

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Authorization header used for all requests
        self.headers = {
            "Authorization": f"Bearer {access_token}"
        }

    # ------------------------------------------------------------------
    # Internal request handler with retry logic
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Internal method to send HTTP requests with retry support.

        Parameters:
        - method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        - endpoint: API endpoint path
        - data: form-data fields
        - files: file fields (if any)

        Returns:
        - Parsed JSON response

        Raises:
        - RuntimeError on final failure
        """

        url = f"{self.base_url}{endpoint}"

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    data=data,
                    files=files,
                    timeout=self.timeout
                )

                # Success response
                if 200 <= response.status_code < 300:
                    if response.content:
                        return response.json()
                    return {}

                # Client errors (do not retry)
                if 400 <= response.status_code < 500:
                    raise RuntimeError(
                        f"Backend rejected request ({response.status_code}): {response.text}"
                    )

                # Server errors (retry)
                raise RuntimeError(
                    f"Backend server error ({response.status_code})"
                )

            except Exception as error:
                last_error = error

                # Retry if attempts remain
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue

                break

        # All retries exhausted
        raise RuntimeError(
            f"Backend request failed after {self.max_retries} attempts: {last_error}"
        )

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def create_prescription(
        self,
        *,
        users: int,
        doctor: Optional[int],
        prescription_image: str,
        patient: str,
        medicines: Dict[str, Any],
        medical_tests: Optional[Dict[str, Any]] = None,
        next_appointment_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new prescription in backend.

        This method sends multipart/form-data as required by backend.

        Parameters:
        - users: User ID (patient account)
        - doctor: Doctor ID (optional)
        - prescription_image: Image URL
        - patient: Human-readable patient info
        - medicines: Medicines data (Python dict, will be JSON stringified)
        - medical_tests: Medical tests data (Python dict, JSON stringified)
        - next_appointment_date: Optional follow-up date (YYYY-MM-DD)

        Returns:
        - Backend response JSON
        """

        form_data: Dict[str, Any] = {
            "users": str(users),
            "prescription_image": prescription_image,
            "patient": patient,
            "medicines": json.dumps(medicines)
        }

        if doctor is not None:
            form_data["doctor"] = str(doctor)

        if medical_tests is not None:
            form_data["medical_tests"] = json.dumps(medical_tests)

        if next_appointment_date:
            form_data["next_appointment_date"] = next_appointment_date

        return self._request(
            method="POST",
            endpoint="/prescriptions/",
            data=form_data
        )

    def get_my_prescriptions(self) -> Dict[str, Any]:
        """
        Fetch all prescriptions for the authenticated user.
        Used for voice queries like:
        'Show my prescriptions'
        """

        return self._request(
            method="GET",
            endpoint="/prescriptions/my_prescriptions/"
        )

    def get_prescription_medicines(self, prescription_id: int) -> Dict[str, Any]:
        """
        Fetch medicines for a specific prescription.
        Used for voice queries like:
        'What medicines are in this prescription?'
        """

        return self._request(
            method="GET",
            endpoint=f"/prescriptions/{prescription_id}/medicines/"
        )
