import pytest
from src.system import SystemController, PermissionLevel

class TestSystemController:
    def test_permission_levels(self):
        controller = SystemController()
        
        controller.set_permission_level(PermissionLevel.NONE)
        assert controller.permissions.mouse_move is False
        
        controller.set_permission_level(PermissionLevel.LIMITED)
        assert controller.permissions.mouse_move is True
        assert controller.permissions.mouse_click is True
        assert controller.permissions.keyboard_input is True
        assert controller.permissions.keyboard_hotkey is False
        
        controller.set_permission_level(PermissionLevel.FULL)
        assert controller.permissions.keyboard_hotkey is True
        assert controller.permissions.window_control is True
    
    def test_individual_permission(self):
        controller = SystemController()
        
        controller.set_individual_permission("mouse_move", True)
        assert controller.permissions.mouse_move is True
        
        controller.set_individual_permission("mouse_move", False)
        assert controller.permissions.mouse_move is False
    
    def test_get_screen_size(self):
        controller = SystemController()
        width, height = controller.get_screen_size()
        assert width > 0
        assert height > 0
    
    def test_get_mouse_position(self):
        controller = SystemController()
        x, y = controller.get_mouse_position()
        assert isinstance(x, int)
        assert isinstance(y, int)
    
    def test_execute_operation_no_permission(self):
        controller = SystemController()
        controller.set_permission_level(PermissionLevel.NONE)
        
        result = controller.execute_operation({
            "type": "mouse_move",
            "x": 100,
            "y": 100
        })
        
        assert result["success"] is False
