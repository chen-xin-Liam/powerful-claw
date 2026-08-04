import re
from typing import Tuple, List

class MarkdownRenderer:
    def __init__(self):
        self.bold_pattern = re.compile(r'\*\*(.+?)\*\*|__(.+?)__')
        self.italic_pattern = re.compile(r'\*(.+?)\*|_(.+?)_')
        self.code_pattern = re.compile(r'`(.+?)`')
        self.code_block_pattern = re.compile(r'```(\w*)\n([\s\S]*?)```')
        self.link_pattern = re.compile(r'\[(.+?)\]\((.+?)\)')
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)', re.MULTILINE)
        self.list_pattern = re.compile(r'^(\s*[-*+])\s+(.+)', re.MULTILINE)
        self.numbered_list_pattern = re.compile(r'^(\s*\d+\.)\s+(.+)', re.MULTILINE)
        self.blockquote_pattern = re.compile(r'^>\s+(.+)', re.MULTILINE)
        self.horizontal_rule_pattern = re.compile(r'^[-*_]{3,}$', re.MULTILINE)
    
    def parse(self, text: str) -> List[Tuple[str, str]]:
        """
        解析Markdown文本，返回格式化的文本片段列表
        返回格式: [(text, style), ...]
        style: 'normal', 'bold', 'italic', 'code', 'heading1-6', 'list', 'blockquote', 'link'
        """
        segments = []
        
        text = text.replace('\r\n', '\n')
        
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if self.horizontal_rule_pattern.match(line):
                segments.append(('─' * 50, 'horizontal_rule'))
                i += 1
                continue
            
            heading_match = self.heading_pattern.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                content = heading_match.group(2)
                segments.append((content, f'heading{level}'))
                i += 1
                continue
            
            blockquote_match = self.blockquote_pattern.match(line)
            if blockquote_match:
                quote_lines = [blockquote_match.group(1)]
                i += 1
                while i < len(lines) and lines[i].startswith('>'):
                    quote_lines.append(lines[i][1:].strip())
                    i += 1
                segments.append(('\n'.join(quote_lines), 'blockquote'))
                continue
            
            code_block_match = self.code_block_pattern.match('\n'.join(lines[i:]))
            if code_block_match:
                language = code_block_match.group(1)
                code_content = code_block_match.group(2)
                segments.append((code_content, 'code_block'))
                lines_used = code_content.count('\n') + 2
                i += lines_used
                continue
            
            list_match = self.list_pattern.match(line)
            if list_match:
                list_items = [list_match.group(2)]
                i += 1
                while i < len(lines):
                    next_match = self.list_pattern.match(lines[i])
                    num_match = self.numbered_list_pattern.match(lines[i])
                    if next_match:
                        list_items.append(next_match.group(2))
                        i += 1
                    elif num_match:
                        list_items.append(num_match.group(2))
                        i += 1
                    elif lines[i].strip() == '':
                        i += 1
                    else:
                        break
                for item in list_items:
                    segments.append((f'• {item}', 'list'))
                continue
            
            num_match = self.numbered_list_pattern.match(line)
            if num_match:
                list_items = [num_match.group(2)]
                i += 1
                while i < len(lines):
                    next_num_match = self.numbered_list_pattern.match(lines[i])
                    next_list_match = self.list_pattern.match(lines[i])
                    if next_num_match:
                        list_items.append(next_num_match.group(2))
                        i += 1
                    elif next_list_match:
                        list_items.append(next_list_match.group(2))
                        i += 1
                    elif lines[i].strip() == '':
                        i += 1
                    else:
                        break
                for idx, item in enumerate(list_items, 1):
                    segments.append((f'{idx}. {item}', 'list'))
                continue
            
            segments.append((line, 'normal'))
            i += 1
        
        return segments
    
    def render_to_text(self, text: str) -> str:
        """将Markdown转换为格式化文本（适合终端显示）"""
        segments = self.parse(text)
        result = []
        
        for content, style in segments:
            if style.startswith('heading'):
                level = int(style[-1])
                result.append(f'\n{"=" * (7 - level)}{content}{"=" * (7 - level)}\n')
            elif style == 'bold':
                result.append(f'【{content}】')
            elif style == 'italic':
                result.append(f'*{content}*')
            elif style == 'code':
                result.append(f'`{content}`')
            elif style == 'code_block':
                result.append(f'\n```\n{content}\n```\n')
            elif style == 'blockquote':
                lines = content.split('\n')
                quoted = '\n'.join(f'▸ {line}' for line in lines)
                result.append(f'\n{quoted}\n')
            elif style == 'list':
                result.append(content)
            elif style == 'horizontal_rule':
                result.append(content)
            else:
                result.append(content)
        
        return '\n'.join(result)
    
    def simplify_markdown(self, text: str) -> str:
        """简化Markdown，保留基本格式但移除复杂元素"""
        text = self.bold_pattern.sub(r'【\1\2】', text)
        text = self.italic_pattern.sub(r'*\1\2*', text)
        text = self.link_pattern.sub(r'\1', text)
        text = self.code_block_pattern.sub(r'\n代码:\n\2\n', text)
        text = self.code_pattern.sub(r'`\1`', text)
        
        lines = text.split('\n')
        result = []
        for line in lines:
            heading_match = self.heading_pattern.match(line.strip())
            if heading_match:
                level = len(heading_match.group(1))
                content = heading_match.group(2).strip()
                result.append(f'\n{"#" * level} {content}\n')
            elif line.startswith('>'):
                result.append(f'▸ {line[1:].strip()}')
            elif self.list_pattern.match(line):
                result.append(f'• {line.lstrip()[1:].strip()}')
            elif self.numbered_list_pattern.match(line):
                result.append(line)
            elif self.horizontal_rule_pattern.match(line):
                result.append('\n─' * 20 + '\n')
            elif line.strip().startswith('---'):
                result.append('\n' + '─' * 30 + '\n')
            else:
                result.append(line)
        
        return '\n'.join(result)