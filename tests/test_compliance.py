import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from main import apply_compliance_redaction, TEMPLATE_RULES


class TestHIPAARedaction:
    """Tests for the HIPAA Safe Harbor compliance template engine."""

    def test_template_loaded(self):
        assert len(TEMPLATE_RULES) > 0, "HIPAA template rules should be loaded on startup"

    def test_ssn_redacted(self):
        text = "Patient SSN is 123-45-6789"
        result = apply_compliance_redaction(text)
        assert "123-45-6789" not in result
        assert "[REDACTED_SSN]" in result

    def test_phone_redacted(self):
        text = "Call 555-019-2830 for details"
        result = apply_compliance_redaction(text)
        assert "555-019-2830" not in result
        assert "[REDACTED_PHONE_FAX]" in result

    def test_email_redacted(self):
        text = "Contact: patient@hospital.org"
        result = apply_compliance_redaction(text)
        assert "patient@hospital.org" not in result
        assert "[REDACTED_EMAIL]" in result

    def test_mrn_redacted(self):
        text = "MRN: 847291 on file"
        result = apply_compliance_redaction(text)
        assert "847291" not in result
        assert "[REDACTED_MRN]" in result

    def test_ip_address_redacted(self):
        text = "Source IP: 192.168.1.5"
        result = apply_compliance_redaction(text)
        assert "192.168.1.5" not in result
        assert "[REDACTED_IP]" in result

    def test_date_redacted(self):
        text = "Admitted 12/05/2023"
        result = apply_compliance_redaction(text)
        assert "12/05/2023" not in result

    def test_url_redacted(self):
        text = "Portal at https://patient-portal.hospital.com/records"
        result = apply_compliance_redaction(text)
        assert "https://patient-portal.hospital.com" not in result
        assert "[REDACTED_URL]" in result

    def test_account_number_redacted(self):
        text = "ACCT: 9928374 billing"
        result = apply_compliance_redaction(text)
        assert "9928374" not in result
        assert "[REDACTED_ACCT]" in result

    def test_multiple_pii_in_one_string(self):
        text = "Patient SSN 123-45-6789, email test@clinic.com, phone 555-123-4567, IP 10.0.0.1"
        result = apply_compliance_redaction(text)
        assert "123-45-6789" not in result
        assert "test@clinic.com" not in result
        assert "10.0.0.1" not in result

    def test_clean_text_unchanged(self):
        text = "This is a normal status message with no PII."
        result = apply_compliance_redaction(text)
        assert result == text

    def test_empty_string(self):
        assert apply_compliance_redaction("") == ""


class TestComplianceIntegration:
    """Verify redaction is applied end-to-end through the execute endpoint."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def test_execute_redacts_pii(self, client):
        res = client.post("/v1/execute", json={
            "command": "echo 'Patient SSN 123-45-6789 email doc@clinic.com'"
        })
        assert res.status_code == 200
        output = res.json()["output"]
        assert "123-45-6789" not in output
        assert "doc@clinic.com" not in output
