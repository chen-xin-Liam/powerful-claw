from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.tree import Tree
from rich.status import Status
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
import threading

console = Console()


class RichTerminal:
    """Rich终端美化工具 - 提供表格、进度条、调试输出等功能"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.console = Console()
        self._initialized = True
    
    def print_table(self, data: list, headers: list, title: str = ""):
        """打印表格"""
        table = Table(title=title)
        
        for header in headers:
            table.add_column(header, style="bold magenta")
        
        for row in data:
            table.add_row(*[str(item) for item in row])
        
        self.console.print(table)
    
    def print_progress(self, iterable, description: str = "Processing"):
        """打印进度条"""
        with Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task(description, total=len(iterable))
            
            for item in iterable:
                yield item
                progress.update(task, advance=1)
    
    def print_panel(self, content: str, title: str = "", border_style: str = "blue"):
        """打印面板"""
        panel = Panel(content, title=title, border_style=border_style)
        self.console.print(panel)
    
    def print_success(self, message: str):
        """打印成功消息"""
        self.console.print(f"[green]✓[/green] {message}")
    
    def print_error(self, message: str):
        """打印错误消息"""
        self.console.print(f"[red]✗[/red] {message}")
    
    def print_warning(self, message: str):
        """打印警告消息"""
        self.console.print(f"[yellow]⚠[/yellow] {message}")
    
    def print_info(self, message: str):
        """打印信息消息"""
        self.console.print(f"[blue]ℹ[/blue] {message}")
    
    def print_debug(self, message: str):
        """打印调试消息"""
        self.console.print(f"[gray]DEBUG:[/gray] {message}")
    
    def print_syntax(self, code: str, language: str = "python"):
        """打印带语法高亮的代码"""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(syntax)
    
    def print_tree(self, data, label: str = "Root"):
        """打印树形结构"""
        tree = Tree(label)
        
        def add_nodes(parent, items):
            if isinstance(items, dict):
                for key, value in items.items():
                    node = parent.add(f"[bold]{key}[/bold]")
                    add_nodes(node, value)
            elif isinstance(items, list):
                for i, item in enumerate(items):
                    node = parent.add(f"[{i}]")
                    add_nodes(node, item)
            else:
                parent.add(str(items))
        
        add_nodes(tree, data)
        self.console.print(tree)
    
    def print_markdown(self, content: str):
        """打印Markdown内容"""
        markdown = Markdown(content)
        self.console.print(markdown)
    
    def prompt(self, message: str) -> str:
        """显示输入提示"""
        return Prompt.ask(message)
    
    def confirm(self, message: str) -> bool:
        """显示确认提示"""
        return Confirm.ask(message)
    
    def status(self, message: str):
        """显示状态指示器"""
        return Status(message, spinner="dots")


# 创建全局终端实例
rich_terminal = RichTerminal()
