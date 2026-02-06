from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api import conversations
from app.config import get_extras_config
from app.db import crud
from app.db.base import Base
from app.db.models import Contact, Conversation, ConversationState, User, UserRole


def _build_test_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, future=True)
    return local_session()


class TestTaxonomyAndTags(unittest.TestCase):
    def setUp(self) -> None:
        self.session = _build_test_session()
        base_config = get_extras_config()
        self._config_patch = patch(
            "app.api.conversations.get_extras_config",
            return_value=replace(
                base_config,
                features=replace(
                    base_config.features,
                    taxonomy_admin_enabled=True,
                ),
            ),
        )
        self._config_patch.start()

        self.admin = User(id=1, username="admin", password_hash="hash", role=UserRole.ADMIN)
        self.supervisor = User(
            id=2,
            username="supervisor",
            password_hash="hash",
            role=UserRole.SUPERVISOR,
        )
        self.agent = User(id=3, username="agent", password_hash="hash", role=UserRole.AGENT)
        self.contact = Contact(id=10, whatsapp_number="15550009999", display_name="Contacto")
        self.conversation = Conversation(
            id=20,
            contact_id=self.contact.id,
            state=ConversationState.ASIGNADO,
            assigned_to=self.agent.id,
        )
        self.session.add_all(
            [self.admin, self.supervisor, self.agent, self.contact, self.conversation]
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self._config_patch.stop()

    def test_supervisor_can_list_taxonomy_tags(self) -> None:
        tag = crud.create_taxonomy_tag(
            self.session,
            name="Ventas",
            created_by=self.admin.id,
        )
        crud.update_taxonomy_tag(tag, is_archived=True)
        self.session.commit()

        tags = conversations.list_taxonomy_tags(
            include_archived=True,
            current_user=self.supervisor,
            db=self.session,
        )
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].name, "Ventas")
        self.assertTrue(tags[0].is_archived)

    def test_create_taxonomy_tag_requires_admin(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            conversations.create_taxonomy_tag(
                payload=conversations.TaxonomyTagCreateRequest(name="Soporte"),
                current_user=self.agent,
                db=self.session,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_supervisor_cannot_update_taxonomy_tag(self) -> None:
        tag = crud.create_taxonomy_tag(
            self.session,
            name="Facturacion",
            created_by=self.admin.id,
        )
        self.session.commit()

        with self.assertRaises(HTTPException) as ctx:
            conversations.update_taxonomy_tag(
                tag_id=tag.id,
                payload=conversations.TaxonomyTagUpdateRequest(name="Billing"),
                current_user=self.supervisor,
                db=self.session,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_admin_can_create_rename_and_archive_tag(self) -> None:
        created = conversations.create_taxonomy_tag(
            payload=conversations.TaxonomyTagCreateRequest(name="Cobros"),
            current_user=self.admin,
            db=self.session,
        )
        self.assertEqual(created.name, "Cobros")
        self.assertFalse(created.is_archived)

        renamed = conversations.update_taxonomy_tag(
            tag_id=created.tag_id,
            payload=conversations.TaxonomyTagUpdateRequest(name="Pagos"),
            current_user=self.admin,
            db=self.session,
        )
        self.assertEqual(renamed.name, "Pagos")

        archived = conversations.update_taxonomy_tag(
            tag_id=created.tag_id,
            payload=conversations.TaxonomyTagUpdateRequest(is_archived=True),
            current_user=self.admin,
            db=self.session,
        )
        self.assertTrue(archived.is_archived)

    def test_agent_can_set_conversation_tags_and_read_detail(self) -> None:
        urgent = crud.create_taxonomy_tag(
            self.session,
            name="Urgente",
            created_by=self.admin.id,
        )
        vip = crud.create_taxonomy_tag(
            self.session,
            name="VIP",
            created_by=self.admin.id,
        )
        self.session.commit()

        assigned = conversations.set_conversation_tags(
            conversation_id=self.conversation.id,
            payload=conversations.SetConversationTagsRequest(
                tag_ids=[urgent.id, vip.id],
            ),
            current_user=self.agent,
            db=self.session,
        )
        self.assertEqual({item.name for item in assigned}, {"Urgente", "VIP"})

        detail = conversations.get_conversation_detail(
            conversation_id=self.conversation.id,
            current_user=self.agent,
            db=self.session,
        )
        self.assertEqual({item.name for item in detail.tags}, {"Urgente", "VIP"})
        self.assertEqual({item.name for item in detail.available_tags}, {"Urgente", "VIP"})

    def test_set_conversation_tags_rejects_archived_tag(self) -> None:
        tag = crud.create_taxonomy_tag(
            self.session,
            name="Archivada",
            created_by=self.admin.id,
        )
        crud.update_taxonomy_tag(tag, is_archived=True)
        self.session.commit()

        with self.assertRaises(HTTPException) as ctx:
            conversations.set_conversation_tags(
                conversation_id=self.conversation.id,
                payload=conversations.SetConversationTagsRequest(tag_ids=[tag.id]),
                current_user=self.agent,
                db=self.session,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Archived tags cannot be assigned")


if __name__ == "__main__":
    unittest.main()
