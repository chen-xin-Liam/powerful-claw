import os
import socket
import platform
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import threading

from src.utils.logger import get_logger
from src.utils.errors import IOError_, ValidationError
from src.utils.error_codes import ErrorCode

logger = get_logger(__name__)

Base = declarative_base()


class ConversationRecord(Base):
    """对话记录表"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    conversation_count = Column(Integer, nullable=False)
    conversation_content = Column(Text, nullable=False)
    permission_level = Column(String(50), nullable=False)
    user_hostname = Column(String(255), nullable=False)
    session_id = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<Conversation(id={self.id}, count={self.conversation_count}, time={self.timestamp})>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "conversation_count": self.conversation_count,
            "conversation_content": self.conversation_content,
            "permission_level": self.permission_level,
            "user_hostname": self.user_hostname,
            "session_id": self.session_id
        }


class DatabaseService:
    """数据库服务 - 使用SQLAlchemy + SQLite存储对话数据"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_folder: str = "userspick"):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.db_folder = db_folder
        self._ensure_db_folder()

        try:
            hostname = socket.gethostname()
        except OSError as e:
            logger.warning(f"获取主机名失败，使用 'unknown': {e}")
            hostname = "unknown"
        db_filename = f"{hostname}.sqlite"
        self.db_path = os.path.join(self.db_folder, db_filename)

        try:
            self.engine = create_engine(
                f"sqlite:///{self.db_path}",
                echo=False,
                connect_args={"check_same_thread": False}
            )

            Base.metadata.create_all(self.engine)

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        except Exception as e:
            # 数据库初始化失败属于关键路径，抛出包装异常
            logger.error(f"数据库初始化失败 ({self.db_path}): {e}", exc_info=True)
            raise IOError_(
                ErrorCode.E_IO_DB_OPERATION,
                f"数据库初始化失败: {e}",
                details={"db_path": self.db_path},
                cause=e,
            ) from e

        self._initialized = True
        self._session_lock = threading.Lock()

    def _ensure_db_folder(self):
        """确保数据库文件夹存在"""
        try:
            if not os.path.exists(self.db_folder):
                os.makedirs(self.db_folder, exist_ok=True)
        except OSError as e:
            logger.error(f"创建数据库目录失败 ({self.db_folder}): {e}", exc_info=True)
            raise IOError_(
                ErrorCode.E_IO_PERMISSION_DENIED,
                f"无法创建数据库目录: {self.db_folder}",
                details={"db_folder": self.db_folder},
                cause=e,
            ) from e

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def save_conversation(
        self,
        conversation_count: int,
        conversation_content: str,
        permission_level: str,
        session_id: Optional[str] = None
    ) -> Optional[int]:
        """保存对话记录"""
        if not isinstance(conversation_count, int) or conversation_count < 0:
            raise ValidationError(
                ErrorCode.E_VAL_INVALID_ARG,
                f"conversation_count 必须是非负整数，实际收到 {conversation_count}",
                details={"arg": "conversation_count", "value": conversation_count},
            )
        if not isinstance(permission_level, str) or not permission_level.strip():
            raise ValidationError(
                ErrorCode.E_VAL_MISSING_REQUIRED,
                "permission_level 不能为空",
                details={"arg": "permission_level"},
            )
        with self._session_lock:
            session = self._get_session()
            try:
                record = ConversationRecord(
                    conversation_count=conversation_count,
                    conversation_content=conversation_content,
                    permission_level=permission_level,
                    user_hostname=socket.gethostname(),
                    session_id=session_id
                )
                session.add(record)
                session.commit()
                record_id = record.id
                return record_id
            except Exception as e:
                session.rollback()
                logger.error(f"保存对话失败: {e}", exc_info=True)
                return None
            finally:
                session.close()

    def save_conversation_batch(
        self,
        conversations: List[Dict[str, Any]]
    ) -> bool:
        """批量保存对话记录"""
        if not isinstance(conversations, list):
            raise ValidationError(
                ErrorCode.E_VAL_INVALID_ARG,
                f"conversations 必须是列表，实际收到 {type(conversations).__name__}",
                details={"arg": "conversations"},
            )
        with self._session_lock:
            session = self._get_session()
            try:
                records = []
                hostname = socket.gethostname()
                for conv in conversations:
                    record = ConversationRecord(
                        conversation_count=conv.get("conversation_count", 1),
                        conversation_content=conv.get("conversation_content", ""),
                        permission_level=conv.get("permission_level", "normal"),
                        user_hostname=hostname,
                        session_id=conv.get("session_id")
                    )
                    records.append(record)
                session.bulk_save_objects(records)
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"批量保存对话失败: {e}", exc_info=True)
                return False
            finally:
                session.close()

    def get_conversations(
        self,
        limit: int = 100,
        offset: int = 0,
        permission_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取对话记录"""
        if not isinstance(limit, int) or limit < 0:
            raise ValidationError(
                ErrorCode.E_VAL_OUT_OF_RANGE,
                f"limit 必须是非负整数，实际收到 {limit}",
                details={"arg": "limit", "value": limit},
            )
        with self._session_lock:
            session = self._get_session()
            try:
                query = session.query(ConversationRecord)

                if permission_level:
                    query = query.filter(
                        ConversationRecord.permission_level == permission_level
                    )

                records = query.order_by(
                    ConversationRecord.timestamp.desc()
                ).offset(offset).limit(limit).all()

                return [record.to_dict() for record in records]
            except Exception as e:
                logger.error(f"获取对话失败: {e}", exc_info=True)
                return []
            finally:
                session.close()

    def get_conversation_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取单条对话记录"""
        if not isinstance(record_id, int) or record_id <= 0:
            raise ValidationError(
                ErrorCode.E_VAL_INVALID_ARG,
                f"record_id 必须是正整数，实际收到 {record_id}",
                details={"arg": "record_id", "value": record_id},
            )
        with self._session_lock:
            session = self._get_session()
            try:
                record = session.query(ConversationRecord).filter(
                    ConversationRecord.id == record_id
                ).first()
                return record.to_dict() if record else None
            except Exception as e:
                logger.error(f"获取对话失败 (id={record_id}): {e}", exc_info=True)
                return None
            finally:
                session.close()

    def get_conversation_count(
        self,
        permission_level: Optional[str] = None
    ) -> int:
        """获取对话总数"""
        with self._session_lock:
            session = self._get_session()
            try:
                query = session.query(ConversationRecord)
                if permission_level:
                    query = query.filter(
                        ConversationRecord.permission_level == permission_level
                    )
                return query.count()
            except Exception as e:
                logger.error(f"获取对话数量失败: {e}", exc_info=True)
                return 0
            finally:
                session.close()

    def delete_conversation(self, record_id: int) -> bool:
        """删除对话记录"""
        if not isinstance(record_id, int) or record_id <= 0:
            raise ValidationError(
                ErrorCode.E_VAL_INVALID_ARG,
                f"record_id 必须是正整数，实际收到 {record_id}",
                details={"arg": "record_id", "value": record_id},
            )
        with self._session_lock:
            session = self._get_session()
            try:
                record = session.query(ConversationRecord).filter(
                    ConversationRecord.id == record_id
                ).first()
                if record:
                    session.delete(record)
                    session.commit()
                    return True
                return False
            except Exception as e:
                session.rollback()
                logger.error(f"删除对话失败 (id={record_id}): {e}", exc_info=True)
                return False
            finally:
                session.close()

    def clear_all_conversations(self) -> bool:
        """清空所有对话记录"""
        with self._session_lock:
            session = self._get_session()
            try:
                session.query(ConversationRecord).delete()
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"清空对话失败: {e}", exc_info=True)
                return False
            finally:
                session.close()

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with self._session_lock:
            session = self._get_session()
            try:
                total = session.query(ConversationRecord).count()

                from sqlalchemy import func
                by_permission = session.query(
                    ConversationRecord.permission_level,
                    func.count(ConversationRecord.id)
                ).group_by(ConversationRecord.permission_level).all()

                by_hostname = session.query(
                    ConversationRecord.user_hostname,
                    func.count(ConversationRecord.id)
                ).group_by(ConversationRecord.user_hostname).all()

                return {
                    "total_conversations": total,
                    "by_permission": dict(by_permission),
                    "by_hostname": dict(by_hostname),
                    "database_path": self.db_path,
                    "database_size_bytes": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                }
            except Exception as e:
                logger.error(f"获取统计失败: {e}", exc_info=True)
                return {}
            finally:
                session.close()

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'engine'):
            self.engine.dispose()


db_service = DatabaseService()