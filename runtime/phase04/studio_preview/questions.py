"""Local HTTP boundary for the existing synthetic consultation engine."""

import re

from abc_foundation.eng02_consultation import ConsultationEngine, SYNTHETIC_SERVICE
from abc_foundation.eng14_policy import SyntheticQuestionPolicy
from abc_foundation.oidc import Principal
from abc_foundation.store import DomainError

QUESTION_ROUTE = re.compile(r"/_studio/consultations/([a-f0-9-]{36})/(questions|next-question|answers)")
LOCAL_ISSUER = "https://studio-preview.invalid"


class ScopedSession:
    def __init__(self, store, actor):
        self.store = store
        self.actor = actor
        self.principal = Principal(actor["sub"], LOCAL_ISSUER)

    def get(self, principal, session_id):
        if principal != self.principal:
            raise DomainError(403, "scope_not_authorized")
        return self.store.get(self.actor, session_id)

    def authorize_version(self, connection, session_id, expected_version):
        session = self.store.get(self.actor, session_id, connection=connection)
        if session.get("service_id") != SYNTHETIC_SERVICE:
            raise DomainError(403, "synthetic_service_only")
        if session["state"] != "CREATED":
            raise DomainError(409, "session_not_active")
        if session["state_version"] != expected_version:
            raise DomainError(409, "state_version_conflict")
        return session


class StudioQuestions:
    def __init__(self, database, store, actor):
        self.scope = ScopedSession(store, actor)
        self.engine = ConsultationEngine(database, self.scope)
        self.policy = SyntheticQuestionPolicy()

    def read(self, session_id, operation):
        result = self.engine.next(self.scope.principal, session_id)
        if operation == "questions":
            return {
                "profile_version": result["profile_version"],
                "questions": [
                    {key: question[key] for key in ("question_id", "text")}
                    for question in sorted(self.engine.questions.values(), key=lambda q: (-q["priority"], q["question_id"]))
                ],
            }
        if question := result["next_question"]:
            question["allowed_values"] = self.engine.questions[question["question_id"]]["allowed_values"]
        return result

    def answer(self, session_id, body, version, key):
        if set(body) != {"question_id", "value"}:
            raise DomainError(400, "invalid_synthetic_answer")
        return self.engine.record(
            self.scope.principal, session_id,
            question_id=body["question_id"], value=body["value"], source="SPECIALIST",
            operation_key=key, expected_version=version,
            authorize_version=self.scope.authorize_version, question_policy=self.policy)
