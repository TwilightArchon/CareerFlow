from __future__ import annotations

import base64
import binascii
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from .contracts import (
    CandidateFact,
    CandidateProfile,
    CandidateProfileInput,
    CandidateProfileSnapshot,
    DocumentStatus,
    EvidenceItem,
    FactState,
    ResumeImportResult,
    Sensitivity,
    SourceDocument,
)
from .database import CandidateProfileRecord, Database
from .document_parser import PDF_MEDIA_TYPE, ResumeMediaType, ResumeParseError, parse_resume
from .security import PayloadCipher

PROFILE_KEY_REFERENCE = "profile-vault-key-v1"


class SecretStore(Protocol):
    def put(self, reference: str, value: str) -> None: ...

    def get(self, reference: str) -> str | None: ...

    def delete(self, reference: str) -> None: ...


class ProfileVersionConflictError(RuntimeError):
    pass


class ProfileKeyUnavailableError(RuntimeError):
    pass


class ProfileRequiredError(RuntimeError):
    pass


class ResumeAlreadyImportedError(RuntimeError):
    pass


class EvidenceNotFoundError(RuntimeError):
    pass


FIELD_SENSITIVITY: dict[str, Sensitivity] = {
    "identity.first_name": Sensitivity.ORDINARY,
    "identity.last_name": Sensitivity.ORDINARY,
    "identity.preferred_name": Sensitivity.ORDINARY,
    "contact.email": Sensitivity.SENSITIVE,
    "contact.phone": Sensitivity.SENSITIVE,
    "address.city": Sensitivity.SENSITIVE,
    "address.region": Sensitivity.SENSITIVE,
    "address.country": Sensitivity.SENSITIVE,
    "address.postal_code": Sensitivity.SENSITIVE,
    "links.linkedin": Sensitivity.ORDINARY,
    "links.github": Sensitivity.ORDINARY,
    "education.0.school": Sensitivity.ORDINARY,
    "education.0.degree": Sensitivity.ORDINARY,
    "education.0.field_of_study": Sensitivity.ORDINARY,
    "education.0.graduation_year": Sensitivity.ORDINARY,
    "work_authorization.status": Sensitivity.LEGAL,
    "work_authorization.requires_sponsorship": Sensitivity.LEGAL,
}


def _input_fields(profile: CandidateProfileInput) -> list[tuple[str, str]]:
    fields: list[tuple[str, str | int | bool | None]] = [
        ("identity.first_name", profile.first_name),
        ("identity.last_name", profile.last_name),
        ("identity.preferred_name", profile.preferred_name),
        ("contact.email", profile.email),
        ("contact.phone", profile.phone),
        ("address.city", profile.city),
        ("address.region", profile.region),
        ("address.country", profile.country),
        ("address.postal_code", profile.postal_code),
        ("links.linkedin", str(profile.linkedin_url) if profile.linkedin_url else ""),
        ("links.github", str(profile.github_url) if profile.github_url else ""),
        ("education.0.school", profile.school),
        ("education.0.degree", profile.degree),
        ("education.0.field_of_study", profile.field_of_study),
        ("education.0.graduation_year", profile.graduation_year),
        ("work_authorization.status", profile.work_authorization),
        ("work_authorization.requires_sponsorship", profile.requires_sponsorship),
    ]
    return [(path, str(value)) for path, value in fields if value not in (None, "", "unspecified")]


def _build_profile(
    profile_input: CandidateProfileInput, *, profile_id: UUID, version: int
) -> CandidateProfile:
    facts: list[CandidateFact] = []
    evidence: list[EvidenceItem] = []
    for path, value in _input_fields(profile_input):
        item = EvidenceItem(
            statement=f"{path} = {value}",
            extraction_method="user",
            confidence=1,
            verified=True,
        )
        evidence.append(item)
        facts.append(
            CandidateFact(
                canonical_path=path,
                value=value,
                state=FactState.VERIFIED,
                evidence_ids=[item.id],
                sensitivity=FIELD_SENSITIVITY[path],
            )
        )
    return CandidateProfile(id=profile_id, version=version, facts=facts, evidence=evidence)


class ProfileVault:
    def __init__(self, database: Database, secret_store: SecretStore, data_dir: Path) -> None:
        self.database = database
        self.secret_store = secret_store
        self.data_dir = data_dir

    async def load(self) -> CandidateProfileSnapshot | None:
        record = await self.database.get_latest_profile_record()
        if record is None:
            return None
        profile = self._profile_for_record(record)
        updated_at = (
            record.updated_at
            if record.updated_at.tzinfo is not None
            else record.updated_at.replace(tzinfo=UTC)
        )
        return CandidateProfileSnapshot(profile=profile, updated_at=updated_at)

    async def save(
        self, profile_input: CandidateProfileInput, *, expected_version: int | None
    ) -> CandidateProfileSnapshot:
        current = await self.database.get_latest_profile_record()
        current_version = current.version if current else None
        if expected_version != current_version:
            raise ProfileVersionConflictError(
                f"Profile version changed from {expected_version} to {current_version}"
            )

        profile_id = UUID(current.id) if current else uuid4()
        version = (current.version + 1) if current else 1
        manual_profile = _build_profile(profile_input, profile_id=profile_id, version=version)
        if current is None:
            profile = manual_profile
        else:
            current_profile = self._profile_for_record(current)
            profile = CandidateProfile(
                id=profile_id,
                version=version,
                facts=[
                    *manual_profile.facts,
                    *[
                        fact
                        for fact in current_profile.facts
                        if fact.canonical_path not in FIELD_SENSITIVITY
                    ],
                ],
                evidence=[
                    *manual_profile.evidence,
                    *[
                        item
                        for item in current_profile.evidence
                        if item.source_document_id is not None or item.extraction_method != "user"
                    ],
                ],
                source_documents=current_profile.source_documents,
            )
        return await self._persist(profile, has_existing_profile=current is not None)

    async def import_resume(
        self,
        content: bytes,
        *,
        filename: str,
        media_type: ResumeMediaType,
        expected_version: int,
    ) -> ResumeImportResult:
        current = await self.database.get_latest_profile_record()
        if current is None:
            raise ProfileRequiredError("Create a verified profile before importing a résumé")
        if expected_version != current.version:
            raise ProfileVersionConflictError(
                f"Profile version changed from {expected_version} to {current.version}"
            )

        current_profile = self._profile_for_record(current)
        digest = hashlib.sha256(content).hexdigest()
        if any(document.sha256 == digest for document in current_profile.source_documents):
            raise ResumeAlreadyImportedError("This résumé version has already been imported")

        document_id = uuid4()
        try:
            statements = parse_resume(content, media_type)
            status = DocumentStatus.PARSED
            parse_error_code = None
            if not statements:
                status = (
                    DocumentStatus.NEEDS_OCR
                    if media_type == PDF_MEDIA_TYPE
                    else DocumentStatus.FAILED
                )
                parse_error_code = "selectable_text_unavailable"
        except ResumeParseError as error:
            statements = []
            status = DocumentStatus.FAILED
            parse_error_code = error.error_code

        artifact_ref = f"artifacts/{document_id}.cfenc"
        source_document = SourceDocument(
            id=document_id,
            filename=Path(filename).name,
            media_type=media_type,
            sha256=digest,
            encrypted_artifact_ref=artifact_ref,
            status=status,
            parse_error_code=parse_error_code,
            extracted_evidence_count=len(statements),
        )
        evidence = [
            EvidenceItem(
                source_document_id=document_id,
                source_span=statement.source_span,
                statement=statement.statement,
                extraction_method="deterministic",
                confidence=1,
                verified=False,
            )
            for statement in statements
        ]
        next_profile = CandidateProfile(
            id=current_profile.id,
            version=current.version + 1,
            facts=current_profile.facts,
            evidence=[*current_profile.evidence, *evidence],
            source_documents=[*current_profile.source_documents, source_document],
        )

        cipher = self._cipher_for_existing_record(current)
        encrypted_artifact = cipher.encrypt(
            content,
            associated_data=self._artifact_associated_data(document_id, digest),
        )
        artifact_path = self.data_dir / artifact_ref
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(encrypted_artifact, encoding="utf-8")
        try:
            snapshot = await self._persist(next_profile, has_existing_profile=True)
        except Exception:
            artifact_path.unlink(missing_ok=True)
            raise
        return ResumeImportResult(snapshot=snapshot, document=source_document)

    async def set_evidence_verification(
        self, evidence_id: UUID, *, verified: bool, expected_version: int
    ) -> CandidateProfileSnapshot:
        current = await self.database.get_latest_profile_record()
        if current is None:
            raise ProfileRequiredError("Create a verified profile before reviewing evidence")
        if expected_version != current.version:
            raise ProfileVersionConflictError(
                f"Profile version changed from {expected_version} to {current.version}"
            )
        current_profile = self._profile_for_record(current)
        found = False
        evidence: list[EvidenceItem] = []
        for item in current_profile.evidence:
            if item.id == evidence_id and item.source_document_id is not None:
                found = True
                evidence.append(item.model_copy(update={"verified": verified}))
            else:
                evidence.append(item)
        if not found:
            raise EvidenceNotFoundError("Imported evidence item was not found")
        next_profile = current_profile.model_copy(
            update={"version": current.version + 1, "evidence": evidence}
        )
        return await self._persist(next_profile, has_existing_profile=True)

    async def _persist(
        self, profile: CandidateProfile, *, has_existing_profile: bool
    ) -> CandidateProfileSnapshot:
        cipher = self._cipher_for_save(has_existing_profile=has_existing_profile)
        now = datetime.now(UTC)
        encrypted = cipher.encrypt(
            profile.model_dump_json(by_alias=True).encode(),
            associated_data=self._associated_data(profile.id, profile.version),
        )
        await self.database.add_profile_record(
            CandidateProfileRecord(
                id=str(profile.id),
                version=profile.version,
                encrypted_payload=encrypted,
                encryption_key_ref=PROFILE_KEY_REFERENCE,
                created_at=now,
                updated_at=now,
            )
        )
        return CandidateProfileSnapshot(profile=profile, updated_at=now)

    def _profile_for_record(self, record: CandidateProfileRecord) -> CandidateProfile:
        cipher = self._cipher_for_existing_record(record)
        plaintext = cipher.decrypt(
            record.encrypted_payload,
            associated_data=self._associated_data(UUID(record.id), record.version),
        )
        return CandidateProfile.model_validate_json(plaintext)

    def _cipher_for_save(self, *, has_existing_profile: bool) -> PayloadCipher:
        encoded = self.secret_store.get(PROFILE_KEY_REFERENCE)
        if encoded is None:
            if has_existing_profile:
                raise ProfileKeyUnavailableError("The profile encryption key is unavailable")
            key = PayloadCipher.new_key()
            self.secret_store.put(PROFILE_KEY_REFERENCE, base64.b64encode(key).decode("ascii"))
            return PayloadCipher(key)
        return self._decode_cipher(encoded)

    def _cipher_for_existing_record(self, record: CandidateProfileRecord) -> PayloadCipher:
        encoded = self.secret_store.get(record.encryption_key_ref)
        if encoded is None:
            raise ProfileKeyUnavailableError("The profile encryption key is unavailable")
        return self._decode_cipher(encoded)

    @staticmethod
    def _decode_cipher(encoded: str) -> PayloadCipher:
        try:
            return PayloadCipher(base64.b64decode(encoded, validate=True))
        except (ValueError, TypeError, binascii.Error) as error:
            raise ProfileKeyUnavailableError("The profile encryption key is invalid") from error

    @staticmethod
    def _associated_data(profile_id: UUID, version: int) -> bytes:
        return f"candidate-profile:{profile_id}:version:{version}".encode()

    @staticmethod
    def _artifact_associated_data(document_id: UUID, digest: str) -> bytes:
        return f"source-document:{document_id}:sha256:{digest}".encode()
