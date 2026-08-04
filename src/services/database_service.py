import os
import socket
import platform
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import threading

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

        hostname = socket.gethostname()
        db_filename = f"{hostname}.sqlite"
        self.db_path = os.path.join(self.db_folder, db_filename)

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

        self._initialized = True
        self._session_lock = threading.Lock()

    def _ensure_db_folder(self):
        """确保数据库文件夹存在"""
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder, exist_ok=True)

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
                print(f"保存对话失败: {e}")
                return None
            finally:
                session.close()

    def save_conversation_batch(
        self,
        conversations: List[Dict[str, Any]]
    ) -> bool:
        """批量保存对话记录"""
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
                print(f"批量保存对话失败: {e}")
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
                print(f"获取对话失败: {e}")
                return []
            finally:
                session.close()

    def get_conversation_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取单条对话记录"""
        with self._session_lock:
            session = self._get_session()
            try:
                record = session.query(ConversationRecord).filter(
                    ConversationRecord.id == record_id
                ).first()
                return record.to_dict() if record else None
            except Exception as e:
                print(f"获取对话失败: {e}")
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
                print(f"获取对话数量失败: {e}")
                return 0
            finally:
                session.close()

    def delete_conversation(self, record_id: int) -> bool:
        """删除对话记录"""
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
                print(f"删除对话失败: {e}")
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
                print(f"清空对话失败: {e}")
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
                print(f"获取统计失败: {e}")
                return {}
            finally:
                session.close()

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'engine'):
            self.engine.dispose()


db_service = DatabaseService()