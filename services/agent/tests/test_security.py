from careerflow_agent.security import REDACTED, PayloadCipher, redact


def test_encryption_round_trip_and_associated_data() -> None:
    cipher = PayloadCipher(PayloadCipher.new_key())
    encrypted = cipher.encrypt(b"candidate-data", associated_data=b"profile:1")
    assert "candidate-data" not in encrypted
    assert cipher.decrypt(encrypted, associated_data=b"profile:1") == b"candidate-data"


def test_redaction_is_recursive() -> None:
    value = {"profile": {"password": "secret"}, "items": [{"api_key": "key"}]}
    assert redact(value) == {
        "profile": {"password": REDACTED},
        "items": [{"api_key": REDACTED}],
    }
