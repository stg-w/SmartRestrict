import logging
from typing import Optional
import oracledb
from backend.database import get_db_connection, rows_to_dicts, row_to_dict
from backend.models import UserProfileResponse, RestrictionItem

logger = logging.getLogger("smartrestrict.user_service")

class UserService:
    """Manages user profiles and saved dietary restriction preferences in Oracle."""

    def save_profile_and_restrictions(
        self,
        user_name: str,
        email: str,
        restriction_ids: list[int]
    ) -> UserProfileResponse:
        clean_email = email.strip().lower()
        clean_name = user_name.strip()

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. Check if user exists by email
                cur.execute("""
                    SELECT USER_ID, USER_NAME, EMAIL, CREATED_ON
                    FROM USERS
                    WHERE LOWER(EMAIL) = :email
                """, {"email": clean_email})
                existing = row_to_dict(cur, cur.fetchone())

                user_id: int
                created_on_str: Optional[str] = None

                if existing:
                    user_id = int(existing["user_id"])
                    created_on_str = str(existing.get("created_on"))
                    # Update name if changed
                    cur.execute("""
                        UPDATE USERS
                        SET USER_NAME = :name
                        WHERE USER_ID = :uid
                    """, {"name": clean_name, "uid": user_id})
                else:
                    # Insert new user with returning identity
                    out_id = cur.var(oracledb.NUMBER)
                    cur.execute("""
                        INSERT INTO USERS (USER_NAME, EMAIL, CREATED_ON)
                        VALUES (:name, :email, SYSDATE)
                        RETURNING USER_ID INTO :out_id
                    """, {"name": clean_name, "email": clean_email, "out_id": out_id})
                    user_id = int(out_id.getvalue()[0])
                    created_on_str = "Just now"

                # 2. Update user restrictions
                cur.execute("DELETE FROM USER_RESTRICTIONS WHERE USER_ID = :uid", {"uid": user_id})

                valid_r_ids = []
                if restriction_ids:
                    # Ensure restriction IDs exist in RESTRICTIONS table
                    cur.execute("SELECT RESTRICTION_ID FROM RESTRICTIONS")
                    available_r_ids = {r[0] for r in cur.fetchall()}
                    for r_id in set(restriction_ids):
                        if r_id in available_r_ids:
                            cur.execute("""
                                INSERT INTO USER_RESTRICTIONS (USER_ID, RESTRICTION_ID)
                                VALUES (:uid, :rid)
                            """, {"uid": user_id, "rid": r_id})
                            valid_r_ids.append(r_id)

                conn.commit()

                # 3. Retrieve updated restrictions
                cur.execute("""
                    SELECT r.RESTRICTION_ID, r.RESTRICTION_NAME, r.DESCRIPTION
                    FROM USER_RESTRICTIONS ur
                    JOIN RESTRICTIONS r ON ur.RESTRICTION_ID = r.RESTRICTION_ID
                    WHERE ur.USER_ID = :uid
                    ORDER BY r.RESTRICTION_ID
                """, {"uid": user_id})
                r_rows = rows_to_dicts(cur)
                restrictions = [
                    RestrictionItem(
                        restriction_id=r["restriction_id"],
                        restriction_name=r["restriction_name"],
                        description=r["description"]
                    )
                    for r in r_rows
                ]

                return UserProfileResponse(
                    user_id=user_id,
                    user_name=clean_name,
                    email=clean_email,
                    created_on=created_on_str,
                    restrictions=restrictions
                )

    def get_profile_by_email(self, email: str) -> Optional[UserProfileResponse]:
        clean_email = email.strip().lower()
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT USER_ID, USER_NAME, EMAIL, CREATED_ON
                    FROM USERS
                    WHERE LOWER(EMAIL) = :email
                """, {"email": clean_email})
                user = row_to_dict(cur, cur.fetchone())
                if not user:
                    return None

                uid = user["user_id"]
                cur.execute("""
                    SELECT r.RESTRICTION_ID, r.RESTRICTION_NAME, r.DESCRIPTION
                    FROM USER_RESTRICTIONS ur
                    JOIN RESTRICTIONS r ON ur.RESTRICTION_ID = r.RESTRICTION_ID
                    WHERE ur.USER_ID = :uid
                    ORDER BY r.RESTRICTION_ID
                """, {"uid": uid})
                r_rows = rows_to_dicts(cur)
                restrictions = [
                    RestrictionItem(
                        restriction_id=r["restriction_id"],
                        restriction_name=r["restriction_name"],
                        description=r["description"]
                    )
                    for r in r_rows
                ]

                return UserProfileResponse(
                    user_id=uid,
                    user_name=user["user_name"],
                    email=user["email"],
                    created_on=str(user.get("created_on")),
                    restrictions=restrictions
                )

user_service = UserService()
