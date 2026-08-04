import customtkinter as ctk
from tkinter import messagebox
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import theme_manager, settings
from src.config.theme_manager import ThemeConfig, ThemeColors

class ThemeSettingsPanel(ctk.CTkFrame):
    """主题设置面板 - 支持热加载、选择和刷新"""
    
    def __init__(self, master, on_theme_change=None):
        super().__init__(master)
        self.on_theme_change = on_theme_change
        self.selected_theme = settings.theme_name
        self.master = master  # 保存主窗口引用
        
        # 加载主题
        theme_manager.load_all_themes()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI布局"""
        # 标题
        title_label = ctk.CTkLabel(self, text="主题设置", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(pady=10, padx=10, anchor="w")
        
        # 主题列表框架
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 主题列表
        self.theme_listbox = ctk.CTkOptionMenu(
            list_frame,
            values=self._get_theme_list(),
            command=self._on_theme_select,
            width=300
        )
        self.theme_listbox.pack(pady=10, padx=10, fill="x")
        
        # 设置当前选中的主题
        if self.selected_theme in theme_manager.get_theme_names():
            self.theme_listbox.set(self.selected_theme)
        
        # 主题预览
        preview_frame = ctk.CTkFrame(list_frame)
        preview_frame.pack(fill="x", padx=10, pady=5)
        
        self.preview_label = ctk.CTkLabel(preview_frame, text="主题预览", font=ctk.CTkFont(size=12, weight="bold"))
        self.preview_label.pack(pady=5, padx=10, anchor="w")
        
        # 暗色模式预览
        dark_preview_frame = ctk.CTkFrame(preview_frame)
        dark_preview_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(dark_preview_frame, text="暗色模式", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=2)
        self.dark_color_preview = ctk.CTkFrame(dark_preview_frame, height=50, corner_radius=8)
        self.dark_color_preview.pack(fill="x", pady=2)
        
        # 亮色模式预览
        light_preview_frame = ctk.CTkFrame(preview_frame)
        light_preview_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(light_preview_frame, text="亮色模式", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=2)
        self.light_color_preview = ctk.CTkFrame(light_preview_frame, height=50, corner_radius=8)
        self.light_color_preview.pack(fill="x", pady=2)
        
        # 显示主题信息
        info_frame = ctk.CTkFrame(list_frame)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        self.author_label = ctk.CTkLabel(info_frame, text="作者: ", font=ctk.CTkFont(size=12))
        self.author_label.pack(pady=2, padx=10, anchor="w")
        
        self.version_label = ctk.CTkLabel(info_frame, text="版本: ", font=ctk.CTkFont(size=12))
        self.version_label.pack(pady=2, padx=10, anchor="w")
        
        self.desc_label = ctk.CTkLabel(info_frame, text="描述: ", font=ctk.CTkFont(size=12), wraplength=250)
        self.desc_label.pack(pady=2, padx=10, anchor="w")
        
        # 操作按钮
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        self.refresh_btn = ctk.CTkButton(
            button_frame,
            text="刷新主题",
            command=self._refresh_themes,
            width=100
        )
        self.refresh_btn.pack(side="left", padx=5, pady=5)
        
        self.apply_btn = ctk.CTkButton(
            button_frame,
            text="应用主题",
            command=self._apply_theme,
            width=100
        )
        self.apply_btn.pack(side="left", padx=5, pady=5)
        
        self.export_btn = ctk.CTkButton(
            button_frame,
            text="导出主题",
            command=self._export_theme,
            width=100
        )
        self.export_btn.pack(side="left", padx=5, pady=5)
        
        self.delete_btn = ctk.CTkButton(
            button_frame,
            text="删除主题",
            command=self._delete_theme,
            width=100,
            fg_color="red"
        )
        self.delete_btn.pack(side="right", padx=5, pady=5)
        
        # 更新预览
        self._update_preview()
    
    def _get_theme_list(self):
        """获取主题列表"""
        return theme_manager.get_theme_names()
    
    def _on_theme_select(self, theme_name):
        """选择主题时更新预览"""
        self.selected_theme = theme_name
        self._update_preview()
    
    def _update_preview(self):
        """更新主题预览 - 支持亮色和暗色模式"""
        theme = theme_manager.get_theme(self.selected_theme)
        if theme:
            # 更新暗色模式预览框颜色
            self.dark_color_preview.configure(fg_color=theme.dark_colors.primary)
            
            # 更新亮色模式预览框颜色
            self.light_color_preview.configure(fg_color=theme.light_colors.primary)
            
            # 更新信息
            self.author_label.configure(text=f"作者: {theme.author}")
            self.version_label.configure(text=f"版本: {theme.version}")
            self.desc_label.configure(text=f"描述: {theme.description}")
    
    def _refresh_themes(self):
        """刷新主题列表（热加载）"""
        changes = theme_manager.hot_reload()
        
        # 更新列表
        themes = theme_manager.get_theme_names()
        self.theme_listbox.configure(values=themes)
        
        # 显示变化信息
        msg = ""
        if changes['added']:
            msg += f"新增主题: {', '.join(changes['added'])}\n"
        if changes['updated']:
            msg += f"更新主题: {', '.join(changes['updated'])}\n"
        if changes['removed']:
            msg += f"删除主题: {', '.join(changes['removed'])}\n"
        
        if msg:
            messagebox.showinfo("主题刷新", msg)
        else:
            messagebox.showinfo("主题刷新", "没有检测到变化")
    
    def _apply_theme(self):
        """应用选中的主题 - 实时应用颜色到界面"""
        if theme_manager.set_theme(self.selected_theme):
            settings.theme_name = self.selected_theme
            
            # 获取当前主题颜色
            theme = theme_manager.get_theme(self.selected_theme)
            if theme:
                # 应用主题颜色到当前界面
                self._apply_theme_colors(theme)
            
            messagebox.showinfo("应用主题", f"主题 '{self.selected_theme}' 已应用")
            
            if self.on_theme_change:
                self.on_theme_change(self.selected_theme)
        else:
            messagebox.showerror("错误", "无法应用主题")
    
    def _apply_theme_colors(self, theme: ThemeConfig):
        """将主题颜色应用到界面元素"""
        try:
            # 获取当前外观模式
            appearance_mode = ctk.get_appearance_mode()
            colors = theme.get_colors(appearance_mode)
            
            # 获取主窗口
            root = self.master
            while root.master:
                root = root.master
            
            # 应用颜色到所有CTkFrame
            for widget in root.winfo_children():
                self._apply_color_to_widget(widget, colors)
            
            # 更新CustomTkinter的默认颜色主题（通过设置全局变量）
            ctk.set_default_color_theme(self._create_temp_color_theme(colors))
            
            print(f"主题颜色已应用: {colors.primary}")
        except Exception as e:
            print(f"应用主题颜色时出错: {e}")
    
    def _apply_color_to_widget(self, widget, colors: ThemeColors):
        """递归应用颜色到控件及其子控件"""
        try:
            # 应用背景色
            if hasattr(widget, 'configure'):
                # 根据控件类型应用不同的颜色
                widget_type = type(widget).__name__
                
                if widget_type == 'CTkFrame':
                    widget.configure(fg_color=colors.surface)
                elif widget_type == 'CTkButton':
                    # 只改变普通按钮的颜色，保留特殊按钮（如删除按钮）的颜色
                    current_color = widget.cget('fg_color')
                    if current_color not in ['red', 'green', 'gray']:
                        widget.configure(fg_color=colors.primary)
                elif widget_type == 'CTkLabel':
                    widget.configure(text_color=colors.text_primary)
                elif widget_type == 'CTkEntry':
                    widget.configure(fg_color=colors.card, text_color=colors.text_primary)
                elif widget_type == 'CTkTextbox':
                    widget.configure(fg_color=colors.card, text_color=colors.text_primary)
                elif widget_type == 'CTkScrollableFrame':
                    widget.configure(fg_color=colors.surface)
                elif widget_type == 'CTkComboBox':
                    widget.configure(fg_color=colors.card, text_color=colors.text_primary)
                elif widget_type == 'CTkSlider':
                    widget.configure(fg_color=colors.border)
            
            # 递归处理子控件
            for child in widget.winfo_children():
                self._apply_color_to_widget(child, colors)
        except Exception as e:
            # 忽略单个控件的错误
            pass
    
    def _create_temp_color_theme(self, colors: ThemeColors) -> str:
        """创建临时颜色主题配置字符串"""
        import tempfile
        import os
        
        theme_content = f"""
[CTk]
fg_color = {colors.surface}
bg_color = {colors.background}

[CTkFrame]
fg_color = {colors.surface}
top_fg_color = {colors.card}

[CTkButton]
fg_color = {colors.primary}
hover_color = {colors.accent}
text_color = {colors.text_primary}

[CTkLabel]
text_color = {colors.text_primary}

[CTkEntry]
fg_color = {colors.card}
text_color = {colors.text_primary}
placeholder_text_color = {colors.text_disabled}

[CTkTextbox]
fg_color = {colors.card}
text_color = {colors.text_primary}

[CTkScrollbar]
fg_color = {colors.border}
button_color = {colors.accent}

[CTkSlider]
fg_color = {colors.border}
progress_color = {colors.primary}

[CTkComboBox]
fg_color = {colors.card}
button_color = {colors.primary}
text_color = {colors.text_primary}
        """
        
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        temp_file.write(theme_content)
        temp_file.close()
        
        return temp_file.name
    
    def _export_theme(self):
        """导出主题配置"""
        import tkinter as tk
        from tkinter import filedialog
        
        theme = theme_manager.get_theme(self.selected_theme)
        if not theme:
            messagebox.showerror("错误", "请选择一个主题")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".ini",
            filetypes=[("INI文件", "*.ini")],
            initialfile=f"{theme.name.lower().replace(' ', '_')}.ini"
        )
        
        if file_path:
            if theme_manager.export_theme(self.selected_theme, file_path):
                messagebox.showinfo("导出成功", f"主题已导出到:\n{file_path}")
            else:
                messagebox.showerror("错误", "导出失败")
    
    def _delete_theme(self):
        """删除主题"""
        if self.selected_theme == "Ocean Blue":
            messagebox.showerror("错误", "无法删除默认主题")
            return
        
        if messagebox.askyesno("确认删除", f"确定要删除主题 '{self.selected_theme}' 吗？"):
            if theme_manager.remove_theme(self.selected_theme):
                # 更新列表
                themes = theme_manager.get_theme_names()
                self.theme_listbox.configure(values=themes)
                
                # 选择第一个主题
                if themes:
                    self.selected_theme = themes[0]
                    self.theme_listbox.set(self.selected_theme)
                    self._update_preview()
                
                messagebox.showinfo("删除成功", "主题已删除")
            else:
                messagebox.showerror("错误", "删除失败")

# 测试代码
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    app = ctk.CTk()
    app.title("主题设置测试")
    app.geometry("400x500")
    
    panel = ThemeSettingsPanel(app)
    panel.pack(fill="both", expand=True, padx=10, pady=10)
    
    app.mainloop()
