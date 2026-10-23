import logging

from sqlalchemy.orm import Session

from app.models import User

logger = logging.getLogger(__name__)


def delete_user(db: Session, user: User) -> None:
    user_id = user.id
    db.delete(user)
    db.commit()
    logger.info("Account deleted: id=%d", user_id)
