"""Review physical PostgreSQL LOGIN after managed SET ROLE abc_app."""
import unittest
from unittest.mock import Mock,MagicMock

from abc_foundation.staging_api import assert_staging_database


class ManagedDatabaseRoleAuditTests(unittest.TestCase):
    def _store(self,login,role="abc_app",privileged=False):
        con=Mock()
        def execute(query,*_args):
            cursor=Mock()
            if "session_user AS login" in query:
                cursor.fetchone.return_value={
                    "role":role,"login":login,"privileged":privileged}
            else:
                cursor.fetchone.return_value={"rls":True,"forced":True}
            return cursor
        con.execute.side_effect=execute
        store=MagicMock()
        store._connect.return_value.__enter__.return_value=con
        return store

    def test_valid_managed_physical_identity_after_set_role(self):
        store=self._store("abc_api_aabbccdd1122")
        assert_staging_database(store,"abc_app",["abc.sessions"],
            expected_login="abc_api_aabbccdd1122")

    def test_app_role_is_not_sufficient_without_pinned_physical_login(self):
        for login,role,privileged in (
            ("abc_app","abc_app",False),
            ("abc_api_wrong123","abc_app",False),
            ("abc_api_aabbccdd1122","postgres",False),
            ("abc_api_aabbccdd1122","abc_app",True)):
            with self.subTest(login=login,role=role,privileged=privileged):
                with self.assertRaisesRegex(ValueError,"database_privilege_boundary_violation"):
                    assert_staging_database(self._store(login,role,privileged),
                      "abc_app",["abc.sessions"],
                      expected_login="abc_api_aabbccdd1122")


if __name__=="__main__":
    unittest.main()
