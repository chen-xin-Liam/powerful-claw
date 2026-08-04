import json
import re
from typing import Dict, Any, Optional

class ResponseParser:
    @staticmethod
    def parse_ai_response(content: str) -> Dict[str, Any]:
        result = {
            "text": "",
            "operations": [],
            "thought": ""
        }
        
        if not content:
            return result
        
        text_parts = []
        operations = []
        
        code_blocks = re.findall(r'```(json)?\s*([\s\S]*?)\s*```', content)
        
        for lang, code in code_blocks:
            if lang.lower() == "json" or lang == "":
                try:
                    parsed = json.loads(code)
                    if isinstance(parsed, list):
                        operations.extend(parsed)
                    elif isinstance(parsed, dict):
                        operations.append(parsed)
                except json.JSONDecodeError:
                    text_parts.append(code)
        
        text_content = re.sub(r'```[\s\S]*?```', '', content)
        text_parts.append(text_content.strip())
        
        result["text"] = "\n".join(text_parts).strip()
        result["operations"] = operations
        
        return result
    
    @staticmethod
    def extract_thinking(content: str) -> str:
        thinking_pattern = r'<thinking>([\s\S]*?)</thinking>'
        match = re.search(thinking_pattern, content)
        if match:
            return match.group(1).strip()
        return ""
    
    @staticmethod
    def is_control_command(content: str) -> bool:
        control_patterns = [
            r'```json.*operation.*```',
            r'"type":\s*["\']mouse["\']',
            r'"type":\s*["\']keyboard["\']',
            r'"type":\s*["\']window["\']'
        ]
        
        for pattern in control_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False
