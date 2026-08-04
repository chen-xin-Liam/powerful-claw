import cattrs
from cattrs import Converter
from datetime import datetime
from typing import Any, Dict, List, Type
from pydantic import BaseModel


class CattrsConverter:
    """Cattrs数据转换器 - 支持对象与字典/JSON之间的转换"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 创建默认转换器
        self.converter = Converter()
        
        # 注册自定义钩子
        self._register_hooks()
        
        self._initialized = True
    
    def _register_hooks(self):
        """注册自定义转换钩子"""
        
        # datetime -> str (ISO format)
        self.converter.register_unstructure_hook(
            datetime,
            lambda dt: dt.isoformat()
        )
        
        # str -> datetime
        self.converter.register_structure_hook(
            datetime,
            lambda s, _: datetime.fromisoformat(s)
        )
        
        # pydantic BaseModel -> dict
        self.converter.register_unstructure_hook(
            BaseModel,
            lambda model: model.model_dump()
        )
    
    def structure(self, obj: Any, cls: Type) -> Any:
        """将原始数据结构化为指定类型"""
        return self.converter.structure(obj, cls)
    
    def unstructure(self, obj: Any) -> Any:
        """将对象转换为原始数据类型"""
        return self.converter.unstructure(obj)
    
    def structure_list(self, objs: List[Any], cls: Type) -> List[Any]:
        """批量结构化为指定类型列表"""
        return [self.converter.structure(obj, cls) for obj in objs]
    
    def unstructure_list(self, objs: List[Any]) -> List[Dict[str, Any]]:
        """批量转换为字典列表"""
        return [self.converter.unstructure(obj) for obj in objs]
    
    def to_dict(self, obj: Any) -> Dict[str, Any]:
        """转换为字典"""
        return self.converter.unstructure(obj)
    
    def from_dict(self, data: Dict[str, Any], cls: Type) -> Any:
        """从字典转换为对象"""
        return self.converter.structure(data, cls)


# 创建全局转换器实例
cattrs_converter = CattrsConverter()
